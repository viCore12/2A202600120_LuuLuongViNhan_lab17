"""Rule-based fact extractor.

Trích profile facts và episodic summaries từ user turn.
Trả về list of "writes" để node save_memory xử lý.

Mỗi write có dạng:
    {"target": "profile"|"episodic", ...}

Profile write xử lý conflict bằng cách ghi đè (latest-write-wins).
Nếu user "đính chính" (à nhầm / không phải / thực ra), vẫn dùng cùng
cơ chế set() — giá trị cũ tự bị đẩy vào history.
"""
from __future__ import annotations
import re


# mẫu: key, regex, group lấy value
PROFILE_RULES = [
    ("name",          re.compile(r"(?:tên (?:tôi|của tôi) là|tôi tên (?:là )?|tôi là) ([A-ZÀ-Ỹ][\wÀ-ỹ]*(?:\s[A-ZÀ-Ỹ][\wÀ-ỹ]*){0,3})", re.U)),
    ("allergy",       re.compile(r"(?:tôi )?(?:bị )?dị ứng (?:với )?(?:là )?([\wÀ-ỹ][\wÀ-ỹ\s]*?)(?:[\.,!\?]|$)", re.U | re.I)),
    ("favorite_food", re.compile(r"tôi (?:thích|yêu thích) ăn ([\wÀ-ỹ][\wÀ-ỹ\s]*?)(?:[\.,!\?]|$)", re.U | re.I)),
    ("city",          re.compile(r"(?:tôi (?:đang )?sống (?:ở|tại)|(?:mới )?chuyển (?:vào|đến|tới|ra)|dọn (?:đến|tới|vào)) ([\wÀ-ỹ][\wÀ-ỹ\s]*?)(?:[\.,!\?]|$)", re.U | re.I)),
    ("company",       re.compile(r"tôi (?:đang )?làm (?:việc )?(?:ở|tại) (?:công ty )?([\wÀ-ỹ][\wÀ-ỹ\s]*?)(?:[\.,!\?]|$)", re.U | re.I)),
    ("goal",          re.compile(r"(?:mục tiêu (?:của )?tôi là|tôi muốn) ([\wÀ-ỹ][\wÀ-ỹ\s]*?)(?:[\.,!\?]|$)", re.U | re.I)),
    ("lang_pref",     re.compile(r"tôi thích (?:lập trình )?(?:bằng|dùng) ([\wÀ-ỹ\+\#]+)", re.U | re.I)),
    ("child_name",    re.compile(r"con (?:tôi|của tôi) tên (?:là )?([A-ZÀ-Ỹ][\wÀ-ỹ]*)", re.U)),
    ("age",           re.compile(r"tôi (?:năm nay )?(\d{1,3}) tuổi", re.U | re.I)),
]

# đính chính: "à nhầm", "thực ra", "không phải ... mà là ..."
CORRECTION_PREFIX = re.compile(
    r"(?:à nhầm|thực ra|thật ra|xin lỗi|sorry|đính chính|không phải|thay vì)",
    re.I | re.U,
)

# tín hiệu kết thúc task → episodic
TASK_DONE_PATTERNS = [
    (re.compile(r"(?:đã|mình đã) (?:fix|sửa|giải quyết|xong|hoàn thành) (.*?)[\.!\?]", re.I | re.U),
     "task_completed"),
    (re.compile(r"(?:cảm ơn|thanks).*?(?:giúp|giải quyết) (.*?)[\.!\?]", re.I | re.U),
     "thanked_help"),
    (re.compile(r"bug (?:hôm nay|lần này) (?:do|là do) (.*?)[\.!\?]", re.I | re.U),
     "bug_rootcause"),
]


_FILLERS = {"rồi", "ạ", "nhé", "nhe", "thôi", "mà", "đó", "luôn", "vậy"}


def _clean(s: str) -> str:
    s = s.strip().strip(",.!?").strip()
    # strip trailing Vietnamese filler words
    parts = s.split()
    while parts and parts[-1].lower() in _FILLERS:
        parts.pop()
    return " ".join(parts)


def extract(user_input: str) -> list[dict]:
    """Trả về list writes: [{target, key, value, source}] hoặc
    [{target:'episodic', summary, outcome, tags}]."""
    writes: list[dict] = []
    text = user_input.strip()

    # câu hỏi → không extract (tránh bắt nhầm "dị ứng gì?")
    is_question = "?" in text or any(
        text.lower().endswith(q) for q in ["gì", "nào", "đâu", "mấy"]
    )

    # profile facts
    for key, rule in PROFILE_RULES:
        if is_question:
            break
        m = rule.search(text)
        if not m:
            continue
        value = _clean(m.group(1))
        # cắt tại dấu hiệu đính chính/phủ định ở giữa câu:
        # "đậu nành chứ không phải sữa bò" → "đậu nành"
        for stopword in [" chứ ", " không phải ", " thay vì ", " mà "]:
            if stopword in value.lower():
                idx = value.lower().index(stopword)
                value = value[:idx].strip()
                break
        value = _clean(value)
        if not value or value.lower() in {"gì", "nào", "đâu"}:
            continue
        # nếu là câu đính chính thì đánh dấu source
        is_correction = bool(CORRECTION_PREFIX.search(text))
        writes.append({
            "target": "profile",
            "key": key,
            "value": value,
            "source": "user_correction" if is_correction else "user_stated",
        })

    # episodic — chỉ ghi khi có tín hiệu hoàn tất task rõ ràng
    for rule, tag in TASK_DONE_PATTERNS:
        m = rule.search(text)
        if m:
            writes.append({
                "target": "episodic",
                "summary": _clean(m.group(0)),
                "outcome": _clean(m.group(1) if m.groups() else ""),
                "tags": [tag],
            })
            break

    return writes
