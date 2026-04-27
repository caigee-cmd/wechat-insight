import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "wechat_insight_cli.py"


def load_module():
    spec = importlib.util.spec_from_file_location("wechat_insight_cli", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CliTests(unittest.TestCase):
    def test_list_command_forwards_list_chats_flag(self):
        module = load_module()
        calls = []

        export_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(["list"], export_module=export_module)

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--list-chats"]])

    def test_export_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        export_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["export", "--days", "7", "--contacts", "老婆"],
            export_module=export_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--days", "7", "--contacts", "老婆"]])

    def test_setup_command_calls_extract_module(self):
        module = load_module()
        calls = []

        extract_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(["setup"], extract_module=extract_module)

        self.assertEqual(result, 0)
        self.assertEqual(calls, [[]])

    def test_main_uses_sys_argv_when_argv_is_none(self):
        module = load_module()
        calls = []

        export_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        with mock.patch.object(sys, "argv", ["wechat-insight", "list"]):
            result = module.main(None, export_module=export_module)

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--list-chats"]])

    def test_doctor_command_reports_config_status(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            config_path = pathlib.Path(td) / "wechat-insight.json"
            keys_path = pathlib.Path(td) / "wechat-keys.json"
            config_path.write_text(json.dumps({
                "wxid": "wxid_test",
                "db_base_path": "/tmp/db_storage",
            }), encoding="utf-8")
            keys_path.write_text(json.dumps({
                "message_0": "ab" * 32,
            }), encoding="utf-8")

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = module.main(
                    ["doctor"],
                    config_path=str(config_path),
                    keys_path=str(keys_path),
                )

        output = buffer.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("配置文件: 已存在", output)
        self.assertIn("密钥文件: 已存在", output)
        self.assertIn("wxid: wxid_test", output)

    def test_daily_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        daily_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["daily", "--input", "/tmp/messages.jsonl"],
            daily_module=daily_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_features_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        features_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["features", "--input", "/tmp/messages.jsonl"],
            features_module=features_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_customer_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        customer_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["customer", "--input", "/tmp/messages.jsonl"],
            customer_module=customer_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_labels_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        labels_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["labels", "--input", "/tmp/messages.jsonl", "--output", "/tmp/labels.json"],
            labels_module=labels_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl", "--output", "/tmp/labels.json"]])

    def test_report_data_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        report_data_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["report-data", "--input", "/tmp/messages.jsonl", "--output", "/tmp/report_payload.json"],
            report_data_module=report_data_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl", "--output", "/tmp/report_payload.json"]])

    def test_html_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        html_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["html", "--payload", "/tmp/report_payload.json", "--output", "/tmp/dashboard.html"],
            html_module=html_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--payload", "/tmp/report_payload.json", "--output", "/tmp/dashboard.html"]])

    def test_dashboard_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        dashboard_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["dashboard", "--payload", "/tmp/report_payload.json", "--port", "4173"],
            dashboard_module=dashboard_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--payload", "/tmp/report_payload.json", "--port", "4173"]])

    def test_emotion_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        emotion_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["emotion", "--input", "/tmp/messages.jsonl"],
            emotion_module=emotion_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_mbti_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        mbti_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["mbti", "--input", "/tmp/messages.jsonl"],
            mbti_module=mbti_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_speech_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        speech_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["speech", "--input", "/tmp/messages.jsonl"],
            speech_module=speech_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])

    def test_social_command_forwards_remaining_args(self):
        module = load_module()
        calls = []

        social_module = types.SimpleNamespace(
            main=lambda argv=None: calls.append(argv) or 0
        )

        result = module.main(
            ["social", "--input", "/tmp/messages.jsonl"],
            social_module=social_module,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [["--input", "/tmp/messages.jsonl"]])


if __name__ == "__main__":
    unittest.main()
