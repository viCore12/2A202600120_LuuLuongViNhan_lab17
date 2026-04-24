"""Benchmark 10 multi-turn conversations: no-memory vs with-memory.

Mỗi conversation có:
  - category: nhóm test (profile/conflict/episodic/semantic/budget/...)
  - turns: list dict {input, expect_substr?}  — substring cần xuất hiện
           trong câu trả lời để tính "Pass".
  - assert_turn: index turn dùng để chấm Pass/Fail (default turn cuối).

Agent được reset giữa các conversation. Với mỗi conversation, chạy 2
lần: một lần không memory (tất cả turn dùng chat_no_memory), một lần
với memory (chat đầy đủ).

Output:
  - in console bảng tổng kết
  - ghi BENCHMARK.md đầy đủ (bảng + transcripts)
"""
from __future__ import annotations
import os
import shutil
from dataclasses import dataclass, field

from agent.graph import MemoryAgent
from agent.llm import approx_tokens

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass


@dataclass
class Turn:
    user: str
    expect: str | None = None  # substring cần có trong response


@dataclass
class Conversation:
    id: int
    category: str
    name: str
    turns: list[Turn]
    assert_turn: int = -1  # index turn dùng để chấm

    def assertion_turn(self) -> Turn:
        return self.turns[self.assert_turn]


CONVERSATIONS: list[Conversation] = [
    # 1. Profile recall sau nhiều turn
    Conversation(
        id=1, category="profile_recall",
        name="Recall user name after 6 turns",
        turns=[
            Turn("Chào bạn, tên tôi là Linh."),
            Turn("Tôi sống ở Hà Nội."),
            Turn("Tôi làm việc tại công ty BlueBolt."),
            Turn("Tôi thích lập trình bằng Python."),
            Turn("Hôm nay trời đẹp nhỉ."),
            Turn("Cảm ơn vì đã trò chuyện."),
            Turn("Tên tôi là gì?", expect="Linh"),
        ],
    ),
    # 2. Conflict update (bắt buộc theo rubric)
    Conversation(
        id=2, category="conflict_update",
        name="Allergy conflict — sữa bò → đậu nành",
        turns=[
            Turn("Tôi dị ứng sữa bò."),
            Turn("À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò."),
            Turn("Tôi bị dị ứng gì?", expect="đậu nành"),
        ],
    ),
    # 3. Episodic recall
    Conversation(
        id=3, category="episodic_recall",
        name="Recall previous debug lesson về docker",
        turns=[
            Turn("Mình đã fix bug docker networking bằng cách dùng service name thay vì localhost."),
            Turn("Sau đó deploy production thì ổn."),
            Turn("Hôm nay lại gặp lỗi container không kết nối, lần trước bug docker mình làm gì?",
                 expect="service"),
        ],
    ),
    # 4. Semantic retrieval — FAQ chunk
    Conversation(
        id=4, category="semantic_retrieval",
        name="Retrieve FAQ: chính sách hoàn tiền",
        turns=[
            Turn("Cho mình hỏi tí về chính sách."),
            Turn("Chính sách hoàn tiền của công ty thế nào?", expect="14 ngày"),
        ],
    ),
    # 5. Trim / token budget
    Conversation(
        id=5, category="budget_trim",
        name="Long conversation but still recall name",
        turns=[
            Turn("Tên tôi là Minh."),
            Turn("Tôi đang học về LangGraph."),
            Turn("Hôm qua tôi đọc về memory stack."),
            Turn("Hôm nay tôi code lab 17."),
            Turn("Tôi dự định dùng Chroma cho semantic."),
            Turn("Mình thấy TF-IDF cũng đủ cho lab."),
            Turn("Đang nghĩ về prompt injection pattern."),
            Turn("Buffer ngắn để tiết kiệm token."),
            Turn("Ủa mà tên tôi là gì nhỉ?", expect="Minh"),
        ],
    ),
    # 6. Multi-fact update
    Conversation(
        id=6, category="profile_recall",
        name="Recall favorite food và city cùng lúc",
        turns=[
            Turn("Tôi sống ở Đà Nẵng."),
            Turn("Tôi thích ăn mì Quảng."),
            Turn("Món ăn tôi thích ăn gì?", expect="mì Quảng"),
        ],
    ),
    # 7. Correction lần 2 — đổi location
    Conversation(
        id=7, category="conflict_update",
        name="Location correction — Hà Nội → Sài Gòn",
        turns=[
            Turn("Tôi sống ở Hà Nội."),
            Turn("À thực ra mình mới chuyển vào Sài Gòn rồi."),
            Turn("Tôi sống ở đâu?", expect="Sài Gòn"),
        ],
    ),
    # 8. Semantic — reset password
    Conversation(
        id=8, category="semantic_retrieval",
        name="Retrieve FAQ: reset mật khẩu",
        turns=[
            Turn("Tôi quên mật khẩu thì sao?"),
            Turn("Link reset mật khẩu có thời hạn bao lâu?", expect="30 phút"),
        ],
    ),
    # 9. Semantic — PII / privacy policy
    Conversation(
        id=9, category="semantic_retrieval",
        name="Retrieve FAQ: chính sách PII bảo mật",
        turns=[
            Turn("Chính sách bảo mật PII của công ty thế nào?", expect="AES-256"),
        ],
    ),
    # 10. Episodic + profile: combined — recall bug rootcause sau
    #     khi đã cập nhật nhiều fact khác
    Conversation(
        id=10, category="episodic_recall",
        name="Episodic + budget: recall sau 5 turn xen kẽ",
        turns=[
            Turn("Mình đã sửa bug auth bằng cách đổi JWT secret."),
            Turn("Tên tôi là Nam."),
            Turn("Tôi thích ăn phở."),
            Turn("Hôm nay mệt quá."),
            Turn("Lần trước bug auth mình làm gì nhỉ?", expect="JWT"),
        ],
    ),
]


@dataclass
class TurnResult:
    user: str
    response: str
    prompt_tokens: int
    writes: int


@dataclass
class ConvResult:
    conv: Conversation
    mode: str  # "no_memory" | "with_memory"
    turn_results: list[TurnResult] = field(default_factory=list)
    passed: bool = False

    def assertion_response(self) -> str:
        return self.turn_results[self.conv.assert_turn].response


def run_conversation(conv: Conversation, agent: MemoryAgent, mode: str) -> ConvResult:
    """Chạy conversation theo 1 mode, reset agent trước đó."""
    agent.reset()
    res = ConvResult(conv=conv, mode=mode)
    for turn in conv.turns:
        if mode == "no_memory":
            out = agent.chat_no_memory(turn.user)
        else:
            out = agent.chat(turn.user)
        res.turn_results.append(TurnResult(
            user=turn.user,
            response=out["response"],
            prompt_tokens=out["prompt_tokens"],
            writes=len(out.get("writes", [])),
        ))
    expected = conv.assertion_turn().expect
    actual = res.assertion_response()
    res.passed = (expected is not None) and (expected.lower() in actual.lower())
    return res


def run_all() -> tuple[list[ConvResult], list[ConvResult]]:
    tmp = ".tmp_bench"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    agent = MemoryAgent(
        profile_path=os.path.join(tmp, "profile.json"),
        episodic_path=os.path.join(tmp, "episodes.jsonl"),
        kb_dir="data/kb",
        short_term_window=8,
        memory_budget=300,
    )
    no_mem = [run_conversation(c, agent, "no_memory") for c in CONVERSATIONS]
    with_mem = [run_conversation(c, agent, "with_memory") for c in CONVERSATIONS]
    shutil.rmtree(tmp, ignore_errors=True)
    return no_mem, with_mem


# ---------- REPORT ----------
def _short(s: str, n: int = 80) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def render_markdown(no_mem: list[ConvResult], with_mem: list[ConvResult]) -> str:
    import os as _os
    lines: list[str] = []
    lines.append("# BENCHMARK — Lab 17 Multi-Memory Agent\n")
    # metadata về backend chạy benchmark
    has_key = bool(_os.getenv("OPENAI_API_KEY"))
    model = _os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm_backend = f"OpenAI `{model}`" if has_key else "mock deterministic"
    try:
        from langgraph.graph import StateGraph  # type: ignore  # noqa: F401
        graph_backend = "LangGraph thật (`StateGraph`)"
    except ImportError:
        graph_backend = "Skeleton LangGraph (pure-Python fallback)"
    try:
        import tiktoken  # type: ignore  # noqa: F401
        tok_backend = "tiktoken (`cl100k_base`)"
    except ImportError:
        tok_backend = "word count"
    lines.append(f"**LLM:** {llm_backend}  ")
    lines.append(f"**Graph:** {graph_backend}  ")
    lines.append(f"**Token counter:** {tok_backend}  \n")
    lines.append(
        "So sánh **no-memory baseline** vs **with-memory agent** trên 10 "
        "multi-turn conversations.\n"
    )
    lines.append("## Summary\n")
    n_pass_nom = sum(1 for r in no_mem if r.passed)
    n_pass_wm = sum(1 for r in with_mem if r.passed)
    lines.append(f"- Pass @ no-memory: **{n_pass_nom}/10**")
    lines.append(f"- Pass @ with-memory: **{n_pass_wm}/10**")
    avg_nom = sum(r.turn_results[-1].prompt_tokens for r in no_mem) / len(no_mem)
    avg_wm = sum(r.turn_results[-1].prompt_tokens for r in with_mem) / len(with_mem)
    lines.append(f"- Avg prompt tokens (final turn) — no-memory: "
                 f"{avg_nom:.0f} | with-memory: {avg_wm:.0f}\n")

    # ---- coverage các nhóm test ----
    cats = sorted({r.conv.category for r in with_mem})
    lines.append("### Coverage các nhóm test\n")
    lines.append("| Nhóm test | # conversations | Pass (with-memory) |")
    lines.append("|---|---:|---:|")
    for cat in cats:
        total = sum(1 for r in with_mem if r.conv.category == cat)
        passed = sum(1 for r in with_mem if r.conv.category == cat and r.passed)
        lines.append(f"| {cat} | {total} | {passed}/{total} |")
    lines.append("")

    # ---- bảng tổng ----
    lines.append("## Kết quả tổng hợp\n")
    lines.append("| # | Category | Scenario | No-memory result | With-memory result | Pass? |")
    lines.append("|---|---|---|---|---|:-:|")
    for nom_r, wm_r in zip(no_mem, with_mem):
        c = nom_r.conv
        expected = c.assertion_turn().expect or ""
        nom_ans = _short(nom_r.assertion_response(), 60)
        wm_ans = _short(wm_r.assertion_response(), 60)
        # cột Pass chính là with-memory, vì no-memory dự kiến fail
        tick = "✅" if wm_r.passed else "❌"
        lines.append(
            f"| {c.id} | {c.category} | {c.name} | {nom_ans} | {wm_ans} | {tick} |"
        )
    lines.append("")

    # ---- transcripts ----
    lines.append("## Transcripts chi tiết\n")
    for nom_r, wm_r in zip(no_mem, with_mem):
        c = nom_r.conv
        lines.append(f"### Conversation #{c.id} — {c.name}\n")
        lines.append(f"**Category:** `{c.category}` — **Expected substring:** "
                     f"`{c.assertion_turn().expect}`\n")
        lines.append("**Turns (with-memory mode):**\n")
        for t in wm_r.turn_results:
            lines.append(f"- user: {t.user}")
            lines.append(f"  - assistant: {t.response}")
            lines.append(f"  - prompt_tokens: {t.prompt_tokens}, writes: {t.writes}")
        lines.append("")
        lines.append(
            f"**Assertion turn — no-memory answer:** "
            f"`{_short(nom_r.assertion_response(), 100)}`"
        )
        lines.append(
            f"**Assertion turn — with-memory answer:** "
            f"`{_short(wm_r.assertion_response(), 100)}`"
        )
        lines.append(f"**Result:** {'Pass ✅' if wm_r.passed else 'Fail ❌'}\n")
        lines.append("---\n")

    return "\n".join(lines)


def main():
    no_mem, with_mem = run_all()

    # in bảng ngắn ra console
    print(f"{'#':>2} {'Category':18} {'Scenario':45} {'NoMem':>6}  {'WithMem':>7}")
    print("-" * 85)
    for nom_r, wm_r in zip(no_mem, with_mem):
        c = nom_r.conv
        print(f"{c.id:>2} {c.category:18} {c.name[:43]:45} "
              f"{'PASS' if nom_r.passed else 'fail':>6}  "
              f"{'PASS' if wm_r.passed else 'fail':>7}")
    print()
    print(f"Total with-memory: {sum(1 for r in with_mem if r.passed)}/10 passed")
    print(f"Total no-memory:   {sum(1 for r in no_mem if r.passed)}/10 passed")

    md = render_markdown(no_mem, with_mem)
    with open("BENCHMARK.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("\nBENCHMARK.md written.")


if __name__ == "__main__":
    main()
