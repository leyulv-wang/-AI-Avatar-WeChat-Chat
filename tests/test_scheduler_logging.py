from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from wxbot.logging_config import configure_logging
from wxbot.scheduler import start_scheduler
from wxbot.service import BotService
from wxbot.weflow import WeFlowClient


class _LLM:
    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int):
        return []


def test_configure_logging_idempotent():
    import logging

    root = logging.getLogger()
    before = list(root.handlers)
    try:
        root.handlers = []
        configure_logging()
        assert root.handlers
        configure_logging()
    finally:
        root.handlers = before


def test_start_scheduler_and_shutdown(tmp_path: Path):
    import asyncio

    async def _run():
        f = Fernet(Fernet.generate_key())
        s = BotService(
            data_dir=tmp_path,
            fernet=f,
            llm=_LLM(),
            weflow=WeFlowClient(base_url=None, token=None, sse_path=None, messages_path=None, send_path=None),
            candidate_count=4,
            context_messages=5,
            reply_timeout_sec=5,
        )
        sch = start_scheduler(s)
        assert sch.running
        sch.shutdown(wait=False)

    asyncio.run(_run())
