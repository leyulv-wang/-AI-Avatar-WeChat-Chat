from __future__ import annotations

import respx
from httpx import Response
import asyncio

from wxbot.weflow import WeFlowClient


def test_sse_url_includes_access_token():
    c = WeFlowClient(
        base_url="http://127.0.0.1:5031",
        token="t",
        sse_path="/api/v1/push/messages",
        messages_path="/api/v1/messages",
        send_path=None,
    )
    u = c.sse_url()
    assert u == "http://127.0.0.1:5031/api/v1/push/messages?access_token=t"


@respx.mock
def test_get_messages_uses_bearer_header():
    route = respx.get("http://127.0.0.1:5031/api/v1/messages").mock(
        return_value=Response(200, json={"messages": [{"content": "x"}]})
    )
    c = WeFlowClient(
        base_url="http://127.0.0.1:5031",
        token="t",
        sse_path=None,
        messages_path="/api/v1/messages",
        send_path=None,
    )
    data = asyncio.run(c.get_messages(talker="wxid_x", limit=1, offset=0, chatlab=True))
    assert route.called
    req = route.calls[0].request
    assert "access_token=t" in str(req.url)
    assert data["messages"][0]["content"] == "x"
