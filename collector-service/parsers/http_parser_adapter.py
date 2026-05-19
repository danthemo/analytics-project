from __future__ import annotations

import hashlib
from datetime import datetime

import httpx

from app.schemas import NormalizedReview


class HttpParserAdapter:
    def __init__(self, source_name: str, parser_url: str, timeout_seconds: float) -> None:
        self.source_name = source_name
        self.parser_url = parser_url
        self.timeout_seconds = timeout_seconds

    async def collect(self, query: str, url: str | None = None) -> list[NormalizedReview]:
        payload = {"query": query}
        if url:
            payload["product_url"] = url

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.parser_url, json=payload)
            response.raise_for_status()
            data = response.json()

        reviews: list[NormalizedReview] = []
        for item in data.get("reviews", []):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            reviews.append(
                NormalizedReview(
                    marketplace_review_id=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    text=text,
                    author=item.get("author"),
                    source=self.source_name,
                    marketplace_rating=_to_int(item.get("marketplace_rating")),
                    published_at=_to_datetime(item.get("published_at")),
                )
            )
        return reviews


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
