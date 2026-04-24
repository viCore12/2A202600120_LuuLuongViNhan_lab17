"""Long-term profile memory — KV store với conflict-aware update.

Backend: JSON file (dễ soi/debug, đủ cho lab). Mỗi key lưu kèm lịch sử
giá trị cũ để phục vụ reflection/audit.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Any


class ProfileMemory:
    def __init__(self, path: str):
        self.path = path
        self._data: dict[str, dict] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = {}
        else:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self._flush()

    # ---- core API ----
    def set(self, key: str, value: Any, source: str = "user") -> dict:
        """Ghi đè fact — nếu đã tồn tại, giá trị cũ được đẩy vào history.

        Đây chính là điểm xử lý conflict: luôn ưu tiên giá trị mới nhất
        (latest-write-wins), không append bừa.
        """
        now = datetime.now(timezone.utc).isoformat()
        prev = self._data.get(key)
        history = []
        if prev is not None:
            history = prev.get("history", [])
            history.append({
                "value": prev["value"],
                "updated_at": prev["updated_at"],
                "source": prev.get("source", "unknown"),
            })
        entry = {
            "value": value,
            "updated_at": now,
            "source": source,
            "history": history,
        }
        self._data[key] = entry
        self._flush()
        return entry

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._data.get(key)
        return entry["value"] if entry else default

    def delete(self, key: str) -> bool:
        """Hỗ trợ GDPR-style deletion — xóa hẳn cả history."""
        if key in self._data:
            del self._data[key]
            self._flush()
            return True
        return False

    def all(self) -> dict[str, Any]:
        return {k: v["value"] for k, v in self._data.items()}

    def raw(self) -> dict[str, dict]:
        return dict(self._data)

    def clear(self) -> None:
        self._data = {}
        self._flush()

    def _flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
