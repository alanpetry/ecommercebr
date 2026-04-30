from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, functions, types

from common import (
    CONFIG_DIR,
    CONTENT_DIR,
    infer_tags,
    isoformat,
    load_json,
    looks_like_spam,
    public_author,
    sanitize_text,
    save_json,
    slugify,
    stable_id,
)


MESSAGES_DIR = CONTENT_DIR / "messages"
GROUP_MEDIA_DIR = CONTENT_DIR / "media" / "groups"


def input_peer_key(peer: object) -> tuple[str, int | None]:
    return (type(peer).__name__, getattr(peer, "channel_id", None) or getattr(peer, "chat_id", None))


def read_existing(path: Path) -> tuple[set[str], int]:
    if not path.exists():
        return set(), 0
    seen: set[str] = set()
    max_id = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            seen.add(str(item["id"]))
            max_id = max(max_id, int(item.get("telegram_message_id", 0)))
    return seen, max_id


def append_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


async def get_ecommerce_filter(client: TelegramClient, folder_title: str):
    filters = await client(functions.messages.GetDialogFiltersRequest())
    for dialog_filter in filters.filters:
        title = getattr(getattr(dialog_filter, "title", None), "text", None)
        if title == folder_title:
            return dialog_filter
    raise RuntimeError(f'Pasta "{folder_title}" não encontrada no Telegram.')


async def resolve_folder_entities(client: TelegramClient, folder_title: str) -> list[object]:
    folder = await get_ecommerce_filter(client, folder_title)
    include_keys = {input_peer_key(peer) for peer in folder.include_peers}
    entities = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if not getattr(entity, "megagroup", False):
            continue
        input_entity = await client.get_input_entity(entity)
        if input_peer_key(input_entity) in include_keys:
            entities.append(entity)
    return sorted(entities, key=lambda e: (getattr(e, "title", "") or "").lower())


async def sync_group_photo(client: TelegramClient, entity: object, slug: str) -> str | None:
    GROUP_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = GROUP_MEDIA_DIR / f"{slug}.jpg"
    tmp = GROUP_MEDIA_DIR / f"{slug}.tmp.jpg"
    try:
        downloaded = await client.download_profile_photo(entity, file=str(tmp), download_big=True)
    except Exception:
        downloaded = None
    if downloaded:
        shutil.move(str(tmp), str(dest))
        return f"media/groups/{slug}.jpg"
    if tmp.exists():
        tmp.unlink()
    return f"media/groups/{slug}.jpg" if dest.exists() else None


async def sync_messages(
    client: TelegramClient,
    entity: object,
    group_cfg: dict,
    tag_config: dict[str, list[str]],
    limit: int | None,
    full: bool,
) -> int:
    slug = group_cfg["slug"]
    group_id = str(group_cfg["telegram_id"])
    path = MESSAGES_DIR / f"{slug}.jsonl"
    seen, max_message_id = read_existing(path)
    min_id = 0 if full else max_message_id
    rows = []

    async for message in client.iter_messages(entity, min_id=min_id, reverse=True, limit=limit):
        raw_text = message.raw_text or ""
        if not raw_text.strip():
            continue
        sanitized, flags = sanitize_text(raw_text)
        if looks_like_spam(raw_text, sanitized, flags):
            continue
        sender = await message.get_sender()
        row_id = stable_id(group_id, message.id)
        if row_id in seen:
            continue
        tags = sorted(set(group_cfg.get("default_tags", [])) | set(infer_tags(sanitized, tag_config)))
        rows.append(
            {
                "id": row_id,
                "telegram_group_id": group_id,
                "telegram_message_id": int(message.id),
                "group_slug": slug,
                "group_title": group_cfg["title"],
                "author": public_author(sender),
                "date": message.date.astimezone().isoformat(),
                "text": sanitized,
                "tags": tags,
                "flags": flags,
            }
        )
    append_jsonl(path, rows)
    return len(rows)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza conversas da pasta E-commerce do Telegram.")
    parser.add_argument("--env", default=os.getenv("TELEGRAM_ENV", "../.env"))
    parser.add_argument("--session", default=os.getenv("TELEGRAM_SESSION_FILE", "../.sessions/alan"))
    parser.add_argument("--folder", default=None)
    parser.add_argument("--limit", type=int, default=int(os.getenv("TELEGRAM_EXPORT_LIMIT", "0")) or None)
    parser.add_argument("--full", action="store_true", help="Ignora o cursor incremental e relê o histórico.")
    args = parser.parse_args()

    load_dotenv(args.env)
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    site_cfg = load_json(CONFIG_DIR / "site.json", {})
    tag_config = load_json(CONFIG_DIR / "tags.json", {})
    groups_doc = load_json(CONFIG_DIR / "groups.json", {"groups": {}})
    state = load_json(CONTENT_DIR / "state.json", {"groups": {}})
    folder_title = args.folder or site_cfg.get("telegram_folder", "E-commerce")

    client = TelegramClient(args.session, api_id, api_hash)
    await client.start()
    try:
        entities = await resolve_folder_entities(client, folder_title)
        total_new = 0
        for entity in entities:
            telegram_id = str(getattr(entity, "id"))
            current_title = getattr(entity, "title", "") or f"Grupo {telegram_id}"
            existing = groups_doc["groups"].get(telegram_id, {})
            slug = existing.get("slug") or slugify(current_title)
            group_cfg = {
                "telegram_id": telegram_id,
                "title": existing.get("title") or current_title,
                "slug": slug,
                "description": existing.get("description", ""),
                "default_tags": existing.get("default_tags", []),
                "public_username": getattr(entity, "username", None),
                "source_title": current_title,
                "avatar": existing.get("avatar"),
            }
            avatar = await sync_group_photo(client, entity, slug)
            if avatar:
                group_cfg["avatar"] = avatar
            groups_doc["groups"][telegram_id] = group_cfg

            added = await sync_messages(client, entity, group_cfg, tag_config, args.limit, args.full)
            state.setdefault("groups", {}).setdefault(telegram_id, {})
            state["groups"][telegram_id].update(
                {
                    "title": group_cfg["title"],
                    "slug": slug,
                    "last_sync_at": isoformat(),
                    "last_added": added,
                }
            )
            total_new += added
            print(f"{group_cfg['title']}: +{added} mensagens")

        state["last_sync_at"] = isoformat()
        save_json(CONFIG_DIR / "groups.json", groups_doc)
        save_json(CONTENT_DIR / "state.json", state)
        print(f"Total novo: {total_new}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

