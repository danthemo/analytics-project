from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.http_client import ServiceClient
from app.schemas import HealthResponse, ProductAnalyzeRequest, ProductCreate, SummaryResponse


app = FastAPI(title=settings.app_name, version="1.0.0")

catalog_client = ServiceClient(settings.catalog_service_url, settings.request_timeout_seconds)
collector_client = ServiceClient(settings.collector_service_url, settings.request_timeout_seconds)
review_client = ServiceClient(settings.review_service_url, settings.request_timeout_seconds)
analysis_client = ServiceClient(settings.analysis_service_url, settings.request_timeout_seconds)
rating_client = ServiceClient(settings.rating_service_url, settings.request_timeout_seconds)

SENTIMENT_LABELS = ("positive", "neutral", "negative")
MARKETPLACE_ORDER = ("Ozon", "Wildberries", "Яндекс Маркет")
MARKETPLACE_LABELS = {
    "ozon": "Ozon",
    "wildberries": "Wildberries",
    "yandex": "Яндекс Маркет",
    "yandex_market": "Яндекс Маркет",
    "yandex-market": "Яндекс Маркет",
}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/products")
def create_product(payload: ProductCreate) -> dict:
    return _create_product(payload)


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    return _get_catalog_product(product_id)


@app.post("/products/{product_id}/collect")
def collect_product_reviews(product_id: int) -> dict:
    return _collect_product_reviews(product_id)


@app.post("/products/{product_id}/analyze")
def analyze_product(product_id: int, force: bool = False) -> dict:
    return _analyze_product(product_id, force=force)


@app.post("/products/{product_id}/rating")
def calculate_product_rating(product_id: int) -> dict:
    return _calculate_product_rating(product_id)


@app.delete("/products/{product_id}")
def delete_product(product_id: int) -> dict:
    return _delete_product(product_id)


@app.get("/products/{product_id}/summary", response_model=SummaryResponse)
def get_product_summary(product_id: int) -> SummaryResponse:
    product = _get_catalog_product(product_id)
    reviews = _get_product_reviews_payload(product_id)
    rating = _get_product_rating(product_id)
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


@app.get("/api/products")
def list_products_frontend() -> list[dict]:
    products = catalog_client.get("/products")
    return [_build_product_card(product) for product in products]


@app.post("/api/products/analyze")
def create_and_analyze_product(payload: ProductAnalyzeRequest) -> dict:
    product_name = payload.name.strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="Product name is required")

    created_product = _create_product(
        ProductCreate(
            marketplace="all",
            title=product_name,
        )
    )
    product_id = int(created_product["id"])
    _collect_product_reviews(product_id)
    _analyze_product(product_id, force=False)
    _calculate_product_rating(product_id)
    return _build_product_view(product_id)


@app.get("/api/products/{product_id}")
def get_product_frontend(product_id: int) -> dict:
    return _build_product_view(product_id)


@app.post("/api/products/{product_id}/refresh")
def refresh_product_frontend(product_id: int) -> dict:
    _collect_product_reviews(product_id)
    _analyze_product(product_id, force=True)
    _calculate_product_rating(product_id)
    return _build_product_view(product_id)


@app.delete("/api/products/{product_id}")
def delete_product_frontend(product_id: int) -> dict:
    return _delete_product(product_id)


@app.get("/api/products/{product_id}/reviews")
def get_product_reviews_frontend(product_id: int) -> list[dict]:
    reviews_payload = _get_product_reviews_payload(product_id)
    return [_map_review_to_frontend(review) for review in reviews_payload["reviews"]]


@app.get("/api/products/{product_id}/stats")
def get_product_stats_frontend(product_id: int) -> dict:
    product = _get_catalog_product(product_id)
    reviews_payload = _get_product_reviews_payload(product_id)
    rating = _get_product_rating_optional(product_id)
    reviews = reviews_payload["reviews"]
    sentiment = _resolve_sentiment_totals(rating, reviews)
    return {
        "productId": str(product["id"]),
        "rating": _resolve_product_rating(rating, reviews),
        "reviewsCount": reviews_payload["count"],
        "sentiment": sentiment,
        "sentimentPercentages": _to_percentages(sentiment),
        "marketplaces": _build_marketplace_stats(reviews),
    }


def _create_product(payload: ProductCreate) -> dict:
    return catalog_client.post("/products", json=payload.model_dump())


def _get_catalog_product(product_id: int) -> dict:
    return catalog_client.get(f"/products/{product_id}")


def _delete_product(product_id: int) -> dict:
    return catalog_client.delete(f"/products/{product_id}")


def _collect_product_reviews(product_id: int) -> dict:
    product = _get_catalog_product(product_id)
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
        "requested_marketplaces": collected.get("requested_marketplaces", []),
        "completed_marketplaces": collected.get("completed_marketplaces", []),
        "failed_marketplaces": collected.get("failed_marketplaces", {}),
    }


def _analyze_product(product_id: int, force: bool = False) -> dict:
    return analysis_client.post(f"/analyze/product/{product_id}", params={"force": str(force).lower()})


def _calculate_product_rating(product_id: int) -> dict:
    return rating_client.post(f"/rating/product/{product_id}")


def _get_product_reviews_payload(product_id: int) -> dict:
    return review_client.get(f"/products/{product_id}/reviews")


def _get_product_rating(product_id: int) -> dict:
    return rating_client.get(f"/rating/product/{product_id}")


def _get_product_rating_optional(product_id: int) -> dict | None:
    try:
        return _get_product_rating(product_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise


def _build_product_card(product: dict) -> dict:
    product_id = int(product["id"])
    reviews_payload = _get_product_reviews_payload(product_id)
    rating = _get_product_rating_optional(product_id)
    return _compose_product_frontend(product, reviews_payload, rating)


def _build_product_view(product_id: int) -> dict:
    product = _get_catalog_product(product_id)
    reviews_payload = _get_product_reviews_payload(product_id)
    rating = _get_product_rating_optional(product_id)
    return _compose_product_frontend(product, reviews_payload, rating)


def _compose_product_frontend(product: dict, reviews_payload: dict, rating: dict | None) -> dict:
    reviews = reviews_payload["reviews"]
    sentiment = _resolve_sentiment_totals(rating, reviews)
    analyzed_reviews = sum(1 for review in reviews if review.get("sentiment") in SENTIMENT_LABELS)
    reviews_count = int(reviews_payload["count"])
    return {
        "id": str(product["id"]),
        "name": product["title"],
        "rating": _resolve_product_rating(rating, reviews),
        "reviewsCount": reviews_count,
        "status": _resolve_status(rating, reviews_count, analyzed_reviews),
        "lastAnalyzedAt": _resolve_last_analyzed_at(product, rating),
        "sentiment": sentiment,
    }


def _map_review_to_frontend(review: dict) -> dict:
    sentiment = review.get("sentiment")
    return {
        "id": str(review["id"]),
        "marketplace": _normalize_marketplace(review.get("source")),
        "text": review["text"],
        "sentiment": sentiment if sentiment in SENTIMENT_LABELS else "neutral",
        "confidence": review.get("confidence"),
        "createdAt": review.get("published_at") or review.get("created_at"),
    }


def _resolve_sentiment_totals(rating: dict | None, reviews: list[dict]) -> dict[str, int]:
    if rating is not None:
        return {
            "positive": int(rating["positive_count"]),
            "neutral": int(rating["neutral_count"]),
            "negative": int(rating["negative_count"]),
        }
    totals = {"positive": 0, "neutral": 0, "negative": 0}
    for review in reviews:
        sentiment = review.get("sentiment")
        if sentiment in totals:
            totals[sentiment] += 1
    return totals


def _resolve_product_rating(rating: dict | None, reviews: list[dict]) -> float:
    if rating is not None:
        return round(float(rating["final_rating"]), 2)
    return round(_compute_marketplace_rating(reviews), 2)


def _resolve_status(rating: dict | None, reviews_count: int, analyzed_reviews: int) -> str:
    if rating is not None and int(rating.get("total_reviews", 0)) > 0:
        return "completed"
    if reviews_count == 0:
        return "pending"
    if analyzed_reviews == 0:
        return "in_progress"
    return "in_progress"


def _resolve_last_analyzed_at(product: dict, rating: dict | None) -> str:
    if rating is not None and rating.get("updated_at"):
        return rating["updated_at"]
    return product["updated_at"]


def _to_percentages(sentiment: dict[str, int]) -> dict[str, float]:
    total = sentiment["positive"] + sentiment["neutral"] + sentiment["negative"]
    if total == 0:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    return {
        "positive": (sentiment["positive"] / total) * 100,
        "neutral": (sentiment["neutral"] / total) * 100,
        "negative": (sentiment["negative"] / total) * 100,
    }


def _build_marketplace_stats(reviews: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {marketplace: [] for marketplace in MARKETPLACE_ORDER}
    for review in reviews:
        grouped.setdefault(_normalize_marketplace(review.get("source")), []).append(review)

    items: list[dict] = []
    for marketplace in MARKETPLACE_ORDER:
        marketplace_reviews = grouped.get(marketplace, [])
        sentiment = _resolve_sentiment_totals(None, marketplace_reviews)
        items.append(
            {
                "marketplace": marketplace,
                "reviewsCount": len(marketplace_reviews),
                "rating": round(_compute_marketplace_rating(marketplace_reviews), 2),
                "positive": sentiment["positive"],
                "neutral": sentiment["neutral"],
                "negative": sentiment["negative"],
            }
        )
    return items


def _compute_marketplace_rating(reviews: list[dict]) -> float:
    rating_values = [int(review["marketplace_rating"]) for review in reviews if review.get("marketplace_rating") is not None]
    if rating_values:
        return sum(rating_values) / len(rating_values)

    sentiment_scores = []
    for review in reviews:
        sentiment = review.get("sentiment")
        if sentiment == "positive":
            sentiment_scores.append(5.0)
        elif sentiment == "neutral":
            sentiment_scores.append(3.0)
        elif sentiment == "negative":
            sentiment_scores.append(1.0)
    if not sentiment_scores:
        return 0.0
    return sum(sentiment_scores) / len(sentiment_scores)


def _normalize_marketplace(raw_value: str | None) -> str:
    if not raw_value:
        return "Wildberries"
    normalized = raw_value.strip().lower()
    return MARKETPLACE_LABELS.get(normalized, raw_value)
