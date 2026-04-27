import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "social_graph.py"


def load_module():
    spec = importlib.util.spec_from_file_location("social_graph", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SocialGraphTests(unittest.TestCase):
    def test_analyze_social_graph_builds_response_latency_and_activity(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "在吗",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776993000,
                "datetime": "2026-04-24 09:10:00",
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "在，我来处理",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "技术群",
                "sender_name": "张三",
                "content": "今天发版完成了",
                "msg_type_label": "text",
                "is_group": True,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.analyze_social_graph(str(input_path))

        self.assertEqual(result["group_message_count"], 1)
        self.assertEqual(result["private_message_count"], 2)
        self.assertEqual(result["median_response_latency_minutes"], 10)
        self.assertEqual(result["top_chats"][0][0], "客户A")
        self.assertIn("persona_modes", result)
        self.assertEqual(result["persona_modes"]["work"]["top_chats"][0][0], "客户A")
        self.assertIsNone(result["persona_modes"]["life"])
        self.assertIn("社交图谱与时间画像", result["report_markdown"])
        self.assertIn("10 分钟", result["report_markdown"])
        self.assertIn("工作人格", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
