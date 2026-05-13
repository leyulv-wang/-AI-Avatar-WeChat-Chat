from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


_EMOJI_HINTS = [
    "[表情包]",
    "[叹气]",
    "[捂脸]",
    "[笑]",
    "[哭]",
]


@dataclass(frozen=True)
class ToneProfile:
    avg_len: float
    punctuation_ratio: float
    emoji_token_top: list[str]
    common_endings: list[str]
    informal_ratio: float

    def to_prompt(self) -> str:
        endings = "、".join(self.common_endings) if self.common_endings else ""
        emojis = "、".join(self.emoji_token_top) if self.emoji_token_top else ""
        return (
            f"对方语言特征（从历史统计）：平均长度≈{self.avg_len:.1f}；标点密度≈{self.punctuation_ratio:.2f}；"
            f"常见情绪/表情标记：{emojis}；常见句末：{endings}；口语化比例≈{self.informal_ratio:.2f}。"
        )


def build_tone_profile(texts: list[str]) -> ToneProfile:
    if not texts:
        return ToneProfile(avg_len=0.0, punctuation_ratio=0.0, emoji_token_top=[], common_endings=[], informal_ratio=0.0)

    lens = [len(t) for t in texts if t]
    avg_len = sum(lens) / max(1, len(lens))

    punct = 0
    total = 0
    for t in texts:
        total += len(t)
        punct += len(re.findall(r"[。！？!?，,；;：:]", t))
    punctuation_ratio = punct / max(1, total)

    emoji_counter = Counter()
    for t in texts:
        for token in _EMOJI_HINTS:
            if token in t:
                emoji_counter[token] += 1
    emoji_token_top = [k for k, _ in emoji_counter.most_common(3)]

    endings_counter = Counter()
    for t in texts:
        m = re.search(r"([\u4e00-\u9fff]{1,3})[。！？!?]*$", t.strip())
        if m:
            endings_counter[m.group(1)] += 1
    common_endings = [k for k, _ in endings_counter.most_common(5)]

    informal_markers = ["哈哈", "hhh", "emmm", "啊", "呀", "诶", "嗷", "吧", "呗", "啦", "嘛"]
    informal_hits = 0
    for t in texts:
        if any(m in t for m in informal_markers):
            informal_hits += 1
    informal_ratio = informal_hits / max(1, len(texts))

    return ToneProfile(
        avg_len=avg_len,
        punctuation_ratio=punctuation_ratio,
        emoji_token_top=emoji_token_top,
        common_endings=common_endings,
        informal_ratio=informal_ratio,
    )

