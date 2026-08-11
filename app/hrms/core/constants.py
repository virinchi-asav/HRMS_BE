from enum import IntEnum

from app.core.constants import UserRole


class Role(IntEnum):
    """Matches the `role` integer column on users, documented in the original Laravel
    migration comment: "1 - Admin, 2 - HR, 3 - Employee, 4 - Candidates". Roles 5-7 were
    added later without an equivalent comment but are consistently used across
    controllers/middleware as Manager/Team Member/BU Head.

    EMPLOYEE(3) is retired - unused in role assignment (new users default to
    TEAM_MEMBER) and had no live rows when removed, so the id is left as a permanent
    gap rather than renumbering everything after it."""

    ADMIN = 1
    HR = 2
    CANDIDATE = 4
    MANAGER = 5
    TEAM_MEMBER = 6
    BU_HEAD = 7


# Named role groups mirroring the exact `role:` middleware combinations found in the
# Laravel routes, so router-level access checks read the same way the routes did.
ADMIN_ONLY = {Role.ADMIN}
ADMIN_OR_HR = {Role.ADMIN, Role.HR}
ADMIN_MANAGER_BUHEAD = {Role.ADMIN, Role.MANAGER, Role.BU_HEAD}

# KMS module now authenticates via the HRMS JWT (single login) - this crosswalk maps
# each HRMS role to the KMS role it plays for KMS's own admin-vs-user gating logic
# (content-visibility scoping, dept/account upload locks, etc).
HRMS_TO_KMS_ROLE: dict[Role, UserRole] = {
    Role.ADMIN: UserRole.SUPER_ADMIN,
    Role.BU_HEAD: UserRole.ADMIN,
    Role.HR: UserRole.ADMIN,
    Role.MANAGER: UserRole.ADMIN,
    Role.TEAM_MEMBER: UserRole.USER,
    Role.CANDIDATE: UserRole.USER,
}

DEFAULT_PASSWORD = "Welcome@123"

EXCEL_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
}

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
