from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.preprocessing import normalize_text


DEFAULT_LABEL_MAPPING = {
    0: "neutral",
    1: "positive",
    2: "negative",
}


@dataclass
class PredictionResult:
    sentiment_class: str
    confidence: float
    probabilities: dict[str, float]


class SentimentAnalyzer:
    def __init__(self, model_dir: str) -> None:
        model_path = Path(model_dir)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model directory {model_dir} was not found. Train the model before starting the service."
            )

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()
        self.label_mapping = self._resolve_label_mapping()

    def _resolve_label_mapping(self) -> dict[int, str]:
        config_mapping = getattr(self.model.config, "id2label", None)
        if not config_mapping:
            return DEFAULT_LABEL_MAPPING

        resolved: dict[int, str] = {}
        for key, value in config_mapping.items():
            resolved[int(key)] = str(value).lower()
        return resolved

    @torch.inference_mode()
    def predict(self, text: str) -> PredictionResult:
        normalized_text = normalize_text(text)
        encoded = self.tokenizer(
            normalized_text,
            truncation=True,
            padding=True,
            max_length=256,
            return_tensors="pt",
        )
        logits = self.model(**encoded).logits
        probabilities = torch.softmax(logits, dim=1).squeeze(0).tolist()

        label_scores = {
            self.label_mapping[idx]: round(float(score), 6)
            for idx, score in enumerate(probabilities)
        }

        best_index = int(torch.argmax(logits, dim=1).item())
        best_label = self.label_mapping[best_index]
        best_score = label_scores[best_label]

        return PredictionResult(
            sentiment_class=best_label,
            confidence=best_score,
            probabilities=label_scores,
        )

