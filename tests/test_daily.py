import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "daily.py"


def load_module():
    spec = importlib.util.spec_from_file_location("daily", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DailyAnalyzerTests(unittest.TestCase):
    def test_analyze_daily_builds_markdown_report(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "早上好",
                "msg_type_label": "text",
                "is_group": False,
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "中午一起吃饭吗",
                "msg_type_label": "text",
                "is_group": False,
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "AI编辑器技术讨论",
                "sender_name": "张三",
                "content": "今天发版完成了",
                "msg_type_label": "text",
                "is_group": True,
            },
            {
                "timestamp": 1777037400,
                "datetime": "2026-04-24 21:30:00",
                "chat_name": "AI编辑器技术讨论",
                "sender_name": "李四",
                "content": "收到",
                "msg_type_label": "text",
                "is_group": True,
            },
            {
                "timestamp": 1777037700,
                "datetime": "2026-04-24 21:35:00",
                "chat_name": "AI编辑器技术讨论",
                "sender_name": "张三",
                "content": "收到",
                "msg_type_label": "text",
                "is_group": True,
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.analyze_daily(str(input_path))

        report = result["report_markdown"]
        self.assertEqual(result["total_messages"], 5)
        self.assertEqual(result["text_messages"], 5)
        self.assertIn("# 微信聊天日报", report)
        self.assertIn("总消息数：5", report)
        self.assertIn("最活跃会话是 AI编辑器技术讨论（3条）", report)
        self.assertIn("老婆（2条）", report)
        self.assertIn("21时（3条）", report)
        self.assertIn("收到（2次）", report)

    def test_find_latest_export_file_prefers_newest_jsonl(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            first = pathlib.Path(td) / "messages_20260423_20260423.jsonl"
            second = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            first.write_text("", encoding="utf-8")
            second.write_text("", encoding="utf-8")
            first.touch()
            second.touch()

            chosen = module.find_latest_export_file(td)

            self.assertEqual(chosen, str(second))

    def test_analyze_daily_includes_direction_breakdown(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "老婆",
                "sender_name": "我",
                "content": "早上好",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "中午一起吃饭吗",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
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
            {
                "timestamp": 1777037400,
                "datetime": "2026-04-24 21:30:00",
                "chat_name": "技术群",
                "sender_name": "unknown",
                "content": "[system] 撤回了一条消息",
                "msg_type_label": "system",
                "is_group": True,
                "is_self": None,
                "direction": "system",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.analyze_daily(str(input_path))

        report = result["report_markdown"]
        self.assertIn("## 互动结构", report)
        self.assertIn("- 主动发出：1条（25.0%）", report)
        self.assertIn("- 收到消息：2条（50.0%）", report)
        self.assertIn("- 系统消息：1条（25.0%）", report)
        self.assertIn("- 技术群（2条，发出 0 / 收到 1 / 系统 1）", report)
        self.assertIn("- 老婆（2条，发出 1 / 收到 1 / 系统 0）", report)

    def test_analyze_daily_highlights_pending_followups(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "中午一起吃饭吗？",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992460,
                "datetime": "2026-04-24 09:01:00",
                "chat_name": "老婆",
                "sender_name": "我",
                "content": "可以",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "某客户",
                "sender_name": "某客户",
                "content": "明天下午把报价发我，可以吗？",
                "msg_type_label": "text",
                "is_group": False,
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

            result = module.analyze_daily(str(input_path))

        report = result["report_markdown"]
        self.assertIn("## 待跟进信号", report)
        self.assertIn("- 待跟进会话数：1", report)
        self.assertIn("- 某客户：明天下午把报价发我，可以吗？", report)
        self.assertIn("商业", report)
        self.assertIn("问题", report)


if __name__ == "__main__":
    unittest.main()
