from dataclasses import dataclass
import os


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = _get_env("APP_NAME", "analysis-service")
    app_port: int = int(_get_env("APP_PORT", "8000"))
    model_dir: str = _get_env("MODEL_DIR", "/app/artifacts/model")
    review_service_url: str = _get_env("REVIEW_SERVICE_URL", "http://review-service:8000")
    request_timeout_seconds: float = float(_get_env("REQUEST_TIMEOUT_SECONDS", "30"))


settings = Settings()
