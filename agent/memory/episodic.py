"""Episodic memory — log các sự kiện/outcome có ý nghĩa.

Backend: JSONL file, mỗi dòng là một episode. Recall theo keyword +
recency score đơn giản.
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class EpisodicMemory:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._episodes: list[dict] = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._episodes.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    def add(self, summary: str, outcome: str = "", tags: list[str] | None = None) -> dict:
        ep = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "outcome": outcome,
            "tags": tags or [],
        }
        self._episodes.append(ep)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ep, ensure_ascii=False) + "\n")
        return ep

    def all(self) -> list[dict]:
        return list(self._episodes)

    def recall(self, query: str, k: int = 3) -> list[dict]:
        """Keyword overlap + recency bonus. Đủ cho skeleton."""
        if not self._episodes:
            return []
        q_tokens = set(_tokenize(query))
        scored = []
        n = len(self._episodes)
        for idx, ep in enumerate(self._episodes):
            text = f"{ep['summary']} {ep['outcome']} {' '.join(ep.get('tags', []))}"
            e_tokens = set(_tokenize(text))
            overlap = len(q_tokens & e_tokens)
            recency = (idx + 1) / n  # newer → higher
            score = overlap + 0.2 * recency
            if overlap > 0:
                scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:k]]

    def clear(self) -> None:
        self._episodes = []
        if os.path.exists(self.path):
            os.remove(self.path)
