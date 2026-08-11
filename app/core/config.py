from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "lmsdev"
    db_user: str = "root"
    db_password: str = ""
    db_echo: bool = False

    # Full connection string override - set this to point BOTH the app and Alembic
    # (alembic.ini's chain) at any SQLAlchemy-supported database/dialect instead of the
    # discrete db_* fields above, which only ever build a mysql+asyncmy:// URL. Leave
    # unset to keep using MySQL via those fields. Mirrors HrmsSettings.hrms_database_url.
    database_url: str | None = None

    # Server
    server_port: int = 8084
    public_host: str = ""
    public_port: int = 0

    # File storage
    file_storage_root: str = r"E:\Java\MKS\LMSDEV\\"
    profile_images_path: str = r"E:\Java\MKS\LMSDEV\Profile Images"

    # JWT
    jwt_secret: str = "mksSecretKey"
    jwt_expiration_ms: int = 86400000

    # Uploads
    max_upload_size_bytes: int = 1024 * 1024 * 1024

    # Confidential file access (comma separated emails)
    confidential_file_users: str = ""

    # Microsoft Graph
    ms_graph_client_id: str = ""
    ms_graph_client_secret: str = ""
    ms_graph_tenant_id: str = ""
    from_email_id: str = ""

    # Password reset
    reset_password_link: str = ""
    reset_password_expiry_minutes: int = 15

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        # Built via URL.create (not an f-string) so special characters in db_user/
        # db_password - e.g. an "@" in the password - get percent-encoded instead of
        # corrupting the userinfo/host split.
        return URL.create(
            "mysql+asyncmy",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)

    @property
    def sqlalchemy_connect_args(self) -> dict:
        """Neon (and most managed Postgres) requires TLS; asyncpg wants this passed as a
        connect arg rather than a "sslmode"-style URL query param (that's libpq syntax,
        not something asyncpg's connect() understands). MySQL needs nothing extra."""
        if self.sqlalchemy_database_uri.startswith("postgresql+asyncpg"):
            return {"ssl": "require"}
        return {}

    @property
    def confidential_file_users_list(self) -> list[str]:
        return [e.strip() for e in self.confidential_file_users.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
