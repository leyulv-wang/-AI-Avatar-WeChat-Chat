from __future__ import annotations

from wxbot.weflow_listener import _parse_sse_events


def test_parse_sse_events_message_new():
    s = (
        "event: message.new\n"
        "data: {\"event\":\"message.new\",\"sessionId\":\"wxid_x\",\"rawid\":\"1\",\"sourceName\":\"张三\",\"content\":\"你好\",\"timestamp\":1760000123}\n"
        "\n"
    )
    evts = _parse_sse_events(s)
    assert len(evts) == 1
    assert evts[0]["event"] == "message.new"
    assert evts[0]["sessionId"] == "wxid_x"
    assert evts[0]["rawid"] == "1"
    assert evts[0]["content"] == "你好"
