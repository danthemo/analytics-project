from __future__ import annotations

import os

from pydantic import BaseModel


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


class Settings(BaseModel):
    app_name: str = _env("APP_NAME", "api-gateway")
    app_port: int = int(_env("APP_PORT", "8000"))
    catalog_service_url: str = _env("CATALOG_SERVICE_URL", "http://catalog-service:8000")
    collector_service_url: str = _env("COLLECTOR_SERVICE_URL", "http://collector-service:8000")
    review_service_url: str = _env("REVIEW_SERVICE_URL", "http://review-service:8000")
    analysis_service_url: str = _env("ANALYSIS_SERVICE_URL", "http://analysis-service:8000")
    rating_service_url: str = _env("RATING_SERVICE_URL", "http://rating-service:8000")
    request_timeout_seconds: float = float(_env("API_GATEWAY_REQUEST_TIMEOUT_SECONDS", _env("REQUEST_TIMEOUT_SECONDS", "300")))


settings = Settings()
