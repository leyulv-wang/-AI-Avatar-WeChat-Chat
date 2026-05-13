from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from wxbot.backup import create_backup, restore_backup
from wxbot.config import get_settings
from wxbot.crypto import ensure_master_key, get_fernet
from wxbot.llm import MockProvider, OllamaProvider, OpenAICompatibleProvider
from wxbot.logging_config import configure_logging
from wxbot.models import InboundMessage, OutboundMessage, RestoreBackupRequest, RoleConfig
from wxbot.scheduler import start_scheduler
from wxbot.service import BotService
from wxbot.weflow import WeFlowClient
from wxbot.weflow_listener import run_sse_listener


configure_logging()
logger = logging.getLogger("wxbot")

settings = get_settings()
data_dir = Path(settings.wxbot_data_dir)
secrets_dir = Path(settings.wxbot_secrets_dir)
backup_dir = Path(settings.wxbot_backup_dir)

storage_encrypt = settings.wxbot_storage_encryption.lower() in ("on", "true", "1", "yes")
if storage_encrypt:
    master_key = ensure_master_key(secrets_dir, settings.wxbot_master_key)
    fernet = get_fernet(master_key)
else:
    fernet = None

provider = settings.wxbot_llm_provider.lower()
if provider == "ollama":
    llm = OllamaProvider(base_url=settings.wxbot_ollama_base_url, model=settings.wxbot_ollama_model)
elif provider == "openai_compat":
    if not settings.wxbot_llm_base_url:
        raise RuntimeError("WXBOT_LLM_BASE_URL 未配置")
    if not settings.wxbot_llm_api_key:
        raise RuntimeError("WXBOT_LLM_API_KEY 未配置")
    if not settings.wxbot_llm_model:
        raise RuntimeError("WXBOT_LLM_MODEL 未配置")
    llm = OpenAICompatibleProvider(
        base_url=settings.wxbot_llm_base_url,
        api_key=settings.wxbot_llm_api_key,
        model=settings.wxbot_llm_model,
        chat_completions_path=settings.wxbot_llm_chat_completions_path,
    )
else:
    llm = MockProvider()

weflow = WeFlowClient(
    base_url=settings.weflow_base_url,
    token=settings.weflow_token,
    sse_path=settings.weflow_sse_path,
    messages_path=settings.weflow_messages_path,
    send_path=settings.weflow_send_path,
)

service = BotService(
    data_dir=data_dir,
    fernet=fernet,
    llm=llm,
    weflow=weflow,
    candidate_count=settings.wxbot_candidate_count,
    context_messages=settings.wxbot_context_messages,
    reply_timeout_sec=settings.wxbot_reply_timeout_sec,
    storage_encrypt=storage_encrypt,
    cache_max_messages=settings.wxbot_cache_max_messages,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    service.ensure_owner_profile()
    scheduler = start_scheduler(service)
    listener_task = None
    if weflow.sse_url():
        import asyncio

        listener_task = asyncio.create_task(run_sse_listener(service=service, weflow=weflow))
    try:
        yield
    finally:
        if listener_task:
            listener_task.cancel()
        scheduler.shutdown(wait=False)


app = FastAPI(title="wxbot", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/weflow/webhook")
async def weflow_webhook(msg: InboundMessage) -> dict[str, str]:
    await service.ingest_inbound(msg)
    return {"status": "accepted"}


@app.post("/api/messages/send")
async def send_message(msg: OutboundMessage) -> dict:
    try:
        return await service.send_outbound(msg.contact_id, msg.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/contacts/{contact_id}/events")
async def get_events(contact_id: str, limit: int = 50) -> dict:
    limit = max(1, min(limit, 200))
    events = service.get_recent_events(contact_id, limit=limit)
    return {"data": events}


@app.get("/api/contacts/{contact_id}/messages")
async def get_messages(contact_id: str, limit: int = 200) -> dict:
    limit = max(1, min(limit, 500))
    try:
        data = await weflow.get_messages(talker=contact_id, limit=limit, offset=0, chatlab=True)
    except Exception:
        events = service.get_recent_events(contact_id, limit=limit)
        events = [e for e in events if e.get("direction") != "candidate"]
        return {"data": events}
    items = data.get("messages") if isinstance(data, dict) else None
    out: list[dict] = []
    if isinstance(items, list):
        for m in items:
            if not isinstance(m, dict):
                continue

            if "createTime" in m or "isSend" in m:
                ts_i = int(m.get("createTime") or 0)
                sender = m.get("senderUsername") if isinstance(m.get("senderUsername"), str) else "unknown"
                is_send = int(m.get("isSend") or 0)
                direction = "outbound" if is_send == 1 else "inbound"
                content = m.get("content") if isinstance(m.get("content"), str) else str(m.get("rawContent") or "")
                pid = m.get("serverId") or m.get("localId")
                out.append(
                    {
                        "event_id": str(pid) if pid is not None else f"{sender}-{ts_i}",
                        "contact_id": contact_id,
                        "contact_name": None,
                        "timestamp": ts_i,
                        "sender": sender,
                        "sender_name": None,
                        "direction": direction,
                        "content": content,
                        "platform_message_id": str(pid) if pid is not None else None,
                        "ai_candidates": None,
                        "meta": {"type": m.get("localType")},
                    }
                )
            else:
                meta = data.get("meta") if isinstance(data, dict) else None
                owner_id = meta.get("ownerId") if isinstance(meta, dict) else None
                owner_base = None
                if isinstance(owner_id, str) and owner_id:
                    owner_base = owner_id.split("_")[0]
                ts = m.get("timestamp")
                try:
                    ts_i = int(ts) if ts is not None else 0
                except Exception:
                    ts_i = 0
                sender = m.get("sender") if isinstance(m.get("sender"), str) else "unknown"
                sender_name = m.get("accountName") if isinstance(m.get("accountName"), str) else None
                is_self = False
                if owner_id and sender == owner_id:
                    is_self = True
                if owner_base and sender == owner_base:
                    is_self = True
                if sender_name == "我":
                    is_self = True
                direction = "outbound" if is_self else "inbound"
                out.append(
                    {
                        "event_id": m.get("platformMessageId") or f"{sender}-{ts_i}",
                        "contact_id": contact_id,
                        "contact_name": meta.get("name") if isinstance(meta, dict) else None,
                        "timestamp": ts_i,
                        "sender": sender,
                        "sender_name": sender_name,
                        "direction": direction,
                        "content": m.get("content") if isinstance(m.get("content"), str) else str(m.get("content") or ""),
                        "platform_message_id": m.get("platformMessageId"),
                        "ai_candidates": None,
                        "meta": {"type": m.get("type")},
                    }
                )

    out.sort(key=lambda x: x.get("timestamp") or 0)
    return {"data": out}


@app.get("/api/contacts")
async def list_contacts(q: str | None = None, limit: int = 200) -> dict:
    limit = max(1, min(limit, 500))
    contacts_root = data_dir / "contacts"
    if not contacts_root.exists():
        return {"data": []}

    items: list[dict] = []
    for p in contacts_root.iterdir():
        if not p.is_dir():
            continue
        contact_id = p.name
        events = service.get_recent_events(contact_id, limit=50)
        last_ts = 0
        last_preview = ""
        display_name = contact_id
        for e in reversed(events):
            if isinstance(e.get("timestamp"), int) and e["timestamp"] > last_ts:
                last_ts = e["timestamp"]
            cn = e.get("contact_name")
            if isinstance(cn, str) and cn.strip():
                display_name = cn.strip()
            if not last_preview and e.get("direction") in ("inbound", "outbound"):
                c = e.get("content")
                if isinstance(c, str) and c.strip():
                    last_preview = c.strip()
        if q and q.strip():
            qs = q.strip().lower()
            if qs not in contact_id.lower() and qs not in display_name.lower() and qs not in last_preview.lower():
                continue
        items.append(
            {
                "id": contact_id,
                "display_name": display_name,
                "last_timestamp": last_ts,
                "last_preview": last_preview,
            }
        )

    items.sort(key=lambda x: x.get("last_timestamp") or 0, reverse=True)
    return {"data": items[:limit]}


@app.get("/api/contacts/{contact_id}/candidates")
async def get_candidates(contact_id: str, limit: int = 5) -> dict:
    limit = max(1, min(limit, 5))
    events = service.get_recent_events(contact_id, limit=200)
    for e in reversed(events):
        if e.get("direction") == "candidate" and isinstance(e.get("ai_candidates"), list):
            cands = [x for x in e["ai_candidates"] if isinstance(x, str) and x.strip()]
            return {"data": cands[:limit], "event_id": e.get("event_id"), "timestamp": e.get("timestamp")}
    return {"data": [], "event_id": None, "timestamp": None}


@app.post("/api/contacts/{contact_id}/candidates/generate")
async def generate_candidates(contact_id: str) -> dict:
    try:
        items = await service.generate_candidates_now(contact_id)
        return {"data": items}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/assistants")
async def list_assistants() -> dict:
    items = [x.model_dump() for x in service.list_assistants()]
    return {"data": items}


@app.post("/api/assistants")
async def create_or_update_assistant(role: RoleConfig) -> dict:
    saved = service.upsert_assistant(role)
    return {"data": saved.model_dump()}


@app.get("/api/contacts/{contact_id}/assistant")
async def get_selected_assistant(contact_id: str) -> dict:
    role_id = service.get_selected_assistant_id(contact_id)
    role = service.get_assistant(role_id) if role_id else None
    return {"data": {"role_id": role_id, "assistant": role.model_dump() if role else None}}


@app.put("/api/contacts/{contact_id}/assistant")
async def set_selected_assistant(contact_id: str, body: dict) -> dict:
    role_id = body.get("role_id")
    if not isinstance(role_id, str) or not role_id:
        raise HTTPException(status_code=400, detail="role_id 必填")
    if service.get_assistant(role_id) is None:
        raise HTTPException(status_code=400, detail="assistant 不存在")
    service.set_selected_assistant(contact_id, role_id)
    return {"status": "ok"}


@app.post("/api/owner-profile/recompute")
async def recompute_owner_profile() -> dict:
    profile = service.recompute_owner_profile()
    return {"data": profile.__dict__}


@app.get("/api/owner-profile")
async def get_owner_profile() -> dict:
    profile = service.get_owner_profile()
    return {"data": profile.__dict__ if profile else None}


@app.get("/api/contacts/{contact_id}/role")
async def get_role(contact_id: str) -> dict:
    role = service.get_role(contact_id)
    return {"data": role.model_dump()}


@app.put("/api/contacts/{contact_id}/role")
async def set_role(contact_id: str, role: RoleConfig) -> dict:
    service.set_role(contact_id, role)
    return {"status": "ok"}


@app.post("/api/backup/create")
async def backup_create() -> dict:
    path = create_backup(data_dir=data_dir, backup_dir=backup_dir)
    return {"path": str(path)}


@app.post("/api/backup/restore")
async def backup_restore(req: RestoreBackupRequest) -> dict:
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(status_code=400, detail="备份文件不存在")
    restore_backup(backup_zip=p, data_dir=data_dir)
    return {"status": "ok"}


@app.get("/api/contacts/{contact_id}/export.csv")
async def export_csv(contact_id: str, limit: int = 1000) -> PlainTextResponse:
    limit = max(1, min(limit, 100000))
    events = service.get_recent_events(contact_id, limit=limit)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "timestamp",
            "direction",
            "sender",
            "sender_name",
            "content",
            "platform_message_id",
            "ai_candidates",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    for e in events:
        writer.writerow(e)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv; charset=utf-8")
