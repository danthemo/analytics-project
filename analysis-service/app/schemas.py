from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class AnalyzeTextResponse(BaseModel):
    sentiment_class: str
    confidence: float
    probabilities: dict[str, float]


class AnalyzeReviewResponse(BaseModel):
    review_id: int
    sentiment: str
    confidence: float


class AnalyzeReviewRequest(BaseModel):
    review_id: int
    text: str = Field(..., min_length=1, max_length=5000)


class AnalyzeProductResponse(BaseModel):
    product_id: int
    analyzed: int
    skipped: int
    results: list[AnalyzeReviewResponse]


class HealthResponse(BaseModel):
    status: str
    model_dir: str
