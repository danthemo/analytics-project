from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.http_client import ServiceClient
from app.schemas import HealthResponse, ProductCreate, SummaryResponse


app = FastAPI(title=settings.app_name, version="1.0.0")

catalog_client = ServiceClient(settings.catalog_service_url, settings.request_timeout_seconds)
collector_client = ServiceClient(settings.collector_service_url, settings.request_timeout_seconds)
review_client = ServiceClient(settings.review_service_url, settings.request_timeout_seconds)
analysis_client = ServiceClient(settings.analysis_service_url, settings.request_timeout_seconds)
rating_client = ServiceClient(settings.rating_service_url, settings.request_timeout_seconds)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/products")
def create_product(payload: ProductCreate) -> dict:
    return catalog_client.post("/products", json=payload.model_dump())


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    return catalog_client.get(f"/products/{product_id}")


@app.post("/products/{product_id}/collect")
def collect_product_reviews(product_id: int) -> dict:
    product = catalog_client.get(f"/products/{product_id}")
    collected = collector_client.post(
        "/collect",
        json={
            "product_id": product_id,
            "marketplace": product["marketplace"],
            "query": product["title"],
            "url": product.get("url"),
            "marketplace_product_id": product.get("marketplace_product_id"),
        },
    )
    saved = review_client.post(
        "/reviews/bulk",
        json={
            "product_id": product_id,
            "reviews": collected["reviews"],
        },
    )
    return {
        "product_id": product_id,
        "collected": collected["collected"],
        "saved": saved["inserted"],
        "skipped_duplicates": saved["skipped_duplicates"],
    }


@app.post("/products/{product_id}/analyze")
def analyze_product(product_id: int, force: bool = False) -> dict:
    return analysis_client.post(f"/analyze/product/{product_id}", params={"force": str(force).lower()})


@app.post("/products/{product_id}/rating")
def calculate_product_rating(product_id: int) -> dict:
    return rating_client.post(f"/rating/product/{product_id}")


@app.get("/products/{product_id}/summary", response_model=SummaryResponse)
def get_product_summary(product_id: int) -> SummaryResponse:
    product = catalog_client.get(f"/products/{product_id}")
    reviews = review_client.get(f"/products/{product_id}/reviews")
    rating = rating_client.get(f"/rating/product/{product_id}")
    return SummaryResponse(
        product=product,
        reviews_count=reviews["count"],
        sentiment={
            "positive": rating["positive_count"],
            "neutral": rating["neutral_count"],
            "negative": rating["negative_count"],
        },
        rating={
            "sentiment_score": rating["sentiment_score"],
            "bayesian_score": rating["bayesian_score"],
            "final_rating": rating["final_rating"],
        },
    )
