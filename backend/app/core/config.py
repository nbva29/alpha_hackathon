from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Alfa Smart Credit API"
    database_url: str = "sqlite:///./alfa_demo.db"
    secret_key: str = "change-me-before-deployment-please-32-chars-min"
    session_hours: int = 8
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8080,http://127.0.0.1:8080"
    )

    # Локальный запуск по умолчанию. Docker Compose переопределяет адрес на http://bank-mock:8001.
    bank_mock_url: str = "http://127.0.0.1:8001"
    bank_internal_key: str = "local-bank-mock-key-change-me"

    upload_dir: str = "./uploads"
    max_upload_bytes: int = 1_048_576
    demo_seed_password: str = "demo123"


settings = Settings()
