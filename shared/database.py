from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def get_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = _env("POSTGRES_USER", "postgres")
    password = _env("POSTGRES_PASSWORD", "postgres")
    host = _env("POSTGRES_HOST", "postgres")
    port = _env("POSTGRES_PORT", "5432")
    db_name = _env("POSTGRES_DB", "reviews_platform")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
