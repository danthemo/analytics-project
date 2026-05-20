from __future__ import annotations

import os

from pydantic import BaseModel


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


class Settings(BaseModel):
    app_name: str = _env("APP_NAME", "collector-service")
    app_port: int = int(_env("APP_PORT", "8000"))
    ozon_parser_url: str = _env("OZON_PARSER_URL", "http://ozon-parser:8001/parse/ozon")
    yandex_market_parser_url: str = _env("YANDEX_MARKET_PARSER_URL", "http://yandex-market-parser:8002/parse/yandex-market")
    request_timeout_seconds: float = float(_env("COLLECTOR_REQUEST_TIMEOUT_SECONDS", _env("REQUEST_TIMEOUT_SECONDS", "240")))


settings = Settings()
