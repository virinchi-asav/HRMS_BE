from datetime import datetime

from pydantic import BaseModel


class TestimonialResponse(BaseModel):
    """The live table has no content columns beyond id/timestamps - see
    TestimonialEntity's docstring. Kept minimal and honest rather than inventing fields."""

    model_config = {"from_attributes": True}

    id: int
    created_at: datetime | None = None
