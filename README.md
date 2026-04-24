# Lab #17 — Multi-Memory Agent với LangGraph

Multi-memory agent có đủ 4 loại memory (short-term / long-term profile /
episodic / semantic), chạy qua LangGraph-style state graph (hoặc
skeleton tương đương nếu chưa cài `langgraph`), có benchmark 10
multi-turn conversations so sánh no-memory vs with-memory.

## Cấu trúc

```
.
├── agent/
│   ├── state.py              # MemoryState (TypedDict)
│   ├── graph.py              # Graph: retrieve → prompt → llm → save
│   ├── prompts.py            # Template 4 section + trim theo budget
│   ├── extractor.py          # Rule-based fact extraction
│   ├── llm.py                # Mock LLM (deterministic) + hook OpenAI
│   └── memory/
│       ├── short_term.py     # Sliding-window buffer
│       ├── profile.py        # JSON KV + conflict-aware update
│       ├── episodic.py       # JSONL log + keyword+recency recall
│       └── semantic.py       # TF-IDF retrieval (fallback không cần vector DB)
├── data/
│   └── kb/faq.md             # Knowledge base seed cho semantic
├── tests/test_conflict.py    # Unit test bắt buộc (rubric mục 3)
├── benchmark.py              # Chạy 10 conversations → BENCHMARK.md
├── BENCHMARK.md              # Kết quả no-memory vs with-memory
├── REFLECTION.md             # Privacy + limitations
├── main.py                   # Demo CLI tương tác
└── requirements.txt          # Mọi deps đều optional
```

## Chạy

```bash
# unit test (conflict handling + recall)
python3 -m unittest tests.test_conflict -v

# benchmark 10 conversations → sinh BENCHMARK.md
python3 benchmark.py

# demo CLI
python3 main.py
```
## Mapping rubric → file

| Rubric | File / Artifact | Ghi chú |
|---|---|---|
| 1. Full memory stack (4 types) — 25đ | [agent/memory/](agent/memory/) | `short_term.py`, `profile.py`, `episodic.py`, `semantic.py` — 4 interfaces riêng biệt, không blob |
| 2. LangGraph state/router + prompt injection — 30đ | [agent/state.py](agent/state.py), [agent/graph.py](agent/graph.py), [agent/prompts.py](agent/prompts.py) | `MemoryState`, 4 node pipeline, prompt có 4 section rõ, có trim theo `memory_budget` |
| 3. Save/update + conflict handling — 15đ | [agent/extractor.py](agent/extractor.py), [agent/memory/profile.py](agent/memory/profile.py), [tests/test_conflict.py](tests/test_conflict.py) | Extract ≥2 profile facts, ghi episodic khi task done, `ProfileMemory.set()` latest-write-wins, test bắt buộc pass |
| 4. Benchmark 10 multi-turn — 20đ | [benchmark.py](benchmark.py), [BENCHMARK.md](BENCHMARK.md) | 10 conv, phủ 5 nhóm (profile / conflict / episodic / semantic / budget), no-mem vs with-mem, token ước lượng bằng word count |
| 5. Reflection privacy/limitations — 10đ | [REFLECTION.md](REFLECTION.md) | 4 câu gợi ý + bảng limitation + privacy-by-design |

## Design choices đáng lưu ý

**Mock LLM deterministic.** Không có API key trong môi trường chấm,
mình viết mock LLM chỉ dùng thông tin có trong prompt. Điều này giúp
benchmark **tái lập được** và **tách riêng** được đóng góp của memory
(câu trả lời thay đổi ⇔ prompt thay đổi ⇔ memory thật sự được inject).
Hook OpenAI có sẵn, chỉ cần set `OPENAI_API_KEY` để chạy LLM thật.

**LangGraph skeleton.** Rubric cho phép skeleton. `MemoryAgent._compile()`
thử `from langgraph.graph import StateGraph`; có thì compile graph
thật, không có thì fallback sequential pipeline cùng 4 node. Node
signatures giống nhau → đổi backend là no-op.

**Semantic fallback TF-IDF.** Rubric cho phép keyword search. Mình
tự implement TF-IDF bằng stdlib (collections.Counter + math.log) để
không phụ thuộc external service. Có hook `add(doc_id, text)` để ingest
thêm runtime, và swap sang Chroma/FAISS là việc thay đổi nội dung
class `SemanticMemory` chứ không đụng vào graph.

**Conflict handling bằng latest-write-wins + history.** Khi user sửa
fact cũ (có hoặc không có prefix "à nhầm/thực ra"), `ProfileMemory.set()`
luôn ghi đè và đẩy giá trị cũ vào `history` thay vì append. Điều này
đảm bảo prompt chỉ thấy giá trị mới nhất, không bao giờ thấy cả hai
giá trị mâu thuẫn.

## Kết quả benchmark (tóm tắt)

- **10/10** pass với with-memory.
- **0/10** pass với no-memory (baseline).
- Coverage đầy đủ 5 nhóm test: profile_recall (2), conflict_update (2),
  episodic_recall (2), semantic_retrieval (3), budget_trim (1).

Xem chi tiết transcript ở [BENCHMARK.md](BENCHMARK.md).
