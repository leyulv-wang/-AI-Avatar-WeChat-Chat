from __future__ import annotations

import asyncio
from pathlib import Path

from cryptography.fernet import Fernet

from wxbot.models import InboundMessage, RoleConfig
from wxbot.service import BotService
from wxbot.weflow import WeFlowClient


class _FakeLLM:
    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int):
        return [f"r{i}" for i in range(count)]


class _FakeWeFlow(WeFlowClient):
    def __init__(self):
        super().__init__(base_url=None, token=None, sse_path=None, messages_path=None, send_path=None)

    async def get_messages(self, *, talker: str, limit: int = 100, offset: int = 0, chatlab: bool = False):
        return {"messages": [{"content": "h1"}, {"content": "h2"}]}

    async def send_text(self, *, contact_id: str, content: str):
        return {"ok": True, "contact_id": contact_id, "content": content}


def _service(tmp_path: Path) -> BotService:
    key = Fernet.generate_key()
    f = Fernet(key)
    return BotService(
        data_dir=tmp_path,
        fernet=f,
        llm=_FakeLLM(),
        weflow=_FakeWeFlow(),
        candidate_count=4,
        context_messages=5,
        reply_timeout_sec=5,
        storage_encrypt=True,
        cache_max_messages=5,
    )


def test_ingest_inbound_writes_event(tmp_path: Path):
    s = _service(tmp_path)
    msg = InboundMessage(contact_id="wxid_x", content="你好")
    asyncio.run(s.ingest_inbound(msg))
    events = s.get_recent_events("wxid_x", limit=10)
    assert any(e.get("direction") == "inbound" and e.get("content") == "你好" for e in events)


def test_ingest_revoke_skips_generation(tmp_path: Path):
    s = _service(tmp_path)
    msg = InboundMessage(contact_id="wxid_x", content="撤回", raw={"event": "message.revoke"})
    asyncio.run(s.ingest_inbound(msg))
    events = s.get_recent_events("wxid_x", limit=10)
    assert any(e.get("direction") == "revoke" for e in events)


def test_generate_and_store_candidates(tmp_path: Path):
    s = _service(tmp_path)
    s.set_role("wxid_x", RoleConfig(name="测试角色"))
    msg = InboundMessage(contact_id="wxid_x", content="hi", platform_message_id="1")
    asyncio.run(s._generate_and_store_candidates(msg))
    events = s.get_recent_events("wxid_x", limit=10)
    cand = [e for e in events if e.get("direction") == "candidate"]
    assert cand
    assert cand[-1]["ai_candidates"] == ["r0", "r1", "r2", "r3"]


def test_send_outbound(tmp_path: Path):
    s = _service(tmp_path)
    resp = asyncio.run(s.send_outbound("wxid_x", "ok"))
    assert resp["ok"] is True
    events = s.get_recent_events("wxid_x", limit=10)
    assert any(e.get("direction") == "outbound" and e.get("content") == "ok" for e in events)
