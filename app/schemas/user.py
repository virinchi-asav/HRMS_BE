from pydantic import BaseModel


class UserTypeResponse(BaseModel):
    """The EMPLOYEE/MANAGEMENT/CUSTOMER content-visibility lookup list - the one piece
    of the old KMS user schema surface that survived the single-login unification."""

    model_config = {"from_attributes": True}

    id: int
    name: str
