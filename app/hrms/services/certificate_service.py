from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from fastapi import Request
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.deps import CurrentHrmsUser
from app.hrms.models.certificate import CertificateTemplateEntity, TrainingCertificateEntity
from app.hrms.models.task_assessment import AssigneeStatus, TaskAssigneeEntity, TaskEntity
from app.hrms.models.training import (
    AssessmentGivenBy,
    AssessmentStatus,
    TrainingAssessmentEntity,
    TrainingProgramEntity,
    TrainingStatus,
)
from app.hrms.schemas.certificate import CertificateIssueRequest, CertificateResponse, CertificateTemplateResponse
from app.hrms.services import file_storage_service
from app.hrms.services.training_service import _is_participant, _user_names


def _draw_centered_text(draw: "ImageDraw.ImageDraw", image_width: int, y: int, text: str, font) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (image_width - text_width) / 2
    draw.text((x, y), text, font=font, fill=(20, 20, 20))


def generate_certificate_image(template_path: Path, recipient_name: str, topic: str, issue_date: date) -> bytes:
    """Overlays the recipient name, training topic, and date onto the template image at
    reasonable centered, stacked positions scaled to the template's own dimensions -
    an approximation since the template's exact layout isn't known ahead of time."""
    with Image.open(template_path) as source:
        img = source.convert("RGB")

    draw = ImageDraw.Draw(img)
    width, height = img.size

    name_font = ImageFont.load_default(size=max(24, width // 18))
    subtitle_font = ImageFont.load_default(size=max(16, width // 32))
    date_font = ImageFont.load_default(size=max(14, width // 40))

    _draw_centered_text(draw, width, int(height * 0.52), recipient_name, name_font)
    _draw_centered_text(
        draw, width, int(height * 0.63), f'has successfully completed training on "{topic}"', subtitle_font
    )
    _draw_centered_text(draw, width, int(height * 0.76), issue_date.strftime("%B %d, %Y"), date_font)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


async def upload_template(
    hrms_db: AsyncSession, current_user: CurrentHrmsUser, content: bytes, original_filename: str
) -> CertificateTemplateEntity:
    stored_name = file_storage_service.unique_filename(original_filename)
    await file_storage_service.save_file(file_storage_service.certificate_template_dir(), stored_name, content)
    entity = CertificateTemplateEntity(file_path=stored_name, uploaded_by=current_user.id, created_at=datetime.utcnow())
    hrms_db.add(entity)
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return entity


async def get_current_template(hrms_db: AsyncSession) -> CertificateTemplateEntity | None:
    result = await hrms_db.execute(
        select(CertificateTemplateEntity)
        .order_by(CertificateTemplateEntity.created_at.desc(), CertificateTemplateEntity.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_template_response(
    hrms_db: AsyncSession, request: Request
) -> CertificateTemplateResponse | None:
    entity = await get_current_template(hrms_db)
    if entity is None:
        return None
    names = await _user_names(hrms_db, {entity.uploaded_by})
    file_url = file_storage_service.build_public_url(request, f"certificate-templates/{entity.file_path}")
    return CertificateTemplateResponse(
        id=entity.id,
        file_url=file_url,
        uploaded_by=entity.uploaded_by,
        uploaded_by_name=names.get(entity.uploaded_by, "Unknown"),
        created_at=entity.created_at,
    )


async def _to_certificate_response(
    hrms_db: AsyncSession, request: Request, entity: TrainingCertificateEntity
) -> CertificateResponse:
    names = await _user_names(hrms_db, {entity.trainee_id, entity.issued_by})
    file_url = file_storage_service.build_public_url(
        request, f"training/{entity.training_id}/certificates/{entity.generated_file_path}"
    )
    return CertificateResponse(
        id=entity.id,
        training_id=entity.training_id,
        trainee_id=entity.trainee_id,
        trainee_name=names.get(entity.trainee_id, "Unknown"),
        recipient_name=entity.recipient_name,
        topic=entity.topic,
        issue_date=entity.issue_date,
        file_url=file_url,
        issued_by=entity.issued_by,
        issued_by_name=names.get(entity.issued_by, "Unknown"),
        created_at=entity.created_at,
    )


async def issue_certificate(
    hrms_db: AsyncSession,
    request: Request,
    current_user: CurrentHrmsUser,
    training_id: int,
    data: CertificateIssueRequest,
) -> CertificateResponse:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    if training is None:
        raise ValueError("Training not found")
    if training.status != TrainingStatus.COMPLETED.value:
        raise ValueError("Training must be completed before issuing a certificate")

    if training.assessment_given_by == AssessmentGivenBy.HR.value:
        # HR-given trainings never get a TrainingAssessmentEntity row - eligibility
        # instead comes from a passed Task Assessment linked to this training.
        assignees_result = await hrms_db.execute(
            select(TaskAssigneeEntity)
            .join(TaskEntity, TaskAssigneeEntity.task_id == TaskEntity.id)
            .where(TaskEntity.training_id == training_id, TaskAssigneeEntity.trainee_id == data.trainee_id)
        )
        passed = any(
            a.passed and a.status in (AssigneeStatus.SUBMITTED.value, AssigneeStatus.AUTO_SUBMITTED.value)
            for a in assignees_result.scalars().all()
        )
        if not passed:
            raise ValueError("This Trainee's Task Assessment must be passed before a certificate can be issued")
    else:
        assessment_result = await hrms_db.execute(
            select(TrainingAssessmentEntity).where(
                TrainingAssessmentEntity.training_id == training_id,
                TrainingAssessmentEntity.trainee_id == data.trainee_id,
            )
        )
        assessment = assessment_result.scalar_one_or_none()
        if assessment is None or assessment.status != AssessmentStatus.SUCCESS.value:
            raise ValueError("This Trainee's assessment must be marked Success before a certificate can be issued")

    existing = await hrms_db.execute(
        select(TrainingCertificateEntity).where(
            TrainingCertificateEntity.training_id == training_id,
            TrainingCertificateEntity.trainee_id == data.trainee_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("A certificate has already been issued to this Trainee for this training")

    template = await get_current_template(hrms_db)
    if template is None:
        raise ValueError("No certificate template has been uploaded yet")

    template_path = file_storage_service.certificate_template_dir() / template.file_path
    image_bytes = generate_certificate_image(template_path, data.recipient_name, training.topic, data.issue_date)

    stored_name = file_storage_service.unique_filename(f"certificate-{data.trainee_id}.png")
    await file_storage_service.save_file(
        file_storage_service.training_certificate_dir(training_id), stored_name, image_bytes
    )

    entity = TrainingCertificateEntity(
        training_id=training_id,
        trainee_id=data.trainee_id,
        recipient_name=data.recipient_name,
        topic=training.topic,
        issue_date=data.issue_date,
        generated_file_path=stored_name,
        issued_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    hrms_db.add(entity)
    await hrms_db.commit()
    await hrms_db.refresh(entity)
    return await _to_certificate_response(hrms_db, request, entity)


async def list_certificates(
    hrms_db: AsyncSession, request: Request, current_user: CurrentHrmsUser, training_id: int
) -> list[CertificateResponse] | None:
    training = await hrms_db.get(TrainingProgramEntity, training_id)
    if training is None or not await _is_participant(hrms_db, current_user, training):
        return None
    result = await hrms_db.execute(
        select(TrainingCertificateEntity)
        .where(TrainingCertificateEntity.training_id == training_id)
        .order_by(TrainingCertificateEntity.id)
    )
    certificates = result.scalars().all()
    return [await _to_certificate_response(hrms_db, request, c) for c in certificates]
