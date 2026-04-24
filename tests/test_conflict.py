"""Test bắt buộc của rubric (mục 3): allergy sữa bò → đậu nành."""
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.graph import MemoryAgent  # noqa: E402


class TestConflictHandling(unittest.TestCase):
    TMP = ".tmp_test"

    def setUp(self):
        shutil.rmtree(self.TMP, ignore_errors=True)
        os.makedirs(self.TMP, exist_ok=True)
        self.agent = MemoryAgent(
            profile_path=os.path.join(self.TMP, "profile.json"),
            episodic_path=os.path.join(self.TMP, "episodes.jsonl"),
            kb_dir="data/kb",
        )

    def tearDown(self):
        shutil.rmtree(self.TMP, ignore_errors=True)

    def test_allergy_conflict(self):
        """Rubric: fact mới phải ghi đè fact cũ, không append mâu thuẫn."""
        self.agent.chat("Tôi dị ứng sữa bò.")
        self.assertEqual(self.agent.profile.get("allergy"), "sữa bò")

        self.agent.chat("À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")
        self.assertEqual(self.agent.profile.get("allergy"), "đậu nành")

        # history phải giữ lại giá trị cũ để audit
        raw = self.agent.profile.raw()["allergy"]
        old_values = [h["value"] for h in raw["history"]]
        self.assertIn("sữa bò", old_values)
        self.assertEqual(raw["source"], "user_correction")

    def test_two_profile_facts(self):
        """Rubric mục 3: update ít nhất 2 profile facts."""
        self.agent.chat("Tên tôi là Linh.")
        self.agent.chat("Tôi dị ứng đậu nành.")
        profile = self.agent.profile.all()
        self.assertEqual(profile.get("name"), "Linh")
        self.assertEqual(profile.get("allergy"), "đậu nành")

    def test_recall_uses_memory(self):
        """Prompt injection phải thực sự dùng được (với-memory ≠ no-memory)."""
        self.agent.chat("Tên tôi là Minh.")
        with_mem = self.agent.chat("Tên tôi là gì?")["response"]
        no_mem = self.agent.chat_no_memory("Tên tôi là gì?")["response"]
        self.assertIn("Minh", with_mem)
        self.assertNotIn("Minh", no_mem)


if __name__ == "__main__":
    unittest.main()
