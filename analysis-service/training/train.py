import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.preprocessing import normalize_text


LABEL_MAPPING = {
    0: "neutral",
    1: "positive",
    2: "negative",
}


class ReviewDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer, max_length: int) -> None:
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict[str, object]:
        encoded = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
        )
        item = {key: torch.tensor(value, dtype=torch.long) for key, value in encoded.items()}
        item["labels"] = self.labels[idx]
        return item


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights: torch.Tensor | None = None, label_smoothing: float = 0.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights
        self.label_smoothing = label_smoothing

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        loss_fct = nn.CrossEntropyLoss(
            weight=self.class_weights.to(logits.device) if self.class_weights is not None else None,
            label_smoothing=self.label_smoothing,
        )
        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))

        if return_outputs:
            return loss, outputs
        return loss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Russian BERT-based sentiment model.")
    parser.add_argument("--data-path", required=True, help="Path to CSV dataset with text,label,src columns.")
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "artifacts" / "model"), help="Directory for saved model.")
    parser.add_argument("--model-name", default="DeepPavlov/rubert-base-cased", help="Base Russian transformer model.")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=12, help="Per-device train batch size.")
    parser.add_argument("--eval-batch-size", type=int, default=24, help="Per-device eval batch size.")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1.5e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--label-smoothing", type=float, default=0.05)
    parser.add_argument("--early-stopping-patience", type=int, default=2)
    parser.add_argument("--logging-steps", type=int, default=100)
    parser.add_argument("--save-total-limit", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--resume-from-checkpoint", default=None, help="Path to a specific checkpoint directory.")
    parser.add_argument("--resume-from-latest", action="store_true", help="Resume from the latest checkpoint in artifacts/checkpoints.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    expected_columns = {"text", "label", "src"}
    missing_columns = expected_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_columns)}")

    df = df[["text", "label"]].copy()
    df["text"] = df["text"].astype(str).map(normalize_text)
    df["label"] = df["label"].astype(int)
    df = df[df["text"].str.len() > 0]

    invalid_labels = sorted(set(df["label"]) - set(LABEL_MAPPING.keys()))
    if invalid_labels:
        raise ValueError(f"Unsupported labels found in dataset: {invalid_labels}")

    return df


def compute_metrics(eval_pred) -> dict[str, float]:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_macro": f1_score(labels, predictions, average="macro"),
        "precision_macro": precision_score(labels, predictions, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, predictions, average="macro", zero_division=0),
    }


def compute_class_weights(labels: list[int], num_labels: int) -> torch.Tensor:
    counts = np.bincount(labels, minlength=num_labels).astype(np.float32)
    total = counts.sum()
    weights = np.ones(num_labels, dtype=np.float32)

    for index, count in enumerate(counts):
        if count > 0:
            weights[index] = total / (num_labels * count)

    return torch.tensor(weights, dtype=torch.float32)


def get_precision_flags() -> tuple[bool, bool]:
    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    use_fp16 = use_cuda and not use_bf16
    return use_fp16, use_bf16


def configure_torch_runtime() -> None:
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True


def find_latest_checkpoint(checkpoints_dir: Path) -> str | None:
    checkpoint_dirs = sorted(
        (path for path in checkpoints_dir.glob("checkpoint-*") if path.is_dir()),
        key=lambda path: int(path.name.split("-")[-1]),
    )
    if not checkpoint_dirs:
        return None
    return str(checkpoint_dirs[-1])


def resolve_resume_checkpoint(args: argparse.Namespace, checkpoints_dir: Path) -> str | None:
    if args.resume_from_checkpoint:
        return str(Path(args.resume_from_checkpoint).resolve())
    if args.resume_from_latest:
        return find_latest_checkpoint(checkpoints_dir)
    return None


def calculate_eval_steps(train_size: int, batch_size: int, grad_accum_steps: int) -> int:
    effective_batch_size = max(1, batch_size * grad_accum_steps)
    steps_per_epoch = max(1, math.ceil(train_size / effective_batch_size))
    return max(250, steps_per_epoch // 4)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    configure_torch_runtime()

    csv_path = Path(args.data_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    checkpoints_dir = output_dir.parent / "checkpoints"

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(csv_path)
    train_df, val_df = train_test_split(
        df,
        test_size=0.2,
        random_state=args.seed,
        stratify=df["label"],
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=3,
        id2label={idx: label for idx, label in LABEL_MAPPING.items()},
        label2id={label: idx for idx, label in LABEL_MAPPING.items()},
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    train_dataset = ReviewDataset(
        texts=train_df["text"].tolist(),
        labels=train_df["label"].tolist(),
        tokenizer=tokenizer,
        max_length=args.max_length,
    )
    val_dataset = ReviewDataset(
        texts=val_df["text"].tolist(),
        labels=val_df["label"].tolist(),
        tokenizer=tokenizer,
        max_length=args.max_length,
    )

    class_weights = compute_class_weights(train_df["label"].tolist(), num_labels=3)
    use_fp16, use_bf16 = get_precision_flags()
    eval_steps = calculate_eval_steps(
        train_size=len(train_df),
        batch_size=args.batch_size,
        grad_accum_steps=args.gradient_accumulation_steps,
    )
    data_collator = DataCollatorWithPadding(
        tokenizer=tokenizer,
        pad_to_multiple_of=8 if torch.cuda.is_available() else None,
    )
    resume_checkpoint = resolve_resume_checkpoint(args, checkpoints_dir)

    training_args = TrainingArguments(
        output_dir=str(checkpoints_dir),
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.epochs,
        weight_decay=args.weight_decay,
        lr_scheduler_type="cosine",
        warmup_ratio=args.warmup_ratio,
        evaluation_strategy="steps",
        save_strategy="steps",
        eval_steps=eval_steps,
        save_steps=eval_steps,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_strategy="steps",
        logging_steps=args.logging_steps,
        save_total_limit=args.save_total_limit,
        fp16=use_fp16,
        bf16=use_bf16,
        fp16_full_eval=use_fp16,
        bf16_full_eval=use_bf16,
        optim="adamw_torch_fused" if torch.cuda.is_available() else "adamw_torch",
        max_grad_norm=1.0,
        dataloader_num_workers=args.num_workers,
        dataloader_pin_memory=torch.cuda.is_available(),
        group_by_length=True,
        save_safetensors=True,
        report_to=[],
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        class_weights=class_weights,
        label_smoothing=args.label_smoothing,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=args.early_stopping_patience)],
    )

    trainer.train(resume_from_checkpoint=resume_checkpoint)
    metrics = trainer.evaluate()

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    metadata = {
        "base_model": args.model_name,
        "label_mapping": {str(idx): label for idx, label in LABEL_MAPPING.items()},
        "train_size": int(len(train_df)),
        "validation_size": int(len(val_df)),
        "device": "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"),
        "precision": "bf16" if use_bf16 else ("fp16" if use_fp16 else "fp32"),
        "training_config": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "warmup_ratio": args.warmup_ratio,
            "label_smoothing": args.label_smoothing,
            "eval_steps": eval_steps,
            "class_weights": [round(float(value), 6) for value in class_weights.tolist()],
            "gradient_checkpointing": True,
            "resume_from_checkpoint": resume_checkpoint,
        },
        "metrics": {key: float(value) for key, value in metrics.items()},
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
