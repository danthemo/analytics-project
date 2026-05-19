from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import settings
from app.model import SentimentAnalyzer
from app.review_client import ReviewServiceClient
from app.schemas import (
    AnalyzeProductResponse,
    AnalyzeReviewRequest,
    AnalyzeReviewResponse,
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    HealthResponse,
)
from shared.database import SessionLocal
from shared.init_db import init_db
from shared.models import ReviewAnalysis


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    analyzer = SentimentAnalyzer(settings.model_dir)
    review_client = ReviewServiceClient(
        base_url=settings.review_service_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    _.state.analyzer = analyzer
    _.state.review_client = review_client
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_dir=settings.model_dir,
    )


@app.post("/api/v1/analyze", response_model=AnalyzeTextResponse)
def analyze_text(request: AnalyzeTextRequest) -> AnalyzeTextResponse:
    prediction = app.state.analyzer.predict(request.text)
    return AnalyzeTextResponse(
        sentiment_class=prediction.sentiment_class,
        confidence=prediction.confidence,
        probabilities=prediction.probabilities,
    )


@app.post("/analyze/review", response_model=AnalyzeReviewResponse)
def analyze_review(request: AnalyzeReviewRequest) -> AnalyzeReviewResponse:
    prediction = app.state.analyzer.predict(request.text)
    with SessionLocal() as db:
        _upsert_analysis(
            db=db,
            review_id=request.review_id,
            sentiment=prediction.sentiment_class,
            confidence=prediction.confidence,
        )
    return AnalyzeReviewResponse(
        review_id=request.review_id,
        sentiment=prediction.sentiment_class,
        confidence=prediction.confidence,
    )


@app.post("/analyze/product/{product_id}", response_model=AnalyzeProductResponse)
def analyze_product(product_id: int, force: bool = False) -> AnalyzeProductResponse:
    all_reviews = app.state.review_client.get_product_reviews(product_id, exclude_analyzed=False)
    reviews = all_reviews if force else app.state.review_client.get_product_reviews(product_id, exclude_analyzed=True)
    skipped = 0 if force else max(len(all_reviews) - len(reviews), 0)
    results: list[AnalyzeReviewResponse] = []

    with SessionLocal() as db:
        for review in reviews:
            prediction = app.state.analyzer.predict(review["text"])
            _upsert_analysis(
                db=db,
                review_id=review["id"],
                sentiment=prediction.sentiment_class,
                confidence=prediction.confidence,
            )
            results.append(
                AnalyzeReviewResponse(
                    review_id=review["id"],
                    sentiment=prediction.sentiment_class,
                    confidence=prediction.confidence,
                )
            )

    return AnalyzeProductResponse(
        product_id=product_id,
        analyzed=len(results),
        skipped=skipped,
        results=results,
    )


def _upsert_analysis(db: Session, review_id: int, sentiment: str, confidence: float) -> None:
    existing = db.query(ReviewAnalysis).filter(ReviewAnalysis.review_id == review_id).first()
    if existing:
        existing.sentiment = sentiment
        existing.confidence = confidence
    else:
        db.add(
            ReviewAnalysis(
                review_id=review_id,
                sentiment=sentiment,
                confidence=confidence,
            )
        )
    db.commit()
