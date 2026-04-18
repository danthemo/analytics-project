import re


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    cleaned = text.replace("\u00a0", " ").strip()
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned

