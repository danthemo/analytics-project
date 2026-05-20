from __future__ import annotations

import hashlib
import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import exists
from sqlalchemy.orm import Session, joinedload

from shared.database import get_db
from shared.init_db import init_db
from shared.models import Product, Review, ReviewAnalysis

from .schemas import (
    BulkReviewsCreate,
    BulkReviewsResponse,
    HealthResponse,
    ProductReviewsResponse,
    ReviewResponse,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="review-service", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def make_dedupe_key(product_id: int, marketplace_review_id: str | None, text: str) -> str:
    raw = marketplace_review_id or hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{product_id}:{raw}".encode("utf-8")).hexdigest()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/reviews/bulk", response_model=BulkReviewsResponse)
def create_reviews(payload: BulkReviewsCreate, db: Session = Depends(get_db)) -> BulkReviewsResponse:
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    inserted = 0
    skipped = 0
    stored_reviews: list[Review] = []

    for item in payload.reviews:
        dedupe_key = make_dedupe_key(payload.product_id, item.marketplace_review_id, item.text)
        existing = db.query(Review).filter(Review.product_id == payload.product_id, Review.dedupe_key == dedupe_key).first()
        if existing:
            skipped += 1
            stored_reviews.append(existing)
            continue

        review = Review(
            product_id=payload.product_id,
            marketplace_review_id=item.marketplace_review_id,
            dedupe_key=dedupe_key,
            text=item.text.strip(),
            author=item.author,
            source=item.source,
            marketplace_rating=item.marketplace_rating,
            published_at=item.published_at,
        )
        db.add(review)
        db.flush()
        stored_reviews.append(review)
        inserted += 1

    db.commit()
    for review in stored_reviews:
        db.refresh(review)

    logger.info(
        "stored reviews product_id=%s received=%s inserted=%s skipped=%s",
        payload.product_id,
        len(payload.reviews),
        inserted,
        skipped,
    )
    return BulkReviewsResponse(
        product_id=payload.product_id,
        received=len(payload.reviews),
        inserted=inserted,
        skipped_duplicates=skipped,
        reviews=stored_reviews,
    )


@app.get("/products/{product_id}/reviews", response_model=ProductReviewsResponse)
def get_product_reviews(
    product_id: int,
    exclude_analyzed: bool = Query(False),
    db: Session = Depends(get_db),
) -> ProductReviewsResponse:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = db.query(Review).options(joinedload(Review.analysis)).filter(Review.product_id == product_id)
    if exclude_analyzed:
        query = query.filter(~exists().where(ReviewAnalysis.review_id == Review.id))

    reviews = query.order_by(Review.id.asc()).all()
    return ProductReviewsResponse(
        product_id=product_id,
        count=len(reviews),
        reviews=[_to_review_response(review) for review in reviews],
    )


@app.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(review_id: int, db: Session = Depends(get_db)) -> Review:
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


def _to_review_response(review: Review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        product_id=review.product_id,
        marketplace_review_id=review.marketplace_review_id,
        text=review.text,
        author=review.author,
        source=review.source,
        marketplace_rating=review.marketplace_rating,
        published_at=review.published_at,
        created_at=review.created_at,
        sentiment=review.analysis.sentiment if review.analysis else None,
        confidence=review.analysis.confidence if review.analysis else None,
    )
