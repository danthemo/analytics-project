from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RatingResult:
    positive_count: int
    neutral_count: int
    negative_count: int
    total_reviews: int
    sentiment_score: float
    bayesian_score: float
    final_rating: float


def calculate_rating(
    positive_count: int,
    neutral_count: int,
    negative_count: int,
    m: int = 20,
    c: float = 0.5,
) -> RatingResult:
    total_reviews = positive_count + neutral_count + negative_count
    if total_reviews <= 0:
        raise ValueError("No analyzed reviews for product")

    sentiment_score = (positive_count + 0.5 * neutral_count) / total_reviews
    bayesian_score = (total_reviews / (total_reviews + m)) * sentiment_score + (m / (total_reviews + m)) * c
    final_rating = 1 + 4 * bayesian_score

    return RatingResult(
        positive_count=positive_count,
        neutral_count=neutral_count,
        negative_count=negative_count,
        total_reviews=total_reviews,
        sentiment_score=round(sentiment_score, 3),
        bayesian_score=round(bayesian_score, 3),
        final_rating=round(final_rating, 3),
    )
