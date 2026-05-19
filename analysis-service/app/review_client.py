from __future__ import annotations

import httpx


class ReviewServiceClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_product_reviews(self, product_id: int, exclude_analyzed: bool = False) -> list[dict]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(
                f"{self.base_url}/products/{product_id}/reviews",
                params={"exclude_analyzed": str(exclude_analyzed).lower()},
            )
            response.raise_for_status()
            payload = response.json()
        return payload.get("reviews", [])
