"""Demo CLI tương tác cho Multi-Memory Agent.

Chạy:
    python3 main.py

Lệnh đặc biệt:
    /profile   xem profile hiện tại
    /episodes  xem episodic log
    /reset     xóa hết memory
    /quit      thoát
"""
from __future__ import annotations
import os

from agent.graph import MemoryAgent

DATA_DIR = "data"


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    agent = MemoryAgent(
        profile_path=os.path.join(DATA_DIR, "profile.json"),
        episodic_path=os.path.join(DATA_DIR, "episodes.jsonl"),
        kb_dir=os.path.join(DATA_DIR, "kb"),
        short_term_window=8,
        memory_budget=300,
    )
    print("Multi-Memory Agent — Lab 17")
    print("Gõ /quit để thoát, /profile, /episodes, /reset để xem/reset state.\n")
    while True:
        try:
            user = input("user> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user == "/quit":
            break
        if user == "/profile":
            print("profile:", agent.profile.all())
            continue
        if user == "/episodes":
            for ep in agent.episodic.all():
                print(" -", ep)
            continue
        if user == "/reset":
            agent.reset()
            print("(reset xong)")
            continue
        out = agent.chat(user)
        print(f"assistant> {out['response']}")
        if out["writes"]:
            print(f"  [writes: {out['writes']}]")


if __name__ == "__main__":
    main()
