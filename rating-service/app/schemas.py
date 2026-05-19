from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RatingResponse(BaseModel):
    product_id: int
    positive_count: int
    neutral_count: int
    negative_count: int
    total_reviews: int
    sentiment_score: float
    bayesian_score: float
    final_rating: float
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HealthResponse(BaseModel):
    status: str
