from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.client import ClientEntity
from app.hrms.models.survey import SurveyEntity
from app.hrms.schemas.survey import SurveySubmissionRequest
from app.utils.pagination import PageResult, paginate


async def get_client_by_username(db: AsyncSession, username: str) -> ClientEntity | None:
    """Mirrors SurveyController::clientSurveyForm - looked up by username only (the
    `{organization}`/`{id}` path segment in `survey/{id}/{name}` is captured but unused
    in the source app)."""
    result = await db.execute(select(ClientEntity).where(ClientEntity.username == username))
    return result.scalar_one_or_none()


async def submit_survey(db: AsyncSession, data: SurveySubmissionRequest) -> SurveyEntity:
    entity = SurveyEntity(
        customer_id=data.client_id,
        delivery=data.delivery,
        quality=data.quality,
        expertise=data.expertise,
        mksvalues=data.mksvalues,
        overallservicesatisfaction=data.overallservicesatisfaction,
        comments=data.comments,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def list_survey_results(db: AsyncSession, page_number: int, page_size: int, search: str | None) -> PageResult:
    """Mirrors ClientController::surveyResults - excludes surveys whose client was
    soft-deleted."""
    stmt = (
        select(SurveyEntity)
        .join(ClientEntity, ClientEntity.id == SurveyEntity.customer_id)
        .where(ClientEntity.deleted_at.is_(None))
    )
    if search:
        stmt = stmt.where(or_(ClientEntity.firstname.ilike(f"%{search}%"), ClientEntity.email.ilike(f"%{search}%")))
    stmt = stmt.order_by(SurveyEntity.id.desc())
    return await paginate(db, stmt, page_number, page_size)


async def export_surveys_xlsx(db: AsyncSession) -> bytes:
    """Mirrors SurveyExport."""
    import io

    import openpyxl

    result = await db.execute(select(SurveyEntity).order_by(SurveyEntity.id))
    surveys = result.scalars().unique().all()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(
        ["#", "Name", "Email", "Organization", "Delivery", "Quality", "Expertise", "Values",
         "Overall Satisfactions", "Comments", "Avg Score", "Submitted On"]
    )
    for survey in surveys:
        client = await db.get(ClientEntity, survey.customer_id)
        scores = [survey.delivery, survey.quality, survey.expertise, survey.mksvalues, survey.overallservicesatisfaction]
        sheet.append([
            survey.id,
            client.firstname if client else None,
            client.email if client else None,
            client.organization if client else None,
            survey.delivery,
            survey.quality,
            survey.expertise,
            survey.mksvalues,
            survey.overallservicesatisfaction,
            survey.comments or "NA",
            round(sum(scores) / 5, 2),
            survey.created_at.strftime("%d-%m-%Y") if survey.created_at else None,
        ])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
