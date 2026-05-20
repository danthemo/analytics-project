from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException


class ServiceClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json, params=params)

    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("DELETE", path, params=params)

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(method, path, json=json, params=params)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Upstream request timed out: {self.base_url}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream service unavailable: {self.base_url}") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or response.json().get("error")
            except ValueError:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail or "Upstream service error")
        return response.json()
