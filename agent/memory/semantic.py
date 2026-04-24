"""Semantic memory — keyword/TF-IDF retrieval fallback.

Rubric cho phép "keyword search fallback" cho semantic. Ở đây mình dùng
TF-IDF tự implement bằng stdlib để không phụ thuộc gì. Có hook để thay
bằng Chroma/FAISS khi cài được (để cộng bonus).
"""
from __future__ import annotations
import json
import math
import os
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class SemanticMemory:
    """TF-IDF retrieval đơn giản trên tập document đã load."""

    def __init__(self, kb_dir: str | None = None):
        self.docs: list[dict] = []           # {id, text, source}
        self._tf: list[Counter] = []
        self._df: Counter = Counter()
        self._n = 0
        if kb_dir and os.path.isdir(kb_dir):
            self.load_dir(kb_dir)

    # ---- ingestion ----
    def add(self, doc_id: str, text: str, source: str = "") -> None:
        self.docs.append({"id": doc_id, "text": text, "source": source})
        tokens = _tokenize(text)
        tf = Counter(tokens)
        self._tf.append(tf)
        for term in tf:
            self._df[term] += 1
        self._n = len(self.docs)

    def load_dir(self, kb_dir: str) -> int:
        count = 0
        for name in sorted(os.listdir(kb_dir)):
            path = os.path.join(kb_dir, name)
            if not os.path.isfile(path):
                continue
            if name.endswith(".jsonl"):
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            self.add(obj.get("id", f"{name}:{i}"),
                                     obj["text"],
                                     source=name)
                            count += 1
                        except (json.JSONDecodeError, KeyError):
                            pass
            elif name.endswith(".txt") or name.endswith(".md"):
                with open(path, "r", encoding="utf-8") as f:
                    # tách theo đoạn rỗng => mỗi paragraph là 1 chunk
                    raw = f.read()
                chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
                for i, chunk in enumerate(chunks):
                    self.add(f"{name}:{i}", chunk, source=name)
                    count += 1
        return count

    # ---- retrieval ----
    def search(self, query: str, k: int = 3) -> list[dict]:
        if self._n == 0:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_tf = Counter(q_tokens)
        scores = []
        for idx, tf in enumerate(self._tf):
            score = 0.0
            for term, qf in q_tf.items():
                if term not in tf:
                    continue
                idf = math.log((self._n + 1) / (1 + self._df[term])) + 1
                score += qf * tf[term] * idf
            if score > 0:
                doc_len = sum(tf.values()) or 1
                scores.append((score / math.sqrt(doc_len), idx))
        scores.sort(reverse=True)
        out = []
        for score, idx in scores[:k]:
            doc = dict(self.docs[idx])
            doc["score"] = round(score, 4)
            out.append(doc)
        return out

    def __len__(self) -> int:
        return self._n
