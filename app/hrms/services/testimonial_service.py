from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.testimonial import TestimonialEntity


async def list_testimonials(db: AsyncSession) -> list[TestimonialEntity]:
    result = await db.execute(select(TestimonialEntity).order_by(TestimonialEntity.id.desc()))
    return list(result.scalars().all())
