from __future__ import annotations

import asyncio
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
    marketplaces = _resolve_marketplaces(payload.marketplace)
    if not marketplaces:
        raise HTTPException(status_code=400, detail=f"Unsupported marketplace: {payload.marketplace}")

    if len(marketplaces) == 1:
        marketplace = marketplaces[0]
        try:
            reviews = await _collect_single_marketplace(payload, marketplace)
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
        return CollectResponse(
            product_id=payload.product_id,
            collected=len(reviews),
            requested_marketplaces=marketplaces,
            completed_marketplaces=marketplaces,
            reviews=reviews,
        )

    results = await asyncio.gather(
        *[_collect_marketplace_result(payload, marketplace) for marketplace in marketplaces]
    )

    reviews: list = []
    completed_marketplaces: list[str] = []
    failed_marketplaces: dict[str, str] = {}

    for marketplace, marketplace_reviews, error_message in results:
        if error_message:
            failed_marketplaces[marketplace] = error_message
            continue
        completed_marketplaces.append(marketplace)
        reviews.extend(marketplace_reviews)

    if not completed_marketplaces:
        details = "; ".join(f"{name}: {message}" for name, message in failed_marketplaces.items())
        raise HTTPException(status_code=502, detail=f"All marketplace collectors failed: {details}")

    logger.info(
        "collected product_id=%s marketplaces=%s reviews=%s failed=%s",
        payload.product_id,
        ",".join(completed_marketplaces),
        len(reviews),
        ",".join(failed_marketplaces.keys()),
    )
    return CollectResponse(
        product_id=payload.product_id,
        collected=len(reviews),
        requested_marketplaces=marketplaces,
        completed_marketplaces=completed_marketplaces,
        failed_marketplaces=failed_marketplaces,
        reviews=reviews,
    )


async def _collect_marketplace_result(
    payload: CollectRequest,
    marketplace: str,
) -> tuple[str, list, str | None]:
    try:
        reviews = await _collect_single_marketplace(payload, marketplace)
        return marketplace, reviews, None
    except httpx.HTTPStatusError as exc:  # type: ignore[name-defined]
        logger.exception("collector upstream error for marketplace=%s", marketplace)
        return marketplace, [], f"upstream error: {exc.response.status_code}"
    except ValueError as exc:
        return marketplace, [], str(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("collector failed for marketplace=%s", marketplace)
        return marketplace, [], str(exc)


async def _collect_single_marketplace(payload: CollectRequest, marketplace: str) -> list:
    if marketplace == "wildberries":
        return await wildberries_adapter.collect(
            query=payload.query,
            url=payload.url,
            marketplace_product_id=payload.marketplace_product_id,
        )
    if marketplace == "ozon":
        if not payload.query:
            raise ValueError("query is required for ozon collection")
        return await ozon_adapter.collect(query=payload.query, url=payload.url)
    if marketplace == "yandex_market":
        if not payload.query:
            raise ValueError("query is required for yandex market collection")
        return await yandex_market_adapter.collect(query=payload.query, url=payload.url)
    raise ValueError(f"Unsupported marketplace: {marketplace}")


def _resolve_marketplaces(raw_marketplace: str) -> list[str]:
    marketplace = raw_marketplace.strip().lower()
    if marketplace in {"all", "all_marketplaces", "all-marketplaces", "multi"}:
        return ["wildberries", "ozon", "yandex_market"]
    if marketplace == "wildberries":
        return ["wildberries"]
    if marketplace == "ozon":
        return ["ozon"]
    if marketplace in {"yandex", "yandex_market", "yandex-market"}:
        return ["yandex_market"]
    return []
