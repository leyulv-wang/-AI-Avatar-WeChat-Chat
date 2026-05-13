from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wxbot.config import get_settings
from wxbot.crypto import ensure_master_key, get_fernet
from wxbot.storage import EncryptedJSONLStore, get_contact_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--contact-id", default=None)
    args = parser.parse_args()

    src = Path(args.path)
    data = json.loads(src.read_text(encoding="utf-8"))
    meta = data.get("meta") or {}
    contact_id = args.contact_id or _infer_contact_id(data) or "unknown"

    settings = get_settings()
    data_dir = Path(settings.wxbot_data_dir)
    secrets_dir = Path(settings.wxbot_secrets_dir)
    storage_encrypt = settings.wxbot_storage_encryption.lower() in ("on", "true", "1", "yes")
    if storage_encrypt:
        master_key = ensure_master_key(secrets_dir, settings.wxbot_master_key)
        fernet = get_fernet(master_key)
    else:
        fernet = None

    paths = get_contact_paths(data_dir, str(contact_id), encrypt=storage_encrypt)
    store = EncryptedJSONLStore(paths.events_path, fernet)
    for m in data.get("messages") or []:
        ts = int(m.get("timestamp") or time.time())
        content = m.get("content") or ""
        sender = m.get("sender") or "unknown"
        event = {
            "event_id": str(uuid.uuid4()),
            "contact_id": str(contact_id),
            "contact_name": meta.get("name"),
            "timestamp": ts,
            "sender": str(sender),
            "sender_name": m.get("accountName"),
            "direction": "inbound" if str(sender) != "wxbot" else "outbound",
            "content": str(content),
            "platform_message_id": m.get("platformMessageId"),
            "ai_candidates": None,
            "meta": {"type": m.get("type")},
        }
        store.append(event)
    return 0


def _infer_contact_id(export_json: dict) -> str | None:
    meta = export_json.get("meta") or {}
    name = meta.get("name")
    members = export_json.get("members")
    if isinstance(name, str) and isinstance(members, list):
        for mem in members:
            if not isinstance(mem, dict):
                continue
            if mem.get("accountName") == name and isinstance(mem.get("platformId"), str):
                return mem["platformId"]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
