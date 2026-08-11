from app.core.constants import USER_TYPE_IDS, UserRole, UserType


def is_user_privileged(role: str, user_type_id: int | None) -> bool:
    """Mirrors UserUtils.isUserPrivileged: ADMIN/SUPER_ADMIN role, or MANAGEMENT user type,
    bypass the "restricted to own department/account" filtering used across user listing
    and content visibility."""
    if role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value):
        return True
    return user_type_id == USER_TYPE_IDS[UserType.MANAGEMENT]
