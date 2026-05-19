from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.init_db import init_db
from shared.models import Product, Rating, Review, ReviewAnalysis

from app.domain.rating_calculator import RatingResult, calculate_rating
from app.schemas import HealthResponse, RatingResponse


app = FastAPI(title="rating-service", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/rating/product/{product_id}", response_model=RatingResponse)
def calculate_product_rating(product_id: int, db: Session = Depends(get_db)) -> RatingResponse:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    counts = _count_sentiments(db, product_id)
    try:
        result = calculate_rating(**counts)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    rating = db.query(Rating).filter(Rating.product_id == product_id).first()
    if not rating:
        rating = Rating(product_id=product_id, **_result_to_db_kwargs(result))
        db.add(rating)
    else:
        for key, value in _result_to_db_kwargs(result).items():
            setattr(rating, key, value)

    db.commit()
    db.refresh(rating)
    return _to_response(rating)


@app.get("/rating/product/{product_id}", response_model=RatingResponse)
def get_product_rating(product_id: int, db: Session = Depends(get_db)) -> RatingResponse:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rating = db.query(Rating).filter(Rating.product_id == product_id).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return _to_response(rating)


def _count_sentiments(db: Session, product_id: int) -> dict[str, int]:
    rows = (
        db.query(ReviewAnalysis.sentiment)
        .join(Review, Review.id == ReviewAnalysis.review_id)
        .filter(Review.product_id == product_id)
        .all()
    )
    counts = {"positive_count": 0, "neutral_count": 0, "negative_count": 0}
    for (sentiment,) in rows:
        if sentiment == "positive":
            counts["positive_count"] += 1
        elif sentiment == "neutral":
            counts["neutral_count"] += 1
        elif sentiment == "negative":
            counts["negative_count"] += 1
    return counts


def _result_to_db_kwargs(result: RatingResult) -> dict[str, int | float]:
    return {
        "positive_count": result.positive_count,
        "neutral_count": result.neutral_count,
        "negative_count": result.negative_count,
        "total_reviews": result.total_reviews,
        "sentiment_score": result.sentiment_score,
        "bayesian_score": result.bayesian_score,
        "final_rating": result.final_rating,
    }


def _to_response(rating: Rating) -> RatingResponse:
    return RatingResponse(
        product_id=rating.product_id,
        positive_count=rating.positive_count,
        neutral_count=rating.neutral_count,
        negative_count=rating.negative_count,
        total_reviews=rating.total_reviews,
        sentiment_score=float(rating.sentiment_score),
        bayesian_score=float(rating.bayesian_score),
        final_rating=float(rating.final_rating),
        created_at=rating.created_at,
        updated_at=rating.updated_at,
    )
