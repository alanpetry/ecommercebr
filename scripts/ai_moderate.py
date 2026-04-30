from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from common import CONFIG_DIR, CONTENT_DIR, ROOT, load_json


MESSAGES_DIR = CONTENT_DIR / "messages"
REJECTED_DIR = CONTENT_DIR / "moderation"


def read_rows() -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    for path in sorted(MESSAGES_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append((path, json.loads(line)))
    return rows


def write_rows(rows: list[tuple[Path, dict]], rejected: list[dict]) -> None:
    by_path: dict[Path, list[dict]] = {}
    for path, row in rows:
        by_path.setdefault(path, []).append(row)
    for path, items in by_path.items():
        items.sort(key=lambda row: int(row.get("telegram_message_id", 0)))
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in items),
            encoding="utf-8",
        )
    if rejected:
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)
        dest = REJECTED_DIR / "rejected.jsonl"
        with dest.open("a", encoding="utf-8") as fh:
            for row in rejected:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def classify_with_codex(batch: list[dict]) -> dict[str, dict]:
    if not shutil.which("codex"):
        raise RuntimeError("Codex CLI não encontrado; não é seguro publicar mensagens sem moderação por IA.")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "decision": {"type": "string", "enum": ["publish", "reject"]},
                        "reason": {"type": "string"},
                    },
                    "required": ["id", "decision", "reason"],
                },
            }
        },
        "required": ["decisions"],
    }
    prompt = {
        "instruction": (
            "Classifique cada mensagem de grupo de Telegram para uma wiki pública. "
            "Use julgamento editorial caso a caso, não regras por palavra-chave. "
            "REJEITE propaganda, pré-lançamento, venda de serviço/produto, convite para lista/grupo externo, "
            "cupom/oferta, mensagem de captação de clientes, pedido para chamar no privado com intenção comercial, "
            "spam, golpe ou texto sem valor para uma conversa pública. "
            "PUBLIQUE dúvidas reais, relatos de experiência, respostas úteis, comparações neutras, problemas operacionais "
            "e conversas normais de vendedores. Link oculto por si só não obriga rejeição: avalie a intenção da mensagem. "
            "Retorne somente JSON compatível com o schema."
        ),
        "messages": batch,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        schema_path = tmp / "schema.json"
        output_path = tmp / "result.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        cmd = [
            "codex",
            "exec",
            "-m",
            os.getenv("CODEX_MODERATION_MODEL", "gpt-5.2"),
            "--sandbox",
            "read-only",
            "-C",
            str(ROOT),
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
            "-",
        ]
        result = subprocess.run(
            cmd,
            input=json.dumps(prompt, ensure_ascii=False),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"Falha na moderação Codex CLI: {details[-2000:]}")
        result = extract_json(output_path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in result["decisions"]}


def moderation_payload(row: dict) -> dict:
    return {
        "id": row["id"],
        "group": row.get("group_title", ""),
        "author": row.get("author", ""),
        "date": row.get("date", ""),
        "text": row.get("text", ""),
        "reply_to_author": row.get("reply_to_author", ""),
        "reply_to_text": row.get("reply_to_text", ""),
        "flags": row.get("flags", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Modera mensagens com avaliação editorial por IA.")
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--recheck-all", action="store_true")
    parser.add_argument("--stamp-current-approved", action="store_true")
    args = parser.parse_args()

    moderation = load_json(CONFIG_DIR / "moderation.json", {})
    manual_rejects = moderation.get("manual_reject_ids", {})
    rows = read_rows()
    now = datetime.now(timezone.utc).isoformat()

    kept: list[tuple[Path, dict]] = []
    rejected: list[dict] = []
    candidates: list[tuple[Path, dict]] = []
    for path, row in rows:
        if row.get("id") in manual_rejects:
            row["moderation"] = {
                "decision": "reject",
                "method": "manual-curation",
                "reason": manual_rejects[row["id"]],
                "reviewed_at": now,
            }
            rejected.append(row)
            continue
        if args.stamp_current_approved and not row.get("moderation"):
            row["moderation"] = {
                "decision": "publish",
                "method": "codex-agent-curated",
                "reason": "Histórico inicial revisado durante a implantação.",
                "reviewed_at": now,
            }
        if args.recheck_all or not row.get("moderation"):
            candidates.append((path, row))
        else:
            kept.append((path, row))

    for idx in range(0, len(candidates), args.batch_size):
        batch_pairs = candidates[idx : idx + args.batch_size]
        decisions = classify_with_codex([moderation_payload(row) for _, row in batch_pairs])
        for path, row in batch_pairs:
            decision = decisions.get(row["id"])
            if not decision:
                raise RuntimeError(f"IA não retornou decisão para {row['id']}")
            row["moderation"] = {
                "decision": decision["decision"],
                "method": "codex-cli",
                "reason": decision["reason"],
                "reviewed_at": now,
            }
            if decision["decision"] == "publish":
                kept.append((path, row))
            else:
                rejected.append(row)

    write_rows(kept, rejected)
    print(f"Moderação IA concluída: {len(kept)} publicadas, {len(rejected)} rejeitadas, {len(candidates)} avaliadas.")


if __name__ == "__main__":
    main()
