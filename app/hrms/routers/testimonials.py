from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.deps import get_current_hrms_user, get_hrms_db
from app.hrms.schemas.testimonial import TestimonialResponse
from app.hrms.services import testimonial_service

router = APIRouter(prefix="/api/hrms/testimonials", tags=["hrms-testimonials"], dependencies=[Depends(get_current_hrms_user)])


@router.get("", response_model=list[TestimonialResponse])
async def list_testimonials(db: AsyncSession = Depends(get_hrms_db)):
    return await testimonial_service.list_testimonials(db)
