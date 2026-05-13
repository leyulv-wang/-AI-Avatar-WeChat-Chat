from __future__ import annotations

import respx
from httpx import Response
import asyncio

from wxbot.llm import OllamaProvider, OpenAICompatibleProvider, _parse_candidates


def test_parse_candidates_json():
    out = _parse_candidates('["a", "b"]')
    assert out == ["a", "b"]


def test_parse_candidates_fallback_lines():
    out = _parse_candidates("- a\n- b\n")
    assert out == ["a", "b"]


@respx.mock
def test_openai_compatible_provider_endpoint_and_multi_choice():
    route = respx.post("http://gw.local/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "[\"a\",\"b\"]"}},
                    {"message": {"content": "[\"c\",\"d\"]"}},
                ]
            },
        )
    )
    p = OpenAICompatibleProvider(base_url="http://gw.local", api_key="k", model="m")
    out = asyncio.run(p.generate_candidates(prompt="hi", count=4, timeout_sec=5))
    assert route.called
    assert out[:4] == ["a", "b", "c", "d"]


@respx.mock
def test_openai_compatible_provider_custom_path():
    route = respx.post("http://gw.local/custom").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "[\"x\",\"y\",\"z\"]"}}]})
    )
    p = OpenAICompatibleProvider(
        base_url="http://gw.local",
        api_key="k",
        model="m",
        chat_completions_path="/custom",
    )
    out = asyncio.run(p.generate_candidates(prompt="hi", count=3, timeout_sec=5))
    assert route.called
    assert out == ["x", "y", "z"]


@respx.mock
def test_ollama_provider_calls_api():
    route = respx.post("http://ollama.local/api/chat").mock(
        return_value=Response(200, json={"message": {"content": "[\"x\",\"y\",\"z\"]"}})
    )
    p = OllamaProvider(base_url="http://ollama.local", model="llama3")
    out = asyncio.run(p.generate_candidates(prompt="hi", count=3, timeout_sec=5))
    assert route.called
    assert out == ["x", "y", "z"]
