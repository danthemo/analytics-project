from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.model import SentimentAnalyzer
from app.schemas import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    HealthResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    analyzer = SentimentAnalyzer(settings.model_dir)
    _.state.analyzer = analyzer
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
