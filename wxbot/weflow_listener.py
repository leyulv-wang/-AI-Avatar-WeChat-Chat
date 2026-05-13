from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx

from wxbot.service import BotService
from wxbot.weflow import WeFlowClient


logger = logging.getLogger("wxbot.weflow_listener")


def _parse_sse_events(text: str) -> list[dict]:
    events: list[dict] = []
    current_event: str | None = None
    current_data: list[str] = []
    for line in text.splitlines():
        line = line.rstrip("\r")
        if not line:
            if current_data:
                data_str = "\n".join(current_data)
                try:
                    payload = json.loads(data_str)
                except Exception:
                    payload = {"raw": data_str}
                if isinstance(payload, dict):
                    if current_event:
                        payload.setdefault("event", current_event)
                    events.append(payload)
            current_event = None
            current_data = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            current_event = line[len("event:") :].strip()
            continue
        if line.startswith("data:"):
            current_data.append(line[len("data:") :].lstrip())
            continue
    return events
async def run_sse_listener(*, service: BotService, weflow: WeFlowClient) -> None:
    url = weflow.sse_url()
    if not url:
        logger.info("WeFlow SSE 未配置，跳过监听")
        return

    while True:
        try:
            timeout = httpx.Timeout(connect=5.0, read=120.0, write=5.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    buf: list[str] = []
                    async for chunk in resp.aiter_text():
                        buf.append(chunk)
                        text = "".join(buf)
                        if "\n\n" not in text:
                            continue
                        parts = text.split("\n\n")
                        buf = [parts[-1]]
                        for part in parts[:-1]:
                            for evt in _parse_sse_events(part + "\n\n"):
                                await service.ingest_weflow_payload(evt)
        except Exception as e:
            logger.warning("WeFlow SSE 断开，5 秒后重连: %s", e)
            await asyncio.sleep(5)
