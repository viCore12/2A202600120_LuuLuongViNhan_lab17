# Báo cáo cá nhân — Lab #17
**Bài:** Build Multi-Memory Agent với LangGraph
**Tên học viên:** Lưu Lương Vi Nhân 
**Mã học viên:** 2A202600120
**Ngày:** 2026-04-24
**LLM:** OpenAI `gpt-4o-mini` (qua Anthropic SDK-style client) · **Graph:** LangGraph thật (`StateGraph`) · **Token counter:** `tiktoken` (`cl100k_base`)

---

## 1. Tổng quan bài làm

Agent được xây dựng thành một pipeline **LangGraph thật** gồm 4 node (`retrieve_memory → build_prompt → call_llm → save_memory`). Toàn bộ 4 loại memory được tách thành 4 class riêng biệt trong `agent/memory/`, không gộp thành blob. Với LLM thật `gpt-4o-mini`, **10/10** conversations ở chế độ with-memory đạt PASS, **0/10** ở no-memory — đủ phân biệt rõ đóng góp của memory stack.

### Cấu trúc repo sau khi hoàn tất

```
agent/
  state.py              # MemoryState (TypedDict) — schema cho LangGraph
  graph.py              # 4 node, compile StateGraph hoặc fallback pipeline
  prompts.py            # Template 4 section + trim theo memory_budget
  extractor.py          # Rule-based extractor (VN) + correction detection
  llm.py                # OpenAI gpt-4o-mini, tiktoken counting, mock fallback
  memory/
    short_term.py       # sliding-window deque
    profile.py          # JSON KV, conflict-aware set() với history
    episodic.py         # JSONL log, recall keyword + recency
    semantic.py         # TF-IDF trên data/kb (fallback keyword)
data/kb/faq.md          # 6 đoạn FAQ làm seed cho semantic retrieval
tests/test_conflict.py  # 3 unit test, tất cả pass
benchmark.py            # runner 10 conversations
BENCHMARK.md            # bảng + transcript chi tiết
REFLECTION.md           # privacy + limitations chi tiết
main.py                 # demo CLI tương tác
```

---

## 2. Các bước đã làm (mapping theo thứ tự plan)

### Bước 1 — Full memory stack (rubric mục 1, 25 điểm)

Bốn backend được implement riêng biệt, mỗi cái có interface rõ:

| Memory type | File | Backend | Interface chính |
|---|---|---|---|
| Short-term | `agent/memory/short_term.py` | `collections.deque(maxlen=window)` | `add(role, content)`, `recent(n)` |
| Long-term profile | `agent/memory/profile.py` | JSON KV với history per key | `set(key, value, source)`, `get(key)`, `delete(key)` |
| Episodic | `agent/memory/episodic.py` | JSONL append-only | `add(summary, outcome, tags)`, `recall(query, k)` |
| Semantic | `agent/memory/semantic.py` | TF-IDF tự implement | `load_dir(kb)`, `search(query, k)` |

### Bước 2 — LangGraph state/router + prompt injection (rubric mục 2, 30 điểm)

- `MemoryState` (TypedDict) có đủ các field rubric gợi ý:
  `messages, user_profile, episodes, semantic_hits, memory_budget`.
- Dùng `StateGraph(MemoryState)` thật — không phải skeleton.
  `MemoryAgent._compile()` kiểm tra import `langgraph.graph` và
  compile `StateGraph` với 4 node + entry/end. Fallback pipeline
  pure-Python chỉ kích hoạt nếu LangGraph chưa cài.
- Prompt có **4 section rõ ràng** (xem `agent/prompts.py`):
  `## USER PROFILE / ## PAST EPISODES / ## RELEVANT KNOWLEDGE / ## RECENT CONVERSATION`
  rồi tới `## CURRENT USER TURN`.
- Có **trim theo token budget** — budget được phân bổ 20/30/30/20 cho
  4 section, dòng dư bị pop ra cuối để không vượt.

### Bước 3 — Save/update + conflict handling (rubric mục 3, 15 điểm)

- `agent/extractor.py` nhận diện 9 loại profile fact (name, allergy,
  favorite_food, city, company, goal, lang_pref, child_name, age)
  bằng regex tiếng Việt, + phát hiện câu đính chính qua prefix
  ("à nhầm", "thực ra", "không phải", "thay vì", "đính chính", "sorry").
- **Conflict handling** trong `ProfileMemory.set()`: luôn ghi đè
  (latest-write-wins) và đẩy giá trị cũ vào `history` với timestamp
  + source. LLM chỉ thấy giá trị mới nhất → không bao giờ thấy cả
  hai giá trị mâu thuẫn.
- **Episodic save** có điều kiện: chỉ ghi khi detect được task-done
  pattern ("đã fix/sửa/xong", "cảm ơn đã giúp", "bug do...") —
  không append bừa.
- **Test bắt buộc của rubric đã pass:**

```
User: Tôi dị ứng sữa bò.                            → profile.allergy = "sữa bò"
User: À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
                                                     → profile.allergy = "đậu nành"
User: Tôi bị dị ứng gì?                             → "Bạn bị dị ứng đậu nành." ✅
```

### Bước 4 — Benchmark 10 conversations (rubric mục 4, 20 điểm)

Xem chi tiết ở [BENCHMARK.md](BENCHMARK.md). Tóm tắt:

| Nhóm test (rubric yêu cầu) | # conv | Pass |
|---|---:|---:|
| profile_recall | 2 | 2/2 |
| conflict_update | 2 | 2/2 |
| episodic_recall | 2 | 2/2 |
| semantic_retrieval | 3 | 3/3 |
| budget_trim | 1 | 1/1 |
| **Tổng** | **10** | **10/10** |

### Bước 5 — Reflection privacy/limitations (rubric mục 5, 10 điểm)

Xem [REFLECTION.md](REFLECTION.md). Trả lời đủ 4 câu gợi ý +
bảng 7 limitations kỹ thuật + checklist privacy-by-design.

---

## 3. Kết quả benchmark với `gpt-4o-mini`

### 3.1 Bảng kết quả đầy đủ

| # | Category | Scenario | No-memory | With-memory | Pass |
|---|---|---|---|---|:-:|
| 1 | profile_recall | Recall user name after 6 turns | Xin lỗi, tôi chưa biết tên của bạn. | Tên bạn là Linh. | ✅ |
| 2 | conflict_update | Allergy conflict | Xin lỗi, tôi không có thông tin về tình trạng dị ứng… | Bạn bị dị ứng đậu nành. | ✅ |
| 3 | episodic_recall | Recall docker debug lesson | Xin lỗi, mình chưa biết về lỗi container… | Lần trước, bạn đã fix bug docker networking bằng service name. | ✅ |
| 4 | semantic_retrieval | FAQ hoàn tiền | Xin lỗi, mình chưa biết chính sách hoàn tiền… | Chính sách hoàn tiền quy định… 14 ngày… | ✅ |
| 5 | budget_trim | 8 turn còn recall name | Xin lỗi, tôi chưa biết tên của bạn. | Tên bạn là Minh. | ✅ |
| 6 | profile_recall | Recall favorite food | Chưa biết món ăn bạn thích… | Bạn thích ăn mì Quảng! | ✅ |
| 7 | conflict_update | Location Hà Nội → Sài Gòn | Xin lỗi, tôi chưa biết bạn sống ở đâu. | Bạn sống ở Sài Gòn. | ✅ |
| 8 | semantic_retrieval | FAQ reset mật khẩu | Chưa biết. | Link reset mật khẩu có hiệu lực trong 30 phút. | ✅ |
| 9 | semantic_retrieval | FAQ PII bảo mật | Xin lỗi, chưa biết chính sách bảo mật… | Dữ liệu cá nhân được mã hóa AES-256… | ✅ |
| 10 | episodic_recall | Recall JWT fix sau 5 turn | Xin lỗi, mình chưa biết bạn đã xử lý bug auth gì… | Lần trước, bạn đã sửa bug auth bằng cách đổi JWT secret. | ✅ |

**Tổng: no-memory 0/10 — with-memory 10/10.**

### 3.2 Token usage (đo bằng `tiktoken`, `cl100k_base`)

| Metric | no-memory | with-memory | Chênh |
|---|---:|---:|---:|
| Prompt tokens / conv — min | 51 | 133 | +82 |
| Prompt tokens / conv — max | 424 | 1226 | +802 |
| Prompt tokens / conv — mean | 181 | 553 | +372 |

With-memory tốn thêm ~3x token so với baseline, nhưng đổi lại toàn bộ
10 assertion pass — tỉ lệ ROI rất tốt. Conversation tốn token nhất là
#5 (budget-trim, 8 turn) và #1 (profile-recall, 7 turn) — do prompt
chứa đầy đủ 4 section memory + recent buffer ngày càng dài.

### 3.3 Writes per conversation

Các conversation có write cao nhất (ghi nhiều fact vào memory):
- #1 (4 writes): tên, city, company, lang_pref
- #10 (3 writes): tên, food, + episodic
- #2, #6, #7 (2 writes): profile + correction

Conversation không write (#4, #8, #9) là các truy vấn thuần semantic
— chỉ đọc KB, đúng hành vi mong đợi.

---

## 4. Những điểm khó / quyết định kỹ thuật đáng ghi

### 4.1 LangGraph + TypedDict schema

Khi thử chạy với `StateGraph(dict)` ban đầu, `retrieve_memory` báo `KeyError: 'user_input'` — LangGraph không auto-merge state khi schema là plain `dict`. Fix bằng cách đổi sang `StateGraph(MemoryState)` với `MemoryState` là `TypedDict`. Bài học: LangGraph cần schema rõ ràng để quản lý state giữa các node, không dùng dict trần được.

### 4.2 Extractor — bẫy câu hỏi và filler word

Ban đầu gặp hai bug:
1. `Tôi bị dị ứng gì?` bị extract thành `allergy = "gì"` vì regex match cả câu hỏi. Fix: skip extract nếu input chứa `?` hoặc kết thúc bằng từ để hỏi ("gì", "nào", "đâu", "mấy").
2. `"mới chuyển vào Sài Gòn rồi."` bị extract thành `city = "Sài Gòn rồi"`. Fix: thêm bước strip các filler tiếng Việt ở cuối ("rồi", "ạ", "nhé", "thôi", "luôn", "vậy", "mà", "đó").

Sau 2 fix này, benchmark từ 8/10 lên **10/10**.

### 4.3 Câu đính chính — ưu tiên fact mới

Rubric yêu cầu không append bừa khi có conflict. Decision: luôn ghi đè bằng `ProfileMemory.set()`, đồng thời push giá trị cũ vào `history` (để audit). Prefix `"à nhầm / thực ra / không phải / thay vì"` chỉ dùng để đánh dấu `source = "user_correction"` cho log, không đổi logic merge.

Hệ quả: prompt chỉ hiện 1 giá trị mới nhất → `gpt-4o-mini` không bao giờ bị confuse. Test case conflict đạt PASS một cách nhất quán.

### 4.4 Semantic fallback TF-IDF

KB 6 chunk đủ nhỏ, không cần Chroma. Mình tự implement TF-IDF bằng stdlib (collections.Counter + math.log) — chạy ổn cho benchmark, đồng thời giữ khả năng thay bằng Chroma là việc đổi class `SemanticMemory` chứ không đụng graph (bonus +2 nếu có thời gian). Rubric rõ ràng "keyword search fallback" được chấp nhận cho full điểm mục 1.

### 4.5 Tiktoken cho token count thật

Thay `len(text.split())` bằng `tiktoken.get_encoding("cl100k_base")` (encoding của GPT-4o family). Số liệu token trong BENCHMARK.md và báo cáo này đều là token thật, không phải ước lượng word count — bonus item #4 của rubric.

---

## 5. Tự đánh giá theo rubric

| Hạng mục | Tối đa | Dự kiến đạt | Lý do |
|---|---:|---:|---|
| 1. Full memory stack | 25 | 25 | 4 backends riêng biệt, interface rõ (deque / JSON KV / JSONL / TF-IDF) |
| 2. LangGraph state/router + prompt injection | 30 | 28-30 | LangGraph thật compile OK, 4 section prompt rõ, có trim budget, test `test_recall_uses_memory` verify inject thực sự hoạt động |
| 3. Save/update + conflict handling | 15 | 14-15 | Update 2+ facts, episodic có outcome, test bắt buộc pass, có history audit |
| 4. Benchmark 10 conv | 20 | 19-20 | Phủ đủ 5 nhóm, 10/10 pass, transcript chi tiết, token đo bằng tiktoken |
| 5. Reflection | 10 | 9-10 | Đủ 4 câu + bảng 7 limitations + privacy-by-design checklist |
| **Core** | **100** | **95-100** | |
| Bonus: LangGraph thật chạy ổn + graph demo rõ | +2 | +2 | Dùng `StateGraph` thật, đã verify qua `hasattr(a, '_langgraph_compiled')` |
| Bonus: Token counting tốt hơn word count | +2 | +2 | Dùng `tiktoken cl100k_base` |
| Bonus: LLM-based extraction có error handling | +2 | 0 | Hiện tại chỉ rule-based, có hook LLM nhưng chưa bật cho extractor |
| Bonus: Chroma/FAISS thật chạy ổn | +2 | 0 | Chưa bật, vẫn dùng TF-IDF (rubric cho phép) |
| Bonus: Redis thật chạy ổn | +2 | 0 | Chưa bật, dùng JSON file |

---

## 6. Hướng cải thiện nếu có thêm thời gian

1. **Chroma cho semantic.** Class `SemanticMemory` đã được thiết kế sao cho việc swap là local — chỉ cần reimplement `add()` và `search()` dùng `chromadb.Client()` với embedding function. KB hiện tại 6 chunk sẽ lên được ~1000 chunk mà vẫn query <100ms.
2. **LLM-based extractor.** Thay regex tiếng Việt bằng function-calling tới gpt-4o-mini với JSON schema rõ. Xử lý typo, code-switching, câu phức tốt hơn.
3. **`user_id` namespace.** Multi-user hóa bằng cách prefix tất cả key của 4 backend theo `user_id`. Điều này cũng mở đường cho cross-session recall.
4. **Consent ledger + TTL automation.** Thêm field `consent_given` / `expires_at` vào profile entry, background job dọn dẹp.

---

## 7. Cách chấm lại (tái lập)

```bash
cd 2A202600120_LuuLuongViNhan_lab17
source .venv/bin/activate
export OPENAI_MODEL=gpt-4o-mini

# Test bắt buộc của rubric
python -m unittest tests.test_conflict -v
# Expect: Ran 3 tests, OK

# Benchmark đầy đủ — regen BENCHMARK.md
python benchmark.py
# Expect: Total with-memory: 10/10 passed, no-memory: 0/10 passed

# Demo tương tác
python main.py
```
