from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


@dataclass
class PageResult:
    items: list[Any]
    total_elements: int
    total_pages: int
    page_number: int
    page_size: int


async def paginate(db: AsyncSession, stmt: Select, page_number: int, page_size: int) -> PageResult:
    """Mirrors Spring Data's PageRequest.of(pageNumber, pageSize) - 0-indexed page number."""
    page_size = max(page_size, 1)
    page_number = max(page_number, 0)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total_elements = (await db.execute(count_stmt)).scalar_one()

    result = await db.execute(stmt.limit(page_size).offset(page_number * page_size))
    items = list(result.scalars().all())

    total_pages = (total_elements + page_size - 1) // page_size if total_elements else 0
    return PageResult(
        items=items,
        total_elements=total_elements,
        total_pages=total_pages,
        page_number=page_number,
        page_size=page_size,
    )


def page_result_to_dict(page_result: PageResult, serialize: Callable[[Any], Any] = lambda x: x) -> dict:
    """Builds a dict matching the JSON shape of Spring Data's Page<T>, for direct return
    from a FastAPI route (avoids Pydantic Generic model plumbing)."""
    content = [serialize(item) for item in page_result.items]
    total_pages = page_result.total_pages
    return {
        "content": content,
        "totalElements": page_result.total_elements,
        "totalPages": total_pages,
        "size": page_result.page_size,
        "number": page_result.page_number,
        "numberOfElements": len(content),
        "first": page_result.page_number == 0,
        "last": (page_result.page_number >= total_pages - 1) if total_pages else True,
        "empty": len(content) == 0,
    }
