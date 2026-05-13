from __future__ import annotations

from wxbot.tone import build_tone_profile


def test_build_tone_profile_basic():
    profile = build_tone_profile(["哈哈可以。", "我其实不知道[叹气]", "端午节可以"])
    assert profile.avg_len > 0
    assert profile.punctuation_ratio >= 0

