from app.core.constants import SENTINEL_ID


def is_valid_id(id_: int | None) -> bool:
    """Mirrors UserUtils.isValidId: an explicitly supplied, positive id."""
    return id_ is not None and id_ > 0


def is_invalid_id(id_: int | None) -> bool:
    """Mirrors UserUtils.isInValidId: an explicitly supplied, non-positive id.

    Note the Java naming is a bit odd - None ("not supplied") is NOT considered invalid
    by this check; only an explicit id <= 0 is.
    """
    return id_ is not None and id_ <= 0


def is_sentinel(id_: int | None) -> bool:
    """The id=0 'All'/unassigned sentinel used for department/account."""
    return id_ == SENTINEL_ID


def is_valid_field(value: str | None) -> bool:
    return value is not None and value.strip() != ""
