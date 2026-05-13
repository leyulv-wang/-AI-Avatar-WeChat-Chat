from __future__ import annotations

from typing import Any

import httpx


class WeFlowClient:
    def __init__(
        self,
        *,
        base_url: str | None,
        token: str | None,
        sse_path: str | None,
        messages_path: str | None,
        send_path: str | None,
    ):
        self._base_url = (base_url or "").rstrip("/")
        self._token = token
        self._sse_path = sse_path
        self._messages_path = messages_path
        self._send_path = send_path

    def _headers(self) -> dict[str, str]:
        return {}

    def sse_url(self) -> str | None:
        if not (self._base_url and self._sse_path and self._token):
            return None
        token = httpx.QueryParams({"access_token": self._token})
        return f"{self._base_url}{self._sse_path}?{token}"

    async def get_messages(self, *, talker: str, limit: int = 100, offset: int = 0, chatlab: bool = False) -> dict[str, Any]:
        if not (self._base_url and self._messages_path):
            raise RuntimeError("WEFLOW_BASE_URL/WEFLOW_MESSAGES_PATH 未配置")
        data = await self._get_messages_once(talker=talker, limit=limit, offset=offset, chatlab=chatlab)
        msgs = data.get("messages") if isinstance(data, dict) else None
        if chatlab and isinstance(msgs, list) and len(msgs) == 0:
            data2 = await self._get_messages_once(talker=talker, limit=limit, offset=offset, chatlab=False)
            if isinstance(data2, dict) and isinstance(data2.get("messages"), list) and len(data2["messages"]) > 0:
                return data2
        return data

    async def _get_messages_once(self, *, talker: str, limit: int, offset: int, chatlab: bool) -> dict[str, Any]:
        params = {"talker": talker, "limit": str(limit), "offset": str(offset)}
        if chatlab:
            params["chatlab"] = "1"
        if self._token:
            params["access_token"] = self._token
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(
                f"{self._base_url}{self._messages_path}",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        return data if isinstance(data, dict) else {"data": data}

    async def send_text(self, *, contact_id: str, content: str) -> dict[str, Any]:
        if not (self._base_url and self._send_path):
            raise RuntimeError("WEFLOW_BASE_URL/WEFLOW_SEND_PATH 未配置")
        payload = {"contact_id": contact_id, "content": content, "type": "text"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.post(f"{self._base_url}{self._send_path}", headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
