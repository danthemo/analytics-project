from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    marketplace: str
    title: str
    url: str | None = None
    marketplace_product_id: str | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    marketplace: str
    marketplace_product_id: str | None
    title: str
    url: str | None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
