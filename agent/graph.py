"""LangGraph-style skeleton.

Luồng:
    user_input
        │
        ▼
    retrieve_memory ──► build_prompt ──► call_llm ──► save_memory
                                                           │
                                                           ▼
                                                       response

Mỗi node là một pure function `state → state`. Router gom memory từ 4
backends (short-term / profile / episodic / semantic) vào state trước
khi build prompt. Nếu cài được `langgraph`, ta compile graph thật;
nếu không, chạy sequential pipeline tương đương.
"""
from __future__ import annotations
from typing import Callable

from .state import MemoryState
from .memory import ShortTermMemory, ProfileMemory, EpisodicMemory, SemanticMemory
from .prompts import build_prompt, build_prompt_no_memory
from .llm import call_llm
from .extractor import extract


class MemoryAgent:
    def __init__(
        self,
        profile_path: str,
        episodic_path: str,
        kb_dir: str,
        short_term_window: int = 8,
        memory_budget: int = 400,
    ):
        self.short_term = ShortTermMemory(window=short_term_window)
        self.profile = ProfileMemory(profile_path)
        self.episodic = EpisodicMemory(episodic_path)
        self.semantic = SemanticMemory(kb_dir)
        self.memory_budget = memory_budget
        self._graph = self._compile()

    # ============ NODES ============
    def retrieve_memory(self, state: MemoryState) -> MemoryState:
        """Router: gom memory từ 4 backends vào state."""
        query = state["user_input"]
        state["messages"] = self.short_term.recent()
        state["user_profile"] = self.profile.all()
        state["episodes"] = self.episodic.recall(query, k=3)
        state["semantic_hits"] = self.semantic.search(query, k=3)
        state["memory_budget"] = self.memory_budget
        return state

    def build_prompt_node(self, state: MemoryState) -> MemoryState:
        state["prompt"] = build_prompt(state)
        return state

    def call_llm_node(self, state: MemoryState) -> MemoryState:
        state["response"] = call_llm(state["prompt"])
        return state

    def save_memory(self, state: MemoryState) -> MemoryState:
        """Ghi user turn vào short-term + extract facts + episodic outcome."""
        user_input = state["user_input"]
        response = state.get("response", "")

        # 1. short-term
        self.short_term.add("user", user_input)
        self.short_term.add("assistant", response)

        # 2. extract & write
        writes = extract(user_input)
        applied = []
        for w in writes:
            if w["target"] == "profile":
                self.profile.set(w["key"], w["value"], source=w.get("source", "user"))
                applied.append(w)
            elif w["target"] == "episodic":
                self.episodic.add(w["summary"], w.get("outcome", ""), w.get("tags", []))
                applied.append(w)
        state["writes"] = applied
        return state

    # ============ GRAPH ============
    def _compile(self) -> Callable[[MemoryState], MemoryState]:
        """Dùng langgraph thật nếu có, không thì fallback sequential."""
        try:
            from langgraph.graph import StateGraph, END  # type: ignore
        except ImportError:
            def pipeline(state: MemoryState) -> MemoryState:
                state = self.retrieve_memory(state)
                state = self.build_prompt_node(state)
                state = self.call_llm_node(state)
                state = self.save_memory(state)
                return state
            return pipeline

        # Dùng MemoryState (TypedDict) làm schema để LangGraph
        # biết cách merge output giữa các node.
        g = StateGraph(MemoryState)
        g.add_node("retrieve_memory", self.retrieve_memory)
        g.add_node("build_prompt", self.build_prompt_node)
        g.add_node("call_llm", self.call_llm_node)
        g.add_node("save_memory", self.save_memory)
        g.set_entry_point("retrieve_memory")
        g.add_edge("retrieve_memory", "build_prompt")
        g.add_edge("build_prompt", "call_llm")
        g.add_edge("call_llm", "save_memory")
        g.add_edge("save_memory", END)
        compiled = g.compile()
        self._langgraph_compiled = compiled  # giữ reference để inspect
        return compiled.invoke

    # ============ PUBLIC API ============
    def chat(self, user_input: str) -> dict:
        """Một turn có memory đầy đủ."""
        state: MemoryState = {"user_input": user_input}
        state = self._graph(state)
        return {
            "response": state["response"],
            "prompt": state["prompt"],
            "prompt_tokens": len(state["prompt"].split()),
            "writes": state.get("writes", []),
        }

    def chat_no_memory(self, user_input: str) -> dict:
        """Baseline: không retrieve, không save, không inject vào prompt."""
        prompt = build_prompt_no_memory({"user_input": user_input})
        response = call_llm(prompt)
        return {
            "response": response,
            "prompt": prompt,
            "prompt_tokens": len(prompt.split()),
            "writes": [],
        }

    def reset(self) -> None:
        self.short_term.clear()
        self.profile.clear()
        self.episodic.clear()
