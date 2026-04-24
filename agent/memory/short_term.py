"""Short-term memory: sliding window của các message gần nhất."""
from __future__ import annotations
from collections import deque
from typing import Iterable


class ShortTermMemory:
    """Conversation buffer dạng sliding window.

    Lưu các cặp (role, content) gần nhất. Khi vượt `window` thì
    message cũ nhất bị đẩy ra.
    """

    def __init__(self, window: int = 8):
        self.window = window
        self._buf: deque[dict] = deque(maxlen=window)

    def add(self, role: str, content: str) -> None:
        self._buf.append({"role": role, "content": content})

    def recent(self, n: int | None = None) -> list[dict]:
        if n is None or n >= len(self._buf):
            return list(self._buf)
        return list(self._buf)[-n:]

    def clear(self) -> None:
        self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)

    def extend(self, messages: Iterable[dict]) -> None:
        for m in messages:
            self._buf.append(m)
