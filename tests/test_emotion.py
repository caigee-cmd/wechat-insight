import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "emotion.py"


def load_module():
    spec = importlib.util.spec_from_file_location("emotion", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EmotionAnalyzerTests(unittest.TestCase):
    def test_analyze_emotion_builds_distribution_and_daily_rows(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "太棒了，谢谢你",
                "msg_type_label": "text",
                "is_group": False,
            },
            {
                "timestamp": 1776996000,
                "datetime": "2026-04-24 10:00:00",
                "chat_name": "技术群",
                "sender_name": "张三",
                "content": "真离谱，气死我了",
                "msg_type_label": "text",
                "is_group": True,
            },
            {
                "timestamp": 1777075200,
                "datetime": "2026-04-25 08:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "有点焦虑，担心今天赶不上",
                "msg_type_label": "text",
                "is_group": False,
            },
            {
                "timestamp": 1777078800,
                "datetime": "2026-04-25 09:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "谢谢，今天很顺利",
                "msg_type_label": "text",
                "is_group": False,
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260425.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.analyze_emotion(str(input_path))

        self.assertEqual(result["emotion_distribution"]["positive"], 2)
        self.assertEqual(result["emotion_distribution"]["angry"], 1)
        self.assertEqual(result["emotion_distribution"]["anxious"], 1)
        self.assertEqual(result["dominant_emotion"], "positive")
        self.assertEqual(len(result["daily_emotions"]), 2)
        self.assertEqual(result["daily_emotions"][0]["date"], "2026-04-24")
        self.assertIn("persona_modes", result)
        self.assertEqual(result["persona_modes"]["work"]["dominant_emotion"], "positive")
        self.assertIsNone(result["persona_modes"]["life"])
        self.assertIn("情绪周期分析", result["report_markdown"])
        self.assertIn("主导情绪：positive", result["report_markdown"])
        self.assertIn("工作人格", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
