from __future__ import annotations

import json
from pathlib import Path

from common import CONTENT_DIR, looks_like_spam, sanitize_text


MESSAGES_DIR = CONTENT_DIR / "messages"


def clean_file(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0

    kept = []
    removed = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            sanitized, new_flags = sanitize_text(row.get("text", ""))
            flags = row.get("flags") or {}
            merged_flags = {
                "had_link": bool(flags.get("had_link") or new_flags["had_link"]),
                "had_email": bool(flags.get("had_email") or new_flags["had_email"]),
                "had_phone": bool(flags.get("had_phone") or new_flags["had_phone"]),
            }
            if looks_like_spam(row.get("text", ""), sanitized, merged_flags):
                removed += 1
                continue
            row["text"] = sanitized
            row["flags"] = merged_flags
            kept.append(row)

    with path.open("w", encoding="utf-8") as fh:
        for row in kept:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(kept), removed


def main() -> None:
    total_kept = 0
    total_removed = 0
    for path in sorted(MESSAGES_DIR.glob("*.jsonl")):
        kept, removed = clean_file(path)
        total_kept += kept
        total_removed += removed
        if removed:
            print(f"{path.name}: {removed} mensagens removidas")
    print(f"Limpeza concluída: {total_kept} mantidas, {total_removed} removidas")


if __name__ == "__main__":
    main()
