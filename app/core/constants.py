from enum import Enum


class UserRole(str, Enum):
    """Login-as role. Lower id == more privileged (mirrors Java UserRole enum)."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


ROLE_IDS: dict[UserRole, int] = {
    UserRole.SUPER_ADMIN: 1,
    UserRole.ADMIN: 2,
    UserRole.USER: 3,
}


class UserType(str, Enum):
    """Distinct from UserRole - mirrors Java model.UserType enum."""

    EMPLOYEE = "EMPLOYEE"
    MANAGEMENT = "MANAGEMENT"
    CUSTOMER = "CUSTOMER"


USER_TYPE_IDS: dict[UserType, int] = {
    UserType.EMPLOYEE: 1,
    UserType.MANAGEMENT: 2,
    UserType.CUSTOMER: 3,
}

# Sentinel id representing "All" / unassigned department or account.
SENTINEL_ID = 0

DEFAULT_PASSWORD = "password"

# Content-type Apache POI / openpyxl expect for .xlsx imports.
EXCEL_SHEET_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

CONFIDENTIAL_DEPARTMENT_NAME = "Confidential"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_ERROR = "ERROR"
