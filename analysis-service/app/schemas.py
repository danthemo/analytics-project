from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class AnalyzeTextResponse(BaseModel):
    sentiment_class: str
    confidence: float
    probabilities: dict[str, float]


class AnalyzeReviewResponse(BaseModel):
    review_id: int
    review_text: str
    sentiment_class: str
    confidence: float
    probabilities: dict[str, float]


class HealthResponse(BaseModel):
    status: str
    model_dir: str
