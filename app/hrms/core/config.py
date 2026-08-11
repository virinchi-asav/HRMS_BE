from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class HrmsSettings(BaseSettings):
    """Config for the HRMS (recruitment/employee-management) module - a separate MySQL
    database from the KMS module's, matching the ported Laravel app's own
    `mksvision_mkswebsite_new` MySQL database. All env vars are prefixed HRMS_ to stay
    distinct from the KMS module's settings in app/core/config.py."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    hrms_db_host: str = "127.0.0.1"
    hrms_db_port: int = 3306
    hrms_db_name: str = "mksvision_mkswebsite_new"
    hrms_db_user: str = "root"
    hrms_db_password: str = ""
    hrms_db_echo: bool = False

    # Full connection string override - set this to point BOTH the running app and
    # Alembic at any SQLAlchemy-supported database/dialect (e.g. a
    # postgresql+asyncpg://... URL for a Neon copy) instead of the discrete hrms_db_*
    # fields above, which only ever build a mysql+asyncmy:// URL. Leave unset to keep
    # using MySQL via those fields - this is the one knob to turn to "swap the
    # database" for a fresh environment, no code changes needed either way.
    hrms_database_url: str | None = None

    # JWT (reuses the same HS512 scheme as the KMS module, but a separate secret/claims
    # since this is a distinct user base with a different role model)
    hrms_jwt_secret: str = "changeme-hrms-secret"
    hrms_jwt_expiration_minutes: int = 120

    # File storage - mirrors Laravel's public_path('uploads') conventions
    hrms_upload_root: str = "./hrms_uploads"

    # Default password assigned to admin-created users (mirrors Laravel's Welcome@123)
    hrms_default_password: str = "Welcome@123"

    # SMTP (replaces Laravel's Mail facade - MAIL_MAILER=smtp in the Laravel .env)
    hrms_smtp_host: str = "smtp-mail.outlook.com"
    hrms_smtp_port: int = 587
    hrms_smtp_username: str = ""
    hrms_smtp_password: str = ""
    hrms_smtp_use_tls: bool = True
    hrms_mail_from_address: str = "noreply@mksvision.com"
    hrms_mail_from_name: str = "MKS HRMS"

    # Notification recipients (were hardcoded in the Laravel app - now configurable)
    hrms_candidate_submission_notify_email: str = ""
    hrms_profile_update_notify_email: str = ""
    hrms_onboarding_notify_email: str = "hr@mksvision.com"

    # Shared-secret for the HR-system webhook endpoints (the Laravel routes had NO auth
    # at all on these - this closes that gap)
    hrms_webhook_api_key: str = "changeme-webhook-key"

    # Public frontend base URL, used to build links in emails (survey links, etc.)
    hrms_frontend_base_url: str = "http://localhost:5173"

    # Password reset token expiry (matches Laravel config/auth.php: passwords.users.expire = 60)
    hrms_password_reset_expiry_minutes: int = 60

    # Comma-separated list of valid "work location" values for the Users module -
    # kept here (rather than a DB table) since the list is small and rarely changes.
    hrms_work_locations: str = "Hyderabad,Coimbatore"

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.hrms_database_url:
            return self.hrms_database_url
        return (
            f"mysql+asyncmy://{self.hrms_db_user}:{self.hrms_db_password}"
            f"@{self.hrms_db_host}:{self.hrms_db_port}/{self.hrms_db_name}"
        )

    @property
    def sqlalchemy_connect_args(self) -> dict:
        """Neon (and most managed Postgres) requires TLS; asyncpg wants this passed as a
        connect arg rather than a "sslmode"-style URL query param (that's libpq syntax,
        not something asyncpg's connect() understands). MySQL needs nothing extra."""
        if self.sqlalchemy_database_uri.startswith("postgresql+asyncpg"):
            return {"ssl": "require"}
        return {}

    @property
    def work_locations(self) -> list[str]:
        return [loc.strip() for loc in self.hrms_work_locations.split(",") if loc.strip()]


@lru_cache
def get_hrms_settings() -> HrmsSettings:
    return HrmsSettings()


hrms_settings = get_hrms_settings()
