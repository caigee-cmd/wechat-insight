import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "digest.py"


def load_module():
    spec = importlib.util.spec_from_file_location("digest", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DigestTests(unittest.TestCase):
    def test_digest_exports_recent_messages_when_input_is_not_provided(self):
        module = load_module()
        calls = []

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            report_path = temp_dir / "daily.md"
            config_path = temp_dir / "config.json"
            config_path.write_text(
                json.dumps({
                    "data_dir": str(temp_dir),
                    "report_dir": str(temp_dir),
                }),
                encoding="utf-8",
            )

            def export_main(argv):
                calls.append(argv)
                messages_path = temp_dir / "messages_last1d.jsonl"
                messages_path.write_text(
                    json.dumps({
                        "timestamp": 1714377600,
                        "datetime": "2024-04-29 08:00:00",
                        "chat_name": "客户A",
                        "sender_name": "客户A",
                        "content": "今天可以帮我报价吗？",
                        "msg_type_label": "text",
                        "is_group": False,
                        "direction": "inbound",
                        "is_self": False,
                    }, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return 0

            result = module.run_digest(
                days=1,
                output_file=str(report_path),
                config_path=str(config_path),
                export_main=export_main,
            )

        self.assertEqual(calls, [["--days", "1", "--config", str(config_path)]])
        self.assertEqual(result["report_path"], str(report_path))
        self.assertIn("客户A", result["report_markdown"])

    def test_digest_from_input_writes_report_and_can_print_markdown(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            messages_path = temp_dir / "messages_today.jsonl"
            report_path = temp_dir / "daily.md"
            config_path = temp_dir / "config.json"
            config_path.write_text(
                json.dumps({
                    "data_dir": str(temp_dir),
                    "report_dir": str(temp_dir),
                }),
                encoding="utf-8",
            )
            messages = [
                {
                    "timestamp": 1714377600,
                    "datetime": "2024-04-29 08:00:00",
                    "chat_name": "客户A",
                    "sender_name": "客户A",
                    "content": "今天可以帮我报价吗？",
                    "msg_type_label": "text",
                    "is_group": False,
                    "direction": "inbound",
                    "is_self": False,
                },
                {
                    "timestamp": 1714381200,
                    "datetime": "2024-04-29 09:00:00",
                    "chat_name": "客户A",
                    "sender_name": "我",
                    "content": "可以，我下午发你",
                    "msg_type_label": "text",
                    "is_group": False,
                    "direction": "outbound",
                    "is_self": True,
                },
            ]
            messages_path.write_text(
                "".join(json.dumps(message, ensure_ascii=False) + "\n" for message in messages),
                encoding="utf-8",
            )

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = module.main([
                    "--input", str(messages_path),
                    "--output", str(report_path),
                    "--config", str(config_path),
                    "--stdout",
                ])
            report_exists = report_path.exists()

        output = buffer.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("DIGEST_REPORT_PATH=", output)
        self.assertIn(str(report_path), output)
        self.assertIn("# 微信聊天日报", output)
        self.assertIn("客户A", output)
        self.assertTrue(report_exists)

    def test_digest_from_empty_input_writes_empty_report(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            messages_path = temp_dir / "messages_today.jsonl"
            report_path = temp_dir / "daily.md"
            config_path = temp_dir / "config.json"
            config_path.write_text(
                json.dumps({
                    "data_dir": str(temp_dir),
                    "report_dir": str(temp_dir),
                }),
                encoding="utf-8",
            )
            messages_path.write_text("", encoding="utf-8")

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = module.main([
                    "--input", str(messages_path),
                    "--output", str(report_path),
                    "--config", str(config_path),
                    "--stdout",
                ])
            report_text = report_path.read_text(encoding="utf-8")

        output = buffer.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("DIGEST_TOTAL_MESSAGES=0", output)
        self.assertIn("暂无可分析消息", output)
        self.assertIn("暂无可分析消息", report_text)


if __name__ == "__main__":
    unittest.main()
