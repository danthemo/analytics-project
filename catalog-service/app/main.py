from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.init_db import init_db
from shared.models import Product

from .schemas import HealthResponse, ProductCreate, ProductResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="catalog-service", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/products", response_model=ProductResponse)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(
        marketplace=payload.marketplace,
        title=payload.title,
        url=payload.url,
        marketplace_product_id=payload.marketplace_product_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    logger.info("created product id=%s marketplace=%s", product.id, product.marketplace)
    return product


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    return db.query(Product).order_by(Product.id.desc()).all()
