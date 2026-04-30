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

HARD_SPAM_PATTERNS = [
    r"(?i)\b(chama no privado|me chama no pv|link na bio|arrasta pra cima)\b",
    r"(?i)\b(chamar no privado|me chama aqui|manda mensagem no privado|mandar mensagem no meu privado)\b",
    r"(?i)\b(entre em contato|entrar em contato|falar comigo no privado)\b",
    r"(?i)\b(vagas gr[aá]tis|vagas gratuitas|vagas limitadas|grupo vip|grupo exclusivo)\b",
    r"(?i)\b(ofere[cç]o|estou oferecendo|servi[cç]os prestados|presta[cç][aã]o de servi[cç]os|proposta de trabalho)\b",
    r"(?i)\b(consultoria individual|mentoria|curso completo|assistente virtual|suporte via whatsapp)\b",
    r"(?i)\b(desbloqueio.*mercado livre|bloqueio de contas|solu[cç][oõ]es jur[ií]dicas|consultoria jur[ií]dica)\b",
    r"(?i)\b(escrit[oó]rio de contabilidade|live gratuita|quer vender mais)\b",
    r"(?i)\b(compre agora|aproveite agora|oferta imperd[ií]vel)\b",
]

SOFT_SPAM_PATTERNS = [
    r"(?i)\b(cupom|promo[cç][aã]o|oferta imperd[ií]vel|frete gr[aá]tis)\b",
    r"(?i)\b(ganhe dinheiro|renda extra|curso completo|mentoria|grupo vip)\b",
    r"(?i)\b(divulgar|divulga[cç][aã]o|parceiros|clientes|custo-benef[ií]cio)\b",
]


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
    flags = {
        "had_link": bool(URL_RE.search(text)),
        "had_email": bool(EMAIL_RE.search(text)),
        "had_phone": bool(PHONE_RE.search(text)),
    }
    text = URL_RE.sub("[link removido]", text)
    text = EMAIL_RE.sub("[email removido]", text)
    text = PHONE_RE.sub("[telefone removido]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text, flags


def looks_like_spam(original: str, sanitized: str, flags: dict[str, bool]) -> bool:
    lower = original.lower()
    if any(re.search(pattern, lower) for pattern in HARD_SPAM_PATTERNS):
        return True
    if flags.get("had_phone") or flags.get("had_email"):
        return True
    if flags.get("had_link") and any(re.search(pattern, lower) for pattern in SOFT_SPAM_PATTERNS):
        return True
    if sum(1 for pattern in SOFT_SPAM_PATTERNS if re.search(pattern, lower)) >= 2:
        return True
    if sanitized.count("[link removido]") >= 2:
        return True
    meaningful = sanitized.replace("[link removido]", "").strip()
    return len(meaningful) < 12


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


def isoformat(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def html(text: str) -> str:
    return escape(text, quote=True)
