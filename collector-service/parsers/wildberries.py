from __future__ import annotations

from datetime import datetime

import httpx

from app.schemas import NormalizedReview


WILDBERRIES_SEARCH_URL = "https://u-search.wb.ru/exactmatch/ru/common/v18/search"
WILDBERRIES_FEEDBACKS_URL = "https://feedbacks1.wb.ru/feedbacks/v2/{root}"


class WildberriesAdapter:
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    async def collect(
        self,
        query: str | None,
        url: str | None = None,
        marketplace_product_id: str | None = None,
    ) -> list[NormalizedReview]:
        product_root = await self._resolve_product_root(query=query, marketplace_product_id=marketplace_product_id)
        feedbacks_url = WILDBERRIES_FEEDBACKS_URL.format(root=product_root)

        headers = self._default_headers()
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            response = await client.get(feedbacks_url)
            response.raise_for_status()
            payload = response.json()

        feedbacks = payload.get("data", {}).get("feedbacks") or payload.get("feedbacks") or []
        reviews: list[NormalizedReview] = []
        for item in feedbacks:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            author = (
                item.get("userName")
                or item.get("author")
                or item.get("wbUserDetails", {}).get("name")
            )
            review_id = item.get("id")
            rating = item.get("productValuation") or item.get("productRating") or item.get("valuation")
            published_at = (
                item.get("createdDate")
                or item.get("createdAt")
                or item.get("publishedAt")
            )
            reviews.append(
                NormalizedReview(
                    marketplace_review_id=str(review_id) if review_id is not None else None,
                    text=text,
                    author=author,
                    source="wildberries",
                    marketplace_rating=_to_int(rating),
                    published_at=_to_datetime(published_at),
                )
            )

        return reviews

    async def _resolve_product_root(self, query: str | None, marketplace_product_id: str | None) -> int:
        if marketplace_product_id:
            try:
                return int(marketplace_product_id)
            except ValueError:
                pass

        if not query:
            raise ValueError("query is required for wildberries collection")

        params = {
            "ab_testid": "catboost_exp_2",
            "appType": "1",
            "curr": "rub",
            "dest": "1259570983",
            "hide_vflags": "4294967296",
            "inheritFilters": "false",
            "lang": "ru",
            "locale": "ru",
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
            "suppressSpellcheck": "false",
            "query": query,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self._default_headers()) as client:
            response = await client.get(WILDBERRIES_SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        products = payload.get("data", {}).get("products") or payload.get("products") or []
        if not products:
            raise ValueError("wildberries returned no products")

        root = products[0].get("root")
        if not root:
            raise ValueError("wildberries product root is missing")
        return int(root)

    @staticmethod
    def _default_headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.wildberries.ru/",
        }


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
