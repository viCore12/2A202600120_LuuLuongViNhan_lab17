"""LLM interface + mock LLM deterministic cho benchmark.

Interface `call_llm(prompt)` → str. Nếu cài openai và có OPENAI_API_KEY
thì dùng LLM thật (để dành chỗ cắm). Mặc định chạy mock để benchmark
tái lập được.

Mock LLM thiết kế theo nguyên tắc:
- CHỈ dùng thông tin xuất hiện trong prompt.
- Nếu prompt không chứa answer → trả "Tôi chưa có thông tin này."
- Nếu có → trích lại fact tương ứng.

Điều này phản ánh đúng behavior mong đợi: khi memory được inject vào
prompt thì LLM trả lời đúng; khi không inject thì LLM nói không biết.
"""
from __future__ import annotations
import os
import re

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass

try:
    import tiktoken  # type: ignore
    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODING = None


# các mẫu câu hỏi và key profile/tag tương ứng (chỉ match khi là câu hỏi)
QUESTION_PATTERNS = [
    (re.compile(r"(?:tên|gọi) tôi (?:là )?gì|tôi tên (?:là )?gì", re.I), "name"),
    (re.compile(r"tôi (?:bị )?dị ứng (?:với )?(?:gì|cái gì)", re.I), "allergy"),
    (re.compile(r"tôi (?:thích|yêu thích) (?:món )?ăn gì", re.I), "favorite_food"),
    (re.compile(r"tôi sống ở đâu|tôi ở (?:thành phố )?(?:nào|đâu)", re.I), "city"),
    (re.compile(r"công ty (?:tôi|của tôi) (?:tên )?(?:là )?gì|tôi làm (?:ở|tại) (?:công ty )?nào", re.I), "company"),
    (re.compile(r"mục tiêu (?:của )?tôi (?:là )?gì", re.I), "goal"),
    (re.compile(r"ngôn ngữ (?:lập trình )?tôi (?:thích|dùng) (?:là )?gì", re.I), "lang_pref"),
    (re.compile(r"tên con (?:tôi|của tôi) (?:là )?gì", re.I), "child_name"),
    (re.compile(r"tôi (?:năm nay )?bao nhiêu tuổi|tôi tuổi (?:bao nhiêu|mấy)", re.I), "age"),
]

# semantic question → keyword bên trong prompt
SEMANTIC_PATTERNS = [
    (re.compile(r"docker|container", re.I), ["docker", "service name", "hostname"]),
    (re.compile(r"hoàn tiền|refund", re.I), ["hoàn tiền", "14 ngày"]),
    (re.compile(r"giờ (làm việc|hỗ trợ)|support hour", re.I), ["8:00", "hỗ trợ"]),
    (re.compile(r"reset mật khẩu|quên mật khẩu", re.I), ["reset", "30 phút"]),
    (re.compile(r"deploy.*(python|production)|gunicorn|uvicorn", re.I), ["gunicorn", "uvicorn", "debug"]),
    (re.compile(r"PII|bảo mật|mã hóa|privacy", re.I), ["AES-256", "PII", "2 năm"]),
]

# trigger cho câu hỏi có tính episodic (tham chiếu quá khứ)
EPISODIC_TRIGGER = re.compile(
    r"lần trước|trước đây|từng|hôm qua|ngày trước|lần nào|đã.*?chưa",
    re.I | re.U,
)


def _find_profile_in_prompt(prompt: str, key: str) -> str | None:
    """Tìm 'key: value' trong section USER PROFILE của prompt."""
    m = re.search(r"## USER PROFILE\n(.*?)\n\n", prompt, re.S)
    if not m:
        return None
    block = m.group(1)
    for line in block.splitlines():
        line = line.strip("- ").strip()
        if line.lower().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


def _find_semantic_lines(prompt: str, keywords: list[str]) -> list[str]:
    """Quét section KNOWLEDGE, lấy các dòng chứa keyword."""
    m = re.search(r"## RELEVANT KNOWLEDGE.*?\n(.*?)\n\n", prompt, re.S)
    if not m:
        return []
    block = m.group(1)
    out = []
    for line in block.splitlines():
        if any(kw.lower() in line.lower() for kw in keywords):
            out.append(line.strip("- ").strip())
    return out


def _find_all_episodic_lines(prompt: str) -> list[str]:
    m = re.search(r"## PAST EPISODES.*?\n(.*?)\n\n", prompt, re.S)
    if not m:
        return []
    block = m.group(1)
    out = []
    for line in block.splitlines():
        line = line.strip("- ").strip()
        if line and line != "(trống)":
            out.append(line)
    return out


def _last_user_turn(prompt: str) -> str:
    m = re.search(r"## CURRENT USER TURN\nuser: (.*?)\n", prompt, re.S)
    return m.group(1).strip() if m else ""


def mock_llm(prompt: str) -> str:
    """Trả lời dựa trên memory inject vào prompt."""
    q = _last_user_turn(prompt)
    q_lower = q.lower()

    # 1. profile-recall
    for pattern, key in QUESTION_PATTERNS:
        if pattern.search(q):
            value = _find_profile_in_prompt(prompt, key)
            if value:
                return f"Bạn là {value}." if key == "name" else f"{_nice_label(key)}: {value}."
            else:
                return "Tôi chưa có thông tin này trong trí nhớ."

    # 2. episodic-recall — nếu user tham chiếu quá khứ, đọc top của
    # section PAST EPISODES (đã được retrieve_memory sắp xếp theo
    # overlap + recency).
    if EPISODIC_TRIGGER.search(q):
        lines = _find_all_episodic_lines(prompt)
        if lines:
            return "Theo ghi chú trước đây: " + " | ".join(lines[:2])
        return "Tôi không nhớ tình huống tương tự trước đây."

    # 3. semantic-retrieval
    for pattern, kws in SEMANTIC_PATTERNS:
        if pattern.search(q):
            lines = _find_semantic_lines(prompt, kws)
            if lines:
                return lines[0]
            return "Tôi chưa có tài liệu liên quan để trả lời câu này."

    # 4. mặc định — echo một câu xác nhận (cho turn khai báo fact)
    if re.search(r"tên tôi là|tôi tên|tôi là ", q_lower):
        return "Rất vui được biết bạn!"
    if re.search(r"dị ứng", q_lower):
        return "Tôi đã ghi nhận thông tin dị ứng của bạn."
    if re.search(r"tôi thích|tôi yêu thích", q_lower):
        return "Đã ghi nhớ sở thích của bạn."
    return "Bạn muốn tôi giúp gì thêm?"


def _nice_label(key: str) -> str:
    return {
        "name": "Tên bạn",
        "allergy": "Bạn bị dị ứng",
        "favorite_food": "Món ăn bạn thích",
        "city": "Bạn sống ở",
        "company": "Công ty bạn",
        "goal": "Mục tiêu của bạn",
        "lang_pref": "Ngôn ngữ bạn thích",
        "child_name": "Tên con bạn",
        "age": "Tuổi bạn",
    }.get(key, key)


def call_llm(prompt: str) -> str:
    """Entry point. Dùng OpenAI nếu có key, fallback mock."""
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI()
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM error, fallback mock] {mock_llm(prompt)}  ({e})"
    return mock_llm(prompt)


def approx_tokens(text: str) -> int:
    """Đếm token — ưu tiên tiktoken (cl100k_base, đúng với GPT-4o),
    fallback word count (rubric cho phép)."""
    if _ENCODING is not None:
        try:
            return len(_ENCODING.encode(text))
        except Exception:
            pass
    return len(text.split())
