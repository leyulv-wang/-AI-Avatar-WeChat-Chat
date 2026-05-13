from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from wxbot.llm import LLMProvider, with_timeout
from wxbot.models import InboundMessage, RoleConfig
from wxbot.storage import EncryptedJSONLStore, EncryptedJSONStore, get_contact_paths
from wxbot.tone import ToneProfile, build_tone_profile
from wxbot.weflow import WeFlowClient


class BotService:
    def __init__(
        self,
        *,
        data_dir: Path,
        fernet: Fernet | None,
        llm: LLMProvider,
        weflow: WeFlowClient,
        candidate_count: int,
        context_messages: int,
        reply_timeout_sec: int,
        storage_encrypt: bool = True,
        cache_max_messages: int = 200,
    ):
        self._data_dir = data_dir
        self._fernet = fernet
        self._storage_encrypt = storage_encrypt
        self._llm = llm
        self._weflow = weflow
        self._candidate_count = max(3, min(candidate_count, 5))
        self._context_messages = max(1, context_messages)
        self._reply_timeout_sec = max(1, reply_timeout_sec)
        self._cache_max_messages = max(1, cache_max_messages)

    def _events_store(self, contact_id: str) -> EncryptedJSONLStore:
        paths = get_contact_paths(self._data_dir, contact_id, encrypt=self._storage_encrypt)
        return EncryptedJSONLStore(paths.events_path, self._fernet)

    def _profile_store(self, contact_id: str) -> EncryptedJSONStore:
        paths = get_contact_paths(self._data_dir, contact_id, encrypt=self._storage_encrypt)
        return EncryptedJSONStore(paths.profile_path, self._fernet)

    def _role_store(self, contact_id: str) -> EncryptedJSONStore:
        paths = get_contact_paths(self._data_dir, contact_id, encrypt=self._storage_encrypt)
        return EncryptedJSONStore(paths.role_path, self._fernet)

    def _state_store(self, contact_id: str) -> EncryptedJSONStore:
        paths = get_contact_paths(self._data_dir, contact_id, encrypt=self._storage_encrypt)
        return EncryptedJSONStore(paths.state_path, self._fernet)

    def _assistants_store(self) -> EncryptedJSONStore:
        p = self._data_dir / ("assistants.json.enc" if self._storage_encrypt else "assistants.json")
        return EncryptedJSONStore(p, self._fernet)

    def list_assistants(self) -> list[RoleConfig]:
        raw = self._assistants_store().read() or {}
        items = raw.get("assistants") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            return [RoleConfig()]
        out: list[RoleConfig] = []
        for x in items:
            try:
                out.append(RoleConfig.model_validate(x))
            except Exception:
                continue
        return out or [RoleConfig()]

    def upsert_assistant(self, role: RoleConfig) -> RoleConfig:
        store = self._assistants_store()
        raw = store.read() or {}
        items = raw.get("assistants") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            items = []
        if not role.role_id:
            role = role.model_copy(update={"role_id": str(uuid.uuid4())})
        replaced = False
        new_items: list[dict[str, Any]] = []
        for x in items:
            if isinstance(x, dict) and x.get("role_id") == role.role_id:
                new_items.append(role.model_dump())
                replaced = True
            elif isinstance(x, dict):
                new_items.append(x)
        if not replaced:
            new_items.append(role.model_dump())
        store.write({"assistants": new_items})
        return role

    def get_assistant(self, role_id: str) -> RoleConfig | None:
        for r in self.list_assistants():
            if r.role_id == role_id:
                return r
        return None

    def set_selected_assistant(self, contact_id: str, role_id: str) -> None:
        store = self._state_store(contact_id)
        state = store.read() or {}
        state["selected_assistant_id"] = role_id
        state["updated_at"] = int(time.time())
        store.write(state)

    def get_selected_assistant_id(self, contact_id: str) -> str | None:
        state = self._state_store(contact_id).read() or {}
        v = state.get("selected_assistant_id") if isinstance(state, dict) else None
        return v if isinstance(v, str) and v else None

    def _dedup_accept(self, contact_id: str, rawid: str | None) -> bool:
        if not rawid:
            return True
        store = self._state_store(contact_id)
        state = store.read() or {}
        recent = state.get("recent_rawids")
        if not isinstance(recent, list):
            recent = []
        recent_s = [x for x in recent if isinstance(x, str)]
        if rawid in recent_s:
            return False
        recent_s.append(rawid)
        max_keep = max(200, self._cache_max_messages * 5)
        if len(recent_s) > max_keep:
            recent_s = recent_s[-max_keep:]
        state["recent_rawids"] = recent_s
        state["last_rawid"] = rawid
        state["updated_at"] = int(time.time())
        store.write(state)
        return True

    async def ingest_weflow_payload(self, payload: dict[str, Any]) -> bool:
        rawid = payload.get("rawid") if isinstance(payload.get("rawid"), str) else None
        contact_id = payload.get("sessionId") if isinstance(payload.get("sessionId"), str) else None
        if not contact_id:
            return False
        if not self._dedup_accept(contact_id, rawid):
            return False
        event_type = payload.get("event") if isinstance(payload.get("event"), str) else None
        direction = "revoke" if event_type == "message.revoke" else "inbound"
        sender_id = None
        sender_name = payload.get("sourceName") if isinstance(payload.get("sourceName"), str) else None
        contact_name = payload.get("groupName") if isinstance(payload.get("groupName"), str) else None
        content = payload.get("content")
        if not isinstance(content, str):
            content = str(content) if content is not None else ""
        ts = payload.get("timestamp")
        try:
            ts_i = int(ts) if ts is not None else int(time.time())
        except Exception:
            ts_i = int(time.time())

        if direction == "inbound" and rawid:
            info = await self._try_resolve_weflow_message(contact_id=contact_id, rawid=rawid)
            if info:
                sender_id = info.get("sender_id")
                sender_name = info.get("sender_name") or sender_name
                contact_name = info.get("contact_name") or contact_name
                if info.get("direction") in ("inbound", "outbound"):
                    direction = info["direction"]

        event = {
            "event_id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "contact_name": contact_name,
            "timestamp": ts_i,
            "sender": sender_id or "unknown",
            "sender_name": sender_name,
            "direction": direction,
            "content": content,
            "platform_message_id": rawid,
            "ai_candidates": None,
            "meta": payload,
        }
        self._events_store(contact_id).append_and_trim(event, max_lines=self._cache_max_messages)

        if direction == "inbound":
            msg = InboundMessage(
                contact_id=contact_id,
                contact_name=contact_name,
                sender_id=sender_id,
                sender_name=sender_name,
                timestamp=ts_i,
                content=content,
                platform_message_id=rawid,
                raw=payload,
            )
            asyncio.create_task(self._generate_and_store_candidates(msg))
        return True

    async def _try_resolve_weflow_message(self, *, contact_id: str, rawid: str) -> dict[str, Any] | None:
        store = self._state_store(contact_id)
        state = store.read() or {}
        owner_id = state.get("owner_id") if isinstance(state, dict) else None
        try:
            data = await self._weflow.get_messages(talker=contact_id, limit=20, offset=0, chatlab=True)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        meta = data.get("meta")
        if isinstance(meta, dict):
            if isinstance(meta.get("ownerId"), str):
                owner_id = meta.get("ownerId")
                if isinstance(state, dict):
                    state["owner_id"] = owner_id
                    store.write(state)
            contact_name = meta.get("name") if isinstance(meta.get("name"), str) else None
        else:
            contact_name = None

        messages = data.get("messages")
        if not isinstance(messages, list):
            return None
        target = None
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("platformMessageId") == rawid:
                target = m
                break
        if target is None:
            for m in reversed(messages):
                if isinstance(m, dict):
                    target = m
                    break
        if not isinstance(target, dict):
            return None

        sender_id = target.get("sender") if isinstance(target.get("sender"), str) else None
        sender_name = target.get("accountName") if isinstance(target.get("accountName"), str) else None
        owner_base = owner_id.split("_")[0] if isinstance(owner_id, str) and owner_id else None
        is_self = False
        if owner_id and sender_id == owner_id:
            is_self = True
        if owner_base and sender_id == owner_base:
            is_self = True
        if sender_name == "我":
            is_self = True
        direction = "outbound" if is_self else "inbound"
        return {
            "sender_id": sender_id,
            "sender_name": sender_name,
            "contact_name": contact_name,
            "direction": direction,
        }

    async def ingest_inbound(self, msg: InboundMessage) -> dict[str, Any]:
        now = int(time.time()) if msg.timestamp is None else int(msg.timestamp)
        event_type = None
        if isinstance(msg.raw, dict):
            event_type = msg.raw.get("event")
        direction = "revoke" if event_type == "message.revoke" else "inbound"
        event = {
            "event_id": str(uuid.uuid4()),
            "contact_id": msg.contact_id,
            "contact_name": msg.contact_name,
            "timestamp": now,
            "sender": msg.sender_id or "unknown",
            "sender_name": msg.sender_name,
            "direction": direction,
            "content": msg.content,
            "platform_message_id": msg.platform_message_id,
            "ai_candidates": None,
            "meta": msg.raw or None,
        }
        self._events_store(msg.contact_id).append_and_trim(event, max_lines=self._cache_max_messages)

        if direction == "inbound":
            asyncio.create_task(self._generate_and_store_candidates(msg))
        return {"status": "accepted"}

    async def _generate_and_store_candidates(self, msg: InboundMessage) -> None:
        selected_id = self.get_selected_assistant_id(msg.contact_id)
        role = self.get_assistant(selected_id) if selected_id else None
        if role is None:
            role = self.get_role(msg.contact_id)
        profile = self.get_profile(msg.contact_id)
        context = self.get_recent_texts(msg.contact_id, limit=self._context_messages)
        if len(context) < self._context_messages:
            more = await self._try_fetch_weflow_context(
                talker=msg.contact_id,
                limit=self._context_messages,
            )
            merged = [t for t in (more + context) if t]
            context = merged[-self._context_messages :]

        if profile is None:
            base_texts = self.get_recent_texts(msg.contact_id, limit=200)
            profile = build_tone_profile(base_texts)
            self._profile_store(msg.contact_id).write({"tone": profile.__dict__})

        prompt = _build_prompt(
            role=role,
            profile=profile,
            context=context,
            incoming=msg.content,
        )
        try:
            candidates = await with_timeout(
                self._llm.generate_candidates(
                    prompt=prompt,
                    count=self._candidate_count,
                    timeout_sec=self._reply_timeout_sec,
                ),
                timeout_sec=self._reply_timeout_sec,
            )
            err = None
        except Exception as e:
            candidates = []
            err = str(e)

        event = {
            "event_id": str(uuid.uuid4()),
            "contact_id": msg.contact_id,
            "contact_name": msg.contact_name,
            "timestamp": int(time.time()),
            "sender": "wxbot",
            "sender_name": "wxbot",
            "direction": "candidate",
            "content": "",
            "platform_message_id": msg.platform_message_id,
            "ai_candidates": candidates[:5],
            "meta": {"role_id": role.role_id, "error": err} if err else {"role_id": role.role_id},
        }
        self._events_store(msg.contact_id).append_and_trim(event, max_lines=self._cache_max_messages)

    async def _try_fetch_weflow_context(self, *, talker: str, limit: int) -> list[str]:
        try:
            data = await self._weflow.get_messages(talker=talker, limit=min(200, max(1, limit)), offset=0, chatlab=False)
        except Exception:
            return []
        messages = data.get("messages") if isinstance(data, dict) else None
        if not isinstance(messages, list):
            return []
        out: list[str] = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            c = m.get("content")
            if isinstance(c, str) and c.strip():
                out.append(c.strip())
        return out

    async def send_outbound(self, contact_id: str, content: str) -> dict[str, Any]:
        resp = await self._weflow.send_text(contact_id=contact_id, content=content)
        event = {
            "event_id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "contact_name": None,
            "timestamp": int(time.time()),
            "sender": "wxbot",
            "sender_name": "wxbot",
            "direction": "outbound",
            "content": content,
            "platform_message_id": None,
            "ai_candidates": None,
            "meta": {"weflow": resp},
        }
        self._events_store(contact_id).append_and_trim(event, max_lines=self._cache_max_messages)
        return resp

    def get_recent_events(self, contact_id: str, limit: int) -> list[dict[str, Any]]:
        return self._events_store(contact_id).tail(limit)

    async def generate_candidates_now(self, contact_id: str) -> list[str]:
        events = self.get_recent_events(contact_id, limit=200)
        last = None
        for e in reversed(events):
            if e.get("direction") == "inbound" and isinstance(e.get("content"), str) and e.get("content").strip():
                last = e
                break
        if not isinstance(last, dict):
            return []
        msg = InboundMessage(
            contact_id=contact_id,
            contact_name=last.get("contact_name") if isinstance(last.get("contact_name"), str) else None,
            sender_id=last.get("sender") if isinstance(last.get("sender"), str) else None,
            sender_name=last.get("sender_name") if isinstance(last.get("sender_name"), str) else None,
            timestamp=last.get("timestamp") if isinstance(last.get("timestamp"), int) else None,
            content=last.get("content") or "",
            platform_message_id=last.get("platform_message_id") if isinstance(last.get("platform_message_id"), str) else None,
            raw=last.get("meta") if isinstance(last.get("meta"), dict) else None,
        )
        await self._generate_and_store_candidates(msg)
        evts = self.get_recent_events(contact_id, limit=200)
        for e in reversed(evts):
            if e.get("direction") == "candidate" and isinstance(e.get("ai_candidates"), list):
                meta = e.get("meta")
                if isinstance(meta, dict) and isinstance(meta.get("error"), str) and meta.get("error"):
                    raise RuntimeError(meta.get("error"))
                return [x for x in e["ai_candidates"] if isinstance(x, str) and x.strip()][:5]
        return []

    def get_recent_texts(self, contact_id: str, limit: int) -> list[str]:
        events = self.get_recent_events(contact_id, limit=limit * 2)
        texts: list[str] = []
        for e in events:
            if e.get("direction") in ("inbound", "outbound") and isinstance(e.get("content"), str):
                if e["content"].strip():
                    texts.append(e["content"].strip())
        return texts[-limit:]

    def set_role(self, contact_id: str, role: RoleConfig) -> None:
        self._role_store(contact_id).write(role.model_dump())

    def get_role(self, contact_id: str) -> RoleConfig:
        raw = self._role_store(contact_id).read()
        if not raw:
            return RoleConfig()
        return RoleConfig.model_validate(raw)

    def recompute_profile(self, contact_id: str) -> ToneProfile:
        texts = self.get_recent_texts(contact_id, limit=200)
        profile = build_tone_profile(texts)
        self._profile_store(contact_id).write({"tone": profile.__dict__})
        return profile

    def get_profile(self, contact_id: str) -> ToneProfile | None:
        raw = self._profile_store(contact_id).read()
        if not raw:
            return None
        tone = raw.get("tone") if isinstance(raw, dict) else None
        if not isinstance(tone, dict):
            return None
        try:
            return ToneProfile(**tone)
        except Exception:
            return None


def _build_prompt(*, role: RoleConfig, profile: ToneProfile | None, context: list[str], incoming: str) -> str:
    role_block = f"角色设定：{role.name}\n"
    if getattr(role, "system_prompt", ""):
        role_block += f"系统提示词：{role.system_prompt}\n"
    else:
        role_block += (
            f"性格特征：{role.personality}\n"
            f"语言风格：{role.language_style}\n"
            f"专业知识：{role.expertise}\n"
        )
    if role.constraints:
        role_block += "约束：\n" + "\n".join(f"- {c}" for c in role.constraints) + "\n"
    if role.example_replies:
        role_block += "示例回复：\n" + "\n".join(f"- {x}" for x in role.example_replies[:5]) + "\n"

    profile_block = profile.to_prompt() + "\n" if profile else ""
    context_block = "\n".join(f"- {t}" for t in context[-20:])
    return (
        f"{role_block}"
        f"{profile_block}"
        "最近对话（按时间）：\n"
        f"{context_block}\n"
        "对方最新消息：\n"
        f"{incoming}"
    )
