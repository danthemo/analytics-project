from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewIn(BaseModel):
    marketplace_review_id: str | None = None
    text: str
    author: str | None = None
    source: str
    marketplace_rating: int | None = None
    published_at: datetime | None = None


class BulkReviewsCreate(BaseModel):
    product_id: int
    reviews: list[ReviewIn]


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    marketplace_review_id: str | None
    text: str
    author: str | None
    source: str
    marketplace_rating: int | None
    published_at: datetime | None
    created_at: datetime


class BulkReviewsResponse(BaseModel):
    product_id: int
    received: int
    inserted: int
    skipped_duplicates: int
    reviews: list[ReviewResponse]


class ProductReviewsResponse(BaseModel):
    product_id: int
    count: int
    reviews: list[ReviewResponse]


class HealthResponse(BaseModel):
    status: str
