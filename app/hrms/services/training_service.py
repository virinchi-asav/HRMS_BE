from datetime import datetime

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import Role
from app.hrms.core.deps import CurrentHrmsUser
from app.hrms.models.training import (
    AssessmentGivenBy,
    AssessmentStatus,
    MaterialType,
    TrainingAssessmentEntity,
    TrainingAssessmentScreenshotEntity,
    TrainingCommentEntity,
    TrainingDayEntryEntity,
    TrainingMaterialEntity,
    TrainingProgramEntity,
    TrainingStatus,
    TrainingTraineeEntity,
)
from app.hrms.models.user import UserEntity as HrmsUserEntity
from app.hrms.schemas.training import (
    AssessmentResponse,
    AssessmentReviewRequest,
    AssessmentSubmissionUpdateRequest,
    CommentCreateRequest,
    CommentResponse,
    DayEntryCreateRequest,
    DayEntryResponse,
    MaterialLinkCreateRequest,
    MaterialResponse,
    ScreenshotResponse,
    TrainingCreateRequest,
    TrainingResponse,
)
from app.hrms.services import email_service, file_storage_service
from app.models.account import AccountEntity
from app.utils.pagination import PageResult, paginate


async def _user_names(hrms_db: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await hrms_db.execute(select(HrmsUserEntity.id, HrmsUserEntity.name).where(HrmsUserEntity.id.in_(user_ids)))
    return {row.id: row.name for row in result.all()}


async def _account_names(kms_db: AsyncSession, account_ids: set[int]) -> dict[int, str]:
    if not account_ids:
        return {}
    result = await kms_db.execute(select(AccountEntity).where(AccountEntity.account_id.in_(account_ids)))
    return {a.account_id: a.account_name for a in result.scalars().all()}


async def _trainee_counts(hrms_db: AsyncSession, training_ids: list[int]) -> dict[int, int]:
    if not training_ids:
        return {}
    result = await hrms_db.execute(
        select(TrainingTraineeEntity.training_id, func.count())
        .where(TrainingTraineeEntity.training_id.in_(training_ids))
        .group_by(TrainingTraineeEntity.training_id)
    )
    return dict(result.all())


async def _trainee_ids(hrms_db: AsyncSession, training_id: int) -> list[int]:
    result = await hrms_db.execute(
        select(TrainingTraineeEntity.trainee_id).where(TrainingTraineeEntity.training_id == training_id)
    )
    return [row[0] for row in result.all()]


async def _is_participant(hrms_db: AsyncSession, current_user: CurrentHrmsUser, entity: TrainingProgramEntity) -> bool:
    """Admin/HR see everything; BU Head sees their own assigned trainings; Trainer/
    Trainees see the training they're personally part of."""
    if current_user.role in (Role.ADMIN, Role.HR):
        return True
    if entity.bu_head_id == current_user.id or entity.trainer_id == current_user.id:
        return True
    return current_user.id in await _trainee_ids(hrms_db, entity.id)


async def _is_trainer_or_trainee(hrms_db: AsyncSession, current_user: CurrentHrmsUser, entity: TrainingProgramEntity) -> bool:
    if entity.trainer_id == current_user.id:
        return True
    return current_user.id in await _trainee_ids(hrms_db, entity.id)


async def _to_response(hrms_db: AsyncSession, kms_db: AsyncSession, entity: TrainingProgramEntity) -> TrainingResponse:
    trainee_ids = await _trainee_ids(hrms_db, entity.id)
    user_ids = set(trainee_ids) | {entity.trainer_id, entity.bu_head_id, entity.created_by}
    names = await _user_names(hrms_db, user_ids)

    account_name = None
    if entity.account_id:
        accounts = await _account_names(kms_db, {entity.account_id})
        account_name = accounts.get(entity.account_id)

    return TrainingResponse(
        id=entity.id,
        topic=entity.topic,
        description=entity.description,
        account_id=entity.account_id,
        account=account_name,
        trainer_id=entity.trainer_id,
        trainer_name=names.get(entity.trainer_id, "Unknown"),
        bu_head_id=entity.bu_head_id,
        bu_head_name=names.get(entity.bu_head_id, "Unknown"),
        status=entity.status,
        has_assessment=entity.has_assessment,
        assessment_given_by=entity.assessment_given_by,
        rejection_reason=entity.rejection_reason,
        start_date=entity.start_date,
        end_date=entity.end_date,
        created_by=entity.created_by,
        created_by_name=names.get(entity.created_by, "Unknown"),
        approved_at=entity.approved_at,
        rejected_at=entity.rejected_at,
        completed_at=entity.completed_at,
        created_at=entity.created_at,
        trainees=[{"id": tid, "name": names.get(tid, "Unknown")} for tid in trainee_ids],
    )


async def create_training(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, data: TrainingCreateRequest
) -> TrainingResponse:
    if not data.trainee_ids:
        raise ValueError("At least one trainee is required")
    if data.trainer_id in data.trainee_ids:
        raise ValueError("The Trainer cannot also be listed as a Trainee")
    if data.end_date < data.start_date:
        raise ValueError("End date cannot be before the start date")

    user_ids = set(data.trainee_ids) | {data.trainer_id, data.bu_head_id}
    result = await hrms_db.execute(select(HrmsUserEntity).where(HrmsUserEntity.id.in_(user_ids)))
    users_by_id = {u.id: u for u in result.scalars().all()}

    trainer = users_by_id.get(data.trainer_id)
    if trainer is None or trainer.role != Role.TEAM_MEMBER:
        raise ValueError("The Trainer must be a Team Member")

    bu_head = users_by_id.get(data.bu_head_id)
    if bu_head is None or bu_head.role != Role.BU_HEAD:
        raise ValueError("The approver must be a BU Head")

    for trainee_id in data.trainee_ids:
        trainee = users_by_id.get(trainee_id)
        if trainee is None or trainee.role != Role.TEAM_MEMBER:
            raise ValueError(f"Trainee {trainee_id} must be a Team Member")

    # assessment_given_by only means anything when has_assessment=True - default to the
    # prior-only behavior (TRAINER) if enabled but not specified, and force null when
    # assessment isn't enabled at all so the two fields never disagree.
    assessment_given_by = None
    if data.has_assessment:
        assessment_given_by = data.assessment_given_by or AssessmentGivenBy.TRAINER.value

    now = datetime.utcnow()
    entity = TrainingProgramEntity(
        topic=data.topic,
        description=data.description,
        account_id=data.account_id,
        trainer_id=data.trainer_id,
        bu_head_id=data.bu_head_id,
        status=TrainingStatus.PENDING_APPROVAL.value,
        has_assessment=data.has_assessment,
        assessment_given_by=assessment_given_by,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    hrms_db.add(entity)
    await hrms_db.flush()

    for trainee_id in data.trainee_ids:
        hrms_db.add(TrainingTraineeEntity(training_id=entity.id, trainee_id=trainee_id))

    await hrms_db.commit()
    await hrms_db.refresh(entity)

    await email_service.send_training_pending_approval_email(
        bu_head.email, bu_head.name, entity.topic, trainer.name, entity.id
    )

    return await _to_response(hrms_db, kms_db, entity)


async def list_trainings(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, page_number: int, page_size: int
) -> PageResult:
    if current_user.role in (Role.ADMIN, Role.HR):
        stmt = select(TrainingProgramEntity)
    elif current_user.role == Role.BU_HEAD:
        stmt = select(TrainingProgramEntity).where(TrainingProgramEntity.bu_head_id == current_user.id)
    else:
        trainee_subq = select(TrainingTraineeEntity.training_id).where(
            TrainingTraineeEntity.trainee_id == current_user.id
        )
        stmt = select(TrainingProgramEntity).where(
            TrainingProgramEntity.status != TrainingStatus.PENDING_APPROVAL.value,
            or_(
                TrainingProgramEntity.trainer_id == current_user.id,
                TrainingProgramEntity.id.in_(trainee_subq),
            ),
        )
    stmt = stmt.order_by(TrainingProgramEntity.id.desc())
    page_result = await paginate(hrms_db, stmt, page_number, page_size)

    trainings = page_result.items
    training_ids = [t.id for t in trainings]
    user_ids = {t.trainer_id for t in trainings} | {t.bu_head_id for t in trainings}
    account_ids = {t.account_id for t in trainings if t.account_id}

    names = await _user_names(hrms_db, user_ids)
    accounts = await _account_names(kms_db, account_ids)
    trainee_counts = await _trainee_counts(hrms_db, training_ids)

    page_result.items = [
        {
            "id": t.id,
            "topic": t.topic,
            "account": accounts.get(t.account_id),
            "trainer_id": t.trainer_id,
            "trainer_name": names.get(t.trainer_id, "Unknown"),
            "bu_head_id": t.bu_head_id,
            "bu_head_name": names.get(t.bu_head_id, "Unknown"),
            "status": t.status,
            "has_assessment": t.has_assessment,
            "start_date": t.start_date,
            "end_date": t.end_date,
            "trainee_count": trainee_counts.get(t.id, 0),
        }
        for t in trainings
    ]
    return page_result


async def get_training(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int
) -> TrainingResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or not await _is_participant(hrms_db, current_user, entity):
        return None
    return await _to_response(hrms_db, kms_db, entity)


async def approve_training(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int
) -> TrainingResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.bu_head_id != current_user.id or entity.status != TrainingStatus.PENDING_APPROVAL.value:
        return None
    entity.status = TrainingStatus.APPROVED.value
    entity.approved_at = datetime.utcnow()
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)

    trainee_ids = await _trainee_ids(hrms_db, entity.id)
    recipients_result = await hrms_db.execute(
        select(HrmsUserEntity).where(HrmsUserEntity.id.in_({entity.trainer_id, *trainee_ids}))
    )
    for recipient in recipients_result.scalars().all():
        await email_service.send_training_approved_email(recipient.email, recipient.name, entity.topic, entity.id)

    return await _to_response(hrms_db, kms_db, entity)


async def reject_training(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int, reason: str | None
) -> TrainingResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.bu_head_id != current_user.id or entity.status != TrainingStatus.PENDING_APPROVAL.value:
        return None
    entity.status = TrainingStatus.REJECTED.value
    entity.rejection_reason = reason
    entity.rejected_at = datetime.utcnow()
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)

    recipients_result = await hrms_db.execute(
        select(HrmsUserEntity).where(HrmsUserEntity.id.in_({entity.trainer_id, entity.created_by}))
    )
    for recipient in recipients_result.scalars().all():
        await email_service.send_training_rejected_email(recipient.email, recipient.name, entity.topic, reason, entity.id)
    return await _to_response(hrms_db, kms_db, entity)


async def mark_completed(
    hrms_db: AsyncSession, kms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int
) -> TrainingResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.trainer_id != current_user.id or entity.status != TrainingStatus.APPROVED.value:
        return None
    entity.status = TrainingStatus.COMPLETED.value
    entity.completed_at = datetime.utcnow()
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)

    creator = await hrms_db.get(HrmsUserEntity, entity.created_by)
    if creator:
        await email_service.send_training_completed_email(creator.email, entity.topic, current_user.name, entity.id)

    return await _to_response(hrms_db, kms_db, entity)


async def add_day_entry(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int, data: DayEntryCreateRequest
) -> DayEntryResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.trainer_id != current_user.id or entity.status != TrainingStatus.APPROVED.value:
        return None
    day_entry = TrainingDayEntryEntity(
        training_id=training_id,
        entry_date=data.entry_date,
        topic_covered=data.topic_covered,
        status=data.status,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    hrms_db.add(day_entry)
    await hrms_db.commit()
    await hrms_db.refresh(day_entry)
    return DayEntryResponse(
        id=day_entry.id,
        training_id=day_entry.training_id,
        entry_date=day_entry.entry_date,
        topic_covered=day_entry.topic_covered,
        status=day_entry.status,
        created_by=day_entry.created_by,
        created_by_name=current_user.name,
        created_at=day_entry.created_at,
    )


async def list_day_entries(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int
) -> list[DayEntryResponse] | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or not await _is_participant(hrms_db, current_user, entity):
        return None
    result = await hrms_db.execute(
        select(TrainingDayEntryEntity)
        .where(TrainingDayEntryEntity.training_id == training_id)
        .order_by(TrainingDayEntryEntity.entry_date, TrainingDayEntryEntity.id)
    )
    entries = result.scalars().all()
    names = await _user_names(hrms_db, {e.created_by for e in entries})
    return [
        DayEntryResponse(
            id=e.id,
            training_id=e.training_id,
            entry_date=e.entry_date,
            topic_covered=e.topic_covered,
            status=e.status,
            created_by=e.created_by,
            created_by_name=names.get(e.created_by, "Unknown"),
            created_at=e.created_at,
        )
        for e in entries
    ]


async def add_comment(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int, data: CommentCreateRequest
) -> CommentResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or not await _is_trainer_or_trainee(hrms_db, current_user, entity):
        return None
    comment = TrainingCommentEntity(
        training_id=training_id,
        author_id=current_user.id,
        comment=data.comment,
        created_at=datetime.utcnow(),
    )
    hrms_db.add(comment)
    await hrms_db.commit()
    await hrms_db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        training_id=comment.training_id,
        author_id=comment.author_id,
        author_name=current_user.name,
        comment=comment.comment,
        created_at=comment.created_at,
    )


async def list_comments(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int
) -> list[CommentResponse] | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or not await _is_participant(hrms_db, current_user, entity):
        return None
    result = await hrms_db.execute(
        select(TrainingCommentEntity)
        .where(TrainingCommentEntity.training_id == training_id)
        .order_by(TrainingCommentEntity.created_at, TrainingCommentEntity.id)
    )
    comments = result.scalars().all()
    names = await _user_names(hrms_db, {c.author_id for c in comments})
    return [
        CommentResponse(
            id=c.id,
            training_id=c.training_id,
            author_id=c.author_id,
            author_name=names.get(c.author_id, "Unknown"),
            comment=c.comment,
            created_at=c.created_at,
        )
        for c in comments
    ]


def _material_file_url(request: Request, material: TrainingMaterialEntity) -> str | None:
    if not material.file_path:
        return None
    return file_storage_service.build_public_url(request, f"training/{material.training_id}/{material.file_path}")


def _can_manage_materials(entity: TrainingProgramEntity) -> bool:
    """Materials can be attached once approved, and remain addable after completion
    (e.g. a wrap-up doc) - just never while pending approval or rejected."""
    return entity.status in (TrainingStatus.APPROVED.value, TrainingStatus.COMPLETED.value)


async def add_material_link(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    data: MaterialLinkCreateRequest,
) -> MaterialResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.trainer_id != current_user.id or not _can_manage_materials(entity):
        return None
    material = TrainingMaterialEntity(
        training_id=training_id,
        material_type=MaterialType.LINK.value,
        title=data.title,
        link_url=data.link_url,
        added_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    hrms_db.add(material)
    await hrms_db.commit()
    await hrms_db.refresh(material)
    return MaterialResponse(
        id=material.id,
        training_id=material.training_id,
        material_type=material.material_type,
        title=material.title,
        link_url=material.link_url,
        file_url=_material_file_url(request, material),
        added_by=material.added_by,
        added_by_name=current_user.name,
        created_at=material.created_at,
    )


async def add_material_document(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    title: str,
    content: bytes,
    original_filename: str,
) -> MaterialResponse | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or entity.trainer_id != current_user.id or not _can_manage_materials(entity):
        return None
    stored_name = file_storage_service.unique_filename(original_filename)
    await file_storage_service.save_file(
        file_storage_service.training_material_dir(training_id), stored_name, content
    )
    material = TrainingMaterialEntity(
        training_id=training_id,
        material_type=MaterialType.DOCUMENT.value,
        title=title,
        file_path=stored_name,
        added_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    hrms_db.add(material)
    await hrms_db.commit()
    await hrms_db.refresh(material)
    return MaterialResponse(
        id=material.id,
        training_id=material.training_id,
        material_type=material.material_type,
        title=material.title,
        link_url=material.link_url,
        file_url=_material_file_url(request, material),
        added_by=material.added_by,
        added_by_name=current_user.name,
        created_at=material.created_at,
    )


async def list_materials(
    hrms_db: AsyncSession, request: Request, current_user: CurrentHrmsUser, training_id: int
) -> list[MaterialResponse] | None:
    entity = await hrms_db.get(TrainingProgramEntity, training_id)
    if entity is None or not await _is_participant(hrms_db, current_user, entity):
        return None
    result = await hrms_db.execute(
        select(TrainingMaterialEntity)
        .where(TrainingMaterialEntity.training_id == training_id)
        .order_by(TrainingMaterialEntity.created_at, TrainingMaterialEntity.id)
    )
    materials = result.scalars().all()
    names = await _user_names(hrms_db, {m.added_by for m in materials})
    return [
        MaterialResponse(
            id=m.id,
            training_id=m.training_id,
            material_type=m.material_type,
            title=m.title,
            link_url=m.link_url,
            file_url=_material_file_url(request, m),
            added_by=m.added_by,
            added_by_name=names.get(m.added_by, "Unknown"),
            created_at=m.created_at,
        )
        for m in materials
    ]


def _assessment_file_url(request: Request, training_id: int, assessment_id: int, file_path: str | None) -> str | None:
    if not file_path:
        return None
    return file_storage_service.build_public_url(
        request, f"training/{training_id}/assessments/{assessment_id}/{file_path}"
    )


_TERMINAL_ASSESSMENT_STATUSES = (AssessmentStatus.SUCCESS.value, AssessmentStatus.FAILURE.value)


async def _to_assessment_response(
    hrms_db: AsyncSession, request: Request, entity: TrainingAssessmentEntity
) -> AssessmentResponse:
    user_ids = {entity.trainee_id, entity.created_by}
    if entity.reviewed_by:
        user_ids.add(entity.reviewed_by)
    names = await _user_names(hrms_db, user_ids)

    result = await hrms_db.execute(
        select(TrainingAssessmentScreenshotEntity)
        .where(TrainingAssessmentScreenshotEntity.assessment_id == entity.id)
        .order_by(TrainingAssessmentScreenshotEntity.created_at, TrainingAssessmentScreenshotEntity.id)
    )
    screenshots = result.scalars().all()

    return AssessmentResponse(
        id=entity.id,
        training_id=entity.training_id,
        trainee_id=entity.trainee_id,
        trainee_name=names.get(entity.trainee_id, "Unknown"),
        description=entity.description,
        detail_document_url=_assessment_file_url(request, entity.training_id, entity.id, entity.detail_document_path),
        status=entity.status,
        github_repo_url=entity.github_repo_url,
        project_zip_url=_assessment_file_url(request, entity.training_id, entity.id, entity.project_zip_path),
        marks=entity.marks,
        reviewed_by=entity.reviewed_by,
        reviewed_by_name=names.get(entity.reviewed_by, "Unknown") if entity.reviewed_by else None,
        reviewed_at=entity.reviewed_at,
        created_by=entity.created_by,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        screenshots=[
            ScreenshotResponse(
                id=s.id,
                file_url=file_storage_service.build_public_url(
                    request, f"training/{entity.training_id}/assessments/{entity.id}/{s.file_path}"
                ),
                created_at=s.created_at,
            )
            for s in screenshots
        ],
    )


async def create_assessment(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    trainee_id: int,
    description: str,
    detail_document_content: bytes | None,
    detail_document_filename: str | None,
) -> AssessmentResponse:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    if training is None or training.trainer_id != current_user.id:
        raise ValueError("Training not found or not yours to manage")
    if not training.has_assessment:
        raise ValueError("This training does not have assessment enabled")
    if training.assessment_given_by == AssessmentGivenBy.HR.value:
        raise ValueError("This training's assessment is given by HR, not the Trainer")
    if training.status != TrainingStatus.APPROVED.value:
        raise ValueError("Training must be approved before assessments can be given")
    if trainee_id not in await _trainee_ids(hrms_db, training_id):
        raise ValueError("That user is not a Trainee on this training")

    existing = await hrms_db.execute(
        select(TrainingAssessmentEntity).where(
            TrainingAssessmentEntity.training_id == training_id,
            TrainingAssessmentEntity.trainee_id == trainee_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("This Trainee already has an assessment")

    now = datetime.utcnow()
    entity = TrainingAssessmentEntity(
        training_id=training_id,
        trainee_id=trainee_id,
        description=description,
        status=AssessmentStatus.PENDING.value,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    hrms_db.add(entity)
    await hrms_db.flush()

    if detail_document_content and detail_document_filename:
        stored_name = file_storage_service.unique_filename(detail_document_filename)
        await file_storage_service.save_file(
            file_storage_service.training_assessment_dir(training_id, entity.id),
            stored_name,
            detail_document_content,
        )
        entity.detail_document_path = stored_name

    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_assessment_response(hrms_db, request, entity)


async def list_assessments(
    hrms_db: AsyncSession, request: Request, current_user: CurrentHrmsUser, training_id: int
) -> list[AssessmentResponse] | None:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    if training is None or not await _is_participant(hrms_db, current_user, training):
        return None

    stmt = select(TrainingAssessmentEntity).where(TrainingAssessmentEntity.training_id == training_id)
    is_trainee_only = (
        current_user.role not in (Role.ADMIN, Role.HR, Role.BU_HEAD) and current_user.id != training.trainer_id
    )
    if is_trainee_only:
        stmt = stmt.where(TrainingAssessmentEntity.trainee_id == current_user.id)
    stmt = stmt.order_by(TrainingAssessmentEntity.id)

    result = await hrms_db.execute(stmt)
    assessments = result.scalars().all()
    return [await _to_assessment_response(hrms_db, request, a) for a in assessments]


async def get_assessment(
    hrms_db: AsyncSession, request: Request, current_user: CurrentHrmsUser, training_id: int, assessment_id: int
) -> AssessmentResponse | None:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if training is None or entity is None or entity.training_id != training_id:
        return None
    is_admin_view = current_user.role in (Role.ADMIN, Role.HR, Role.BU_HEAD) or current_user.id == training.trainer_id
    if not is_admin_view and entity.trainee_id != current_user.id:
        return None
    return await _to_assessment_response(hrms_db, request, entity)


async def update_submission(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    assessment_id: int,
    data: AssessmentSubmissionUpdateRequest,
) -> AssessmentResponse | None:
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if (
        entity is None
        or entity.training_id != training_id
        or entity.trainee_id != current_user.id
        or entity.status in _TERMINAL_ASSESSMENT_STATUSES
    ):
        return None
    if data.github_repo_url is not None:
        entity.github_repo_url = data.github_repo_url
    if data.status is not None:
        entity.status = data.status
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_assessment_response(hrms_db, request, entity)


async def add_screenshot(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    assessment_id: int,
    content: bytes,
    original_filename: str,
) -> AssessmentResponse | None:
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if (
        entity is None
        or entity.training_id != training_id
        or entity.trainee_id != current_user.id
        or entity.status in _TERMINAL_ASSESSMENT_STATUSES
    ):
        return None
    stored_name = file_storage_service.unique_filename(original_filename)
    await file_storage_service.save_file(
        file_storage_service.training_assessment_dir(training_id, assessment_id), stored_name, content
    )
    hrms_db.add(
        TrainingAssessmentScreenshotEntity(
            assessment_id=assessment_id, file_path=stored_name, created_at=datetime.utcnow()
        )
    )
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_assessment_response(hrms_db, request, entity)


async def delete_screenshot(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, training_id: int, assessment_id: int, screenshot_id: int
) -> bool:
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if (
        entity is None
        or entity.training_id != training_id
        or entity.trainee_id != current_user.id
        or entity.status in _TERMINAL_ASSESSMENT_STATUSES
    ):
        return False
    screenshot = await hrms_db.get(TrainingAssessmentScreenshotEntity, screenshot_id)
    if screenshot is None or screenshot.assessment_id != assessment_id:
        return False
    file_storage_service.delete_file(
        file_storage_service.training_assessment_dir(training_id, assessment_id) / screenshot.file_path
    )
    await hrms_db.delete(screenshot)
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    return True


async def upload_project_zip(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    assessment_id: int,
    content: bytes,
    original_filename: str,
) -> AssessmentResponse | None:
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if (
        entity is None
        or entity.training_id != training_id
        or entity.trainee_id != current_user.id
        or entity.status in _TERMINAL_ASSESSMENT_STATUSES
    ):
        return None
    if entity.project_zip_path:
        file_storage_service.delete_file(
            file_storage_service.training_assessment_dir(training_id, assessment_id) / entity.project_zip_path
        )
    stored_name = file_storage_service.unique_filename(original_filename)
    await file_storage_service.save_file(
        file_storage_service.training_assessment_dir(training_id, assessment_id), stored_name, content
    )
    entity.project_zip_path = stored_name
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_assessment_response(hrms_db, request, entity)


async def review_assessment(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    assessment_id: int,
    data: AssessmentReviewRequest,
) -> AssessmentResponse | None:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    entity = await hrms_db.get(TrainingAssessmentEntity, assessment_id)
    if (
        training is None
        or entity is None
        or entity.training_id != training_id
        or training.trainer_id != current_user.id
        or entity.status != AssessmentStatus.READY_FOR_REVIEW.value
    ):
        return None
    entity.marks = data.marks
    entity.status = data.status
    entity.reviewed_by = current_user.id
    entity.reviewed_at = datetime.utcnow()
    entity.updated_at = datetime.utcnow()
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_assessment_response(hrms_db, request, entity)
