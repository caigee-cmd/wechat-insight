import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "mbti.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mbti", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MbtiAnalyzerTests(unittest.TestCase):
    def test_analyze_mbti_infers_type_from_self_messages(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "大家明天开会，我来安排一下。",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776996000,
                "datetime": "2026-04-24 10:00:00",
                "chat_name": "技术群",
                "sender_name": "我",
                "content": "这个方向要看长期策略和模型能力，先做个框架。",
                "msg_type_label": "text",
                "is_group": True,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776999600,
                "datetime": "2026-04-24 11:00:00",
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "按数据和逻辑判断，这个方案效率更高，今天确认。",
                "msg_type_label": "text",
                "is_group": False,
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

            result = module.analyze_mbti(str(input_path))

        self.assertEqual(result["mbti_type"], "ENTJ")
        self.assertEqual(result["dimensions"]["EI"]["letter"], "E")
        self.assertEqual(result["dimensions"]["SN"]["letter"], "N")
        self.assertEqual(result["dimensions"]["TF"]["letter"], "T")
        self.assertEqual(result["dimensions"]["JP"]["letter"], "J")
        self.assertIn("persona_modes", result)
        self.assertEqual(result["persona_modes"]["work"]["mbti_type"], "ENTJ")
        self.assertIsNone(result["persona_modes"]["life"])
        self.assertIn("MBTI 性格推测", result["report_markdown"])
        self.assertIn("ENTJ", result["report_markdown"])
        self.assertIn("工作人格", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
