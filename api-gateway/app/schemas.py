from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProductCreate(BaseModel):
    marketplace: str
    title: str
    url: str | None = None
    marketplace_product_id: str | None = None


class SummaryResponse(BaseModel):
    product: dict[str, Any]
    reviews_count: int
    sentiment: dict[str, int]
    rating: dict[str, float]


class HealthResponse(BaseModel):
    status: str
