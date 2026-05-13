from __future__ import annotations

import asyncio
from pathlib import Path

from wxbot.service import BotService
from wxbot.weflow import WeFlowClient


class _LLM:
    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int):
        return []


def _service(tmp_path: Path) -> BotService:
    return BotService(
        data_dir=tmp_path,
        fernet=None,
        llm=_LLM(),
        weflow=WeFlowClient(base_url=None, token=None, sse_path=None, messages_path=None, send_path=None),
        candidate_count=4,
        context_messages=5,
        reply_timeout_sec=5,
        storage_encrypt=False,
        cache_max_messages=50,
    )


def test_weflow_rawid_dedup_persists_across_restart(tmp_path: Path):
    payload = {
        "event": "message.new",
        "sessionId": "wxid_x",
        "rawid": "123",
        "sourceName": "张三",
        "content": "你好",
        "timestamp": 1760000123,
    }

    s1 = _service(tmp_path)
    assert asyncio.run(s1.ingest_weflow_payload(payload)) is True
    assert asyncio.run(s1.ingest_weflow_payload(payload)) is False

    s2 = _service(tmp_path)
    assert asyncio.run(s2.ingest_weflow_payload(payload)) is False
