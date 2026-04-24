"""Prompt template với 4 section memory rõ ràng + trim theo budget."""
from __future__ import annotations


SYSTEM_HEADER = (
    "Bạn là một trợ lý thân thiện, trả lời bằng tiếng Việt. "
    "Chỉ dùng thông tin trong các section MEMORY dưới đây khi trả lời. "
    "Nếu không có thông tin, nói rõ là chưa biết."
)


def _word_count(text: str) -> int:
    return len(text.split())


def _trim_to_budget(lines: list[str], budget: int) -> list[str]:
    """Cắt bớt dòng cuối (ít ưu tiên nhất trong block) đến khi fit budget."""
    used = sum(_word_count(l) for l in lines)
    while lines and used > budget:
        popped = lines.pop()
        used -= _word_count(popped)
    return lines


def build_prompt(state: dict) -> str:
    """Build prompt có 4 section: Profile, Episodic, Semantic, Recent + User turn.

    Phân bổ budget:  profile 20% - episodic 30% - semantic 30% - recent 20%.
    """
    budget = int(state.get("memory_budget", 400))
    profile_budget = max(20, int(budget * 0.2))
    episodic_budget = max(30, int(budget * 0.3))
    semantic_budget = max(30, int(budget * 0.3))
    recent_budget = max(30, int(budget * 0.2))

    parts: list[str] = [SYSTEM_HEADER, ""]

    # ----- PROFILE -----
    profile = state.get("user_profile") or {}
    parts.append("## USER PROFILE")
    if profile:
        p_lines = [f"- {k}: {v}" for k, v in profile.items()]
        p_lines = _trim_to_budget(p_lines, profile_budget)
        parts.extend(p_lines)
    else:
        parts.append("(trống)")
    parts.append("")

    # ----- EPISODIC -----
    episodes = state.get("episodes") or []
    parts.append("## PAST EPISODES (tình huống liên quan đã xảy ra)")
    if episodes:
        ep_lines = []
        for ep in episodes:
            tags = ",".join(ep.get("tags", []))
            line = f"- [{ep.get('ts','')[:10]}] {ep.get('summary','')}"
            if ep.get("outcome"):
                line += f" → {ep['outcome']}"
            if tags:
                line += f" ({tags})"
            ep_lines.append(line)
        ep_lines = _trim_to_budget(ep_lines, episodic_budget)
        parts.extend(ep_lines)
    else:
        parts.append("(trống)")
    parts.append("")

    # ----- SEMANTIC -----
    hits = state.get("semantic_hits") or []
    parts.append("## RELEVANT KNOWLEDGE (retrieved)")
    if hits:
        sem_lines = []
        for h in hits:
            text = h["text"].replace("\n", " ")
            sem_lines.append(f"- [{h.get('source','kb')}] {text}")
        sem_lines = _trim_to_budget(sem_lines, semantic_budget)
        parts.extend(sem_lines)
    else:
        parts.append("(trống)")
    parts.append("")

    # ----- RECENT CONVERSATION -----
    messages = state.get("messages") or []
    parts.append("## RECENT CONVERSATION")
    if messages:
        rec_lines = [f"{m['role']}: {m['content']}" for m in messages]
        rec_lines = _trim_to_budget(rec_lines, recent_budget)
        parts.extend(rec_lines)
    else:
        parts.append("(trống)")
    parts.append("")

    # ----- CURRENT TURN -----
    parts.append("## CURRENT USER TURN")
    parts.append(f"user: {state.get('user_input','')}")
    parts.append("")
    parts.append("assistant:")

    return "\n".join(parts)


def build_prompt_no_memory(state: dict) -> str:
    """Baseline prompt không inject memory — dùng cho benchmark no-memory."""
    parts = [
        SYSTEM_HEADER,
        "",
        "## CURRENT USER TURN",
        f"user: {state.get('user_input','')}",
        "",
        "assistant:",
    ]
    return "\n".join(parts)
