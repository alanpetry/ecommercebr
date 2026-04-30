from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient

from common import CONFIG_DIR, CONTENT_DIR, compact_text, load_json, privacy_block_reason, public_author, sanitize_text, stable_id


MESSAGES_DIR = CONTENT_DIR / "messages"


def read_group_rows() -> dict[str, tuple[Path, list[dict]]]:
    groups: dict[str, tuple[Path, list[dict]]] = {}
    for path in sorted(MESSAGES_DIR.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if rows:
            groups[str(rows[0]["telegram_group_id"])] = (path, rows)
    return groups


async def main() -> None:
    load_dotenv("../.env")
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    groups_doc = load_json(CONFIG_DIR / "groups.json", {"groups": {}})
    grouped = read_group_rows()
    client = TelegramClient("../.sessions/alan", api_id, api_hash)
    await client.start()
    try:
        for group_id, (path, rows) in grouped.items():
            group_cfg = groups_doc["groups"].get(group_id, {})
            entity_ref = group_cfg.get("public_username") or int(group_id)
            entity = await client.get_entity(entity_ref)
            ids = [int(row["telegram_message_id"]) for row in rows]
            messages = await client.get_messages(entity, ids=ids)
            by_id = {int(msg.id): msg for msg in messages if msg}
            changed = 0
            for row in rows:
                message = by_id.get(int(row["telegram_message_id"]))
                if not message:
                    continue
                reply_id = getattr(message, "reply_to_msg_id", None)
                if not reply_id:
                    reply_to = getattr(message, "reply_to", None)
                    reply_id = getattr(reply_to, "reply_to_msg_id", None)
                if not reply_id:
                    continue
                row["reply_to_telegram_message_id"] = int(reply_id)
                row["reply_to_id"] = stable_id(group_id, reply_id)
                try:
                    replied = await message.get_reply_message()
                except Exception:
                    replied = None
                if replied and getattr(replied, "raw_text", None):
                    text, flags = sanitize_text(replied.raw_text or "")
                    if not privacy_block_reason(text, flags):
                        row["reply_to_text"] = compact_text(text, 220)
                        try:
                            sender = await replied.get_sender()
                        except Exception:
                            sender = None
                        row["reply_to_author"] = public_author(sender) if sender else "Participante"
                changed += 1
            rows.sort(key=lambda row: int(row.get("telegram_message_id", 0)))
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            print(f"{group_cfg.get('title', group_id)}: {changed} respostas vinculadas")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
