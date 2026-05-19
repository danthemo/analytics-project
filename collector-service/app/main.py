from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
import httpx

from app.config import settings
from app.schemas import CollectRequest, CollectResponse, HealthResponse
from parsers.http_parser_adapter import HttpParserAdapter
from parsers.wildberries import WildberriesAdapter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="1.0.0")

wildberries_adapter = WildberriesAdapter(timeout_seconds=settings.request_timeout_seconds)
ozon_adapter = HttpParserAdapter(
    source_name="ozon",
    parser_url=settings.ozon_parser_url,
    timeout_seconds=settings.request_timeout_seconds,
)
yandex_market_adapter = HttpParserAdapter(
    source_name="yandex_market",
    parser_url=settings.yandex_market_parser_url,
    timeout_seconds=settings.request_timeout_seconds,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/collect", response_model=CollectResponse)
async def collect_reviews(payload: CollectRequest) -> CollectResponse:
    marketplace = payload.marketplace.strip().lower()
    try:
        if marketplace == "wildberries":
            reviews = await wildberries_adapter.collect(
                query=payload.query,
                url=payload.url,
                marketplace_product_id=payload.marketplace_product_id,
            )
        elif marketplace == "ozon":
            if not payload.query:
                raise ValueError("query is required for ozon collection")
            reviews = await ozon_adapter.collect(query=payload.query, url=payload.url)
        elif marketplace in {"yandex", "yandex_market", "yandex-market"}:
            if not payload.query:
                raise ValueError("query is required for yandex market collection")
            reviews = await yandex_market_adapter.collect(query=payload.query, url=payload.url)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported marketplace: {marketplace}")
    except httpx.HTTPStatusError as exc:  # type: ignore[name-defined]
        logger.exception("collector upstream error")
        raise HTTPException(status_code=502, detail=f"Collector upstream error: {exc.response.status_code}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("collector failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "collected product_id=%s marketplace=%s reviews=%s",
        payload.product_id,
        marketplace,
        len(reviews),
    )
    return CollectResponse(product_id=payload.product_id, collected=len(reviews), reviews=reviews)
