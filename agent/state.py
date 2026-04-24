"""MemoryState — state dict truyền giữa các node của graph."""
from __future__ import annotations
from typing import TypedDict, Any


class MemoryState(TypedDict, total=False):
    # input
    user_input: str
    # conversation
    messages: list[dict]           # short-term buffer snapshot
    # memory retrieval
    user_profile: dict[str, Any]
    episodes: list[dict]
    semantic_hits: list[dict]
    # control
    memory_budget: int             # tính theo "words"
    # output
    prompt: str
    response: str
    # writes executed in save_memory node
    writes: list[dict]
