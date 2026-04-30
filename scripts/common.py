from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CONTENT_DIR = ROOT / "content"
DOCS_DIR = ROOT / "docs"


URL_RE = re.compile(r"(?i)\b(?:https?://|www\.|t\.me/|telegram\.me/|wa\.me/)\S+")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){9,}(?!\d)")
HANDLE_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{5,32})")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
LINK_PLACEHOLDER = "[link oculto]"
EMAIL_PLACEHOLDER = "[email oculto]"
PHONE_PLACEHOLDER = "[telefone oculto]"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "grupo"


def stable_id(*parts: object, length: int = 16) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def sanitize_text(text: str) -> tuple[str, dict[str, bool]]:
    text = (
        text.replace("[link removido]", LINK_PLACEHOLDER)
        .replace("[email removido]", EMAIL_PLACEHOLDER)
        .replace("[telefone removido]", PHONE_PLACEHOLDER)
    )
    flags = {
        "had_link": bool(URL_RE.search(text)),
        "had_email": bool(EMAIL_RE.search(text)),
        "had_phone": bool(PHONE_RE.search(text)),
    }
    text = URL_RE.sub(LINK_PLACEHOLDER, text)
    text = EMAIL_RE.sub(EMAIL_PLACEHOLDER, text)
    text = PHONE_RE.sub(PHONE_PLACEHOLDER, text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text, flags


def privacy_block_reason(sanitized: str, flags: dict[str, bool]) -> str | None:
    if flags.get("had_phone") or flags.get("had_email"):
        return "privacy"
    meaningful = (
        sanitized.replace(LINK_PLACEHOLDER, "")
        .replace(EMAIL_PLACEHOLDER, "")
        .replace(PHONE_PLACEHOLDER, "")
        .strip()
    )
    if len(meaningful) < 12:
        return "empty_after_sanitization"
    return None


def looks_like_spam(original: str, sanitized: str, flags: dict[str, bool]) -> bool:
    return privacy_block_reason(sanitized, flags) is not None


def public_author(sender: Any) -> str:
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    first_name = (getattr(sender, "first_name", None) or "").strip()
    if first_name:
        return first_name.split()[0]
    title = (getattr(sender, "title", None) or "").strip()
    if title:
        return title.split()[0]
    return "Participante"


def infer_tags(text: str, tag_config: dict[str, list[str]]) -> list[str]:
    lower = unicodedata.normalize("NFKD", text.lower())
    lower = "".join(ch for ch in lower if not unicodedata.combining(ch))
    tags = []
    for tag, keywords in tag_config.items():
        for keyword in keywords:
            k = unicodedata.normalize("NFKD", keyword.lower())
            k = "".join(ch for ch in k if not unicodedata.combining(ch))
            if k in lower:
                tags.append(tag)
                break
    return sorted(set(tags))


def compact_text(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def isoformat(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def html(text: str) -> str:
    return escape(text, quote=True)
