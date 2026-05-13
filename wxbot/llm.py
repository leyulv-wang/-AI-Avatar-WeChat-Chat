from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str


class LLMProvider:
    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int) -> list[str]:
        raise NotImplementedError


class MockProvider(LLMProvider):
    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int) -> list[str]:
        base = [
            "收到，我想想怎么安排。",
            "可以呀，你更倾向哪里？",
            "哈哈可以，具体时间你方便吗？",
            "我觉得这样安排比较稳：先……",
            "行，那就按这个来。",
        ]
        return base[: max(1, min(count, 5))]


class OllamaProvider(LLMProvider):
    def __init__(self, *, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int) -> list[str]:
        instruction = (
            "你是微信私聊的智能回复助手。只输出严格 JSON 数组，数组元素为候选回复字符串。"
            f"输出 {count} 条，每条不超过 60 个字，符合角色与语气要求。不要输出任何额外文本。"
        )
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
        }
        timeout = httpx.Timeout(timeout_sec)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = (((data or {}).get("message") or {}).get("content"))
        if not isinstance(content, str):
            return []
        return _parse_candidates(content)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        chat_completions_path: str | None = None,
    ):
        self._base_url = _strip_wrapping_quotes(base_url).rstrip("/")
        self._api_key = api_key
        self._model = model
        self._chat_path = _strip_wrapping_quotes(chat_completions_path) if chat_completions_path else None

    def _endpoint(self) -> str:
        if self._chat_path:
            if self._chat_path.startswith("http://") or self._chat_path.startswith("https://"):
                return self._chat_path
            if not self._chat_path.startswith("/"):
                return f"{self._base_url}/{self._chat_path}"
            return f"{self._base_url}{self._chat_path}"

        base = self._base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1/chat"):
            return f"{base}/completions"
        return f"{base}/chat/completions"

    async def generate_candidates(self, *, prompt: str, count: int, timeout_sec: int) -> list[str]:
        instruction = (
            "你是微信私聊的智能回复助手。输出候选回复，用简洁口语化中文。"
            "只输出内容本身，不要解释。"
        )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": instruction},
                {
                    "role": "user",
                    "content": (
                        "请输出严格 JSON 数组（数组元素为字符串），不要输出任何额外文本。"
                        f"输出 {count} 条，每条不超过 60 个字。\n\n"
                        f"{prompt}"
                    ),
                },
            ],
            "temperature": 0.7,
            "stream": False,
            "max_tokens": 256,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(timeout_sec)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self._endpoint(), json=payload, headers=headers)
            if resp.status_code >= 400:
                detail = resp.text
                if isinstance(detail, str) and len(detail) > 800:
                    detail = detail[:800] + "..."
                raise RuntimeError(f"LLM 请求失败 HTTP {resp.status_code}: {detail}")
            data = resp.json()

        choices = (data or {}).get("choices") if isinstance(data, dict) else None
        if isinstance(choices, list) and choices:
            texts: list[str] = []
            for ch in choices:
                if not isinstance(ch, dict):
                    continue
                msg = ch.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    texts.append(msg["content"].strip())
                elif isinstance(ch.get("text"), str):
                    texts.append(ch["text"].strip())
            if len(texts) == 1:
                return _parse_candidates(texts[0])
            out: list[str] = []
            for t in texts:
                out.extend(_parse_candidates(t))
            dedup: list[str] = []
            seen = set()
            for x in out:
                if x and x not in seen:
                    dedup.append(x)
                    seen.add(x)
            return dedup[: max(1, min(count, 5))]

        content = None
        if isinstance(data, dict):
            content = (((data.get("message") or {}) if isinstance(data.get("message"), dict) else {}).get("content"))
        if isinstance(content, str):
            return _parse_candidates(content)
        return []


def _parse_candidates(text: str) -> list[str]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            out = [str(x).strip() for x in obj if str(x).strip()]
            return out
    except Exception:
        pass
    lines = [ln.strip("-• \t") for ln in text.splitlines() if ln.strip()]
    out = [ln for ln in lines if ln]
    return out


def _strip_wrapping_quotes(v: str) -> str:
    s = v.strip()
    if len(s) >= 2 and (s[0] == s[-1] and s[0] in ("'", '"', "`")):
        s = s[1:-1].strip()
    return s


async def with_timeout(coro, timeout_sec: int):
    return await asyncio.wait_for(coro, timeout=timeout_sec)
