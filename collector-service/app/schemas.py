from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    product_id: int
    marketplace: str
    query: str | None = None
    url: str | None = None
    marketplace_product_id: str | None = None


class NormalizedReview(BaseModel):
    marketplace_review_id: str | None = None
    text: str
    author: str | None = None
    source: str
    marketplace_rating: int | None = None
    published_at: datetime | None = None


class CollectResponse(BaseModel):
    product_id: int
    collected: int
    reviews: list[NormalizedReview]


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
