import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "speech_patterns.py"


def load_module():
    spec = importlib.util.spec_from_file_location("speech_patterns", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SpeechPatternTests(unittest.TestCase):
    def test_analyze_speech_patterns_extracts_repeated_phrases_and_punctuation(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "收到",
                "msg_type_label": "text",
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776992460,
                "datetime": "2026-04-24 09:01:00",
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "收到",
                "msg_type_label": "text",
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776996000,
                "datetime": "2026-04-24 10:00:00",
                "chat_name": "技术群",
                "sender_name": "我",
                "content": "我来安排一下！",
                "msg_type_label": "text",
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776999600,
                "datetime": "2026-04-24 11:00:00",
                "chat_name": "技术群",
                "sender_name": "我",
                "content": "真的吗？",
                "msg_type_label": "text",
                "is_self": True,
                "direction": "outbound",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.analyze_speech_patterns(str(input_path))

        self.assertEqual(result["repeated_phrases"][0]["text"], "收到")
        self.assertEqual(result["repeated_phrases"][0]["count"], 2)
        self.assertEqual(result["punctuation_counts"]["question"], 1)
        self.assertEqual(result["punctuation_counts"]["exclamation"], 1)
        self.assertGreater(result["avg_message_length"], 1)
        self.assertIn("persona_modes", result)
        self.assertEqual(result["persona_modes"]["work"]["repeated_phrases"][0]["text"], "收到")
        self.assertIsNone(result["persona_modes"]["life"])
        self.assertIn("口癖与语言风格分析", result["report_markdown"])
        self.assertIn("工作人格", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
