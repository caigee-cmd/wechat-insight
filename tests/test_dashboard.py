import importlib.util
import json
import os
import pathlib
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "dashboard.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dashboard", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DashboardTests(unittest.TestCase):
    def test_prepare_dashboard_payload_copies_payload_into_public_dir(self):
        module = load_module()

        payload = {
            "schema_version": "report-data.v1",
            "overview": {"total_messages": 3},
            "sections": {},
            "artifacts": {"payload_path": "/tmp/report_payload.json"},
        }

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            source_payload = temp_dir / "report_payload.json"
            project_dir = temp_dir / "dashboard"
            (project_dir / "public").mkdir(parents=True)
            (project_dir / "package.json").write_text("{}", encoding="utf-8")
            source_payload.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = module.prepare_dashboard_payload(
                project_dir=str(project_dir),
                payload_path=str(source_payload),
            )

            copied_payload_path = project_dir / "public" / "report_payload.json"
            self.assertEqual(result["project_dir"], str(project_dir))
            self.assertEqual(result["source_payload_path"], str(source_payload))
            self.assertEqual(result["dashboard_payload_path"], str(copied_payload_path))
            self.assertTrue(copied_payload_path.exists())
            copied_payload = json.loads(copied_payload_path.read_text(encoding="utf-8"))
            self.assertEqual(copied_payload["schema_version"], "report-data.v1")
            self.assertEqual(copied_payload["overview"]["total_messages"], 3)

    def test_build_dashboard_command_returns_shell_dev_command(self):
        module = load_module()

        command = module.build_dashboard_command(
            project_dir="/tmp/dashboard",
            host="127.0.0.1",
            port=4173,
        )

        self.assertEqual(command["cwd"], "/tmp/dashboard")
        self.assertEqual(
            command["argv"],
            [
                os.environ.get("SHELL") or "/bin/zsh",
                "-lc",
                "npm run dev -- --host 127.0.0.1 --port 4173",
            ],
        )

    def test_build_export_args_supports_dashboard_date_export(self):
        module = load_module()

        args = module.build_export_args(
            days=7,
            chats="客户群",
            contacts="陈毅",
            config_path="/tmp/config.json",
            output_dir="~/wechat-data",
        )

        self.assertEqual(
            args,
            [
                "--days", "7",
                "--chats", "客户群",
                "--contacts", "陈毅",
                "--config", "/tmp/config.json",
                "--output", os.path.expanduser("~/wechat-data"),
            ],
        )

    def test_run_dashboard_exports_before_payload_when_days_is_provided(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            project_dir = temp_dir / "dashboard"
            data_dir = temp_dir / "data"
            payload_path = temp_dir / "report_payload.json"
            exported_path = data_dir / "messages_last7d.jsonl"
            (project_dir / "public").mkdir(parents=True)
            (project_dir / "package.json").write_text("{}", encoding="utf-8")
            data_dir.mkdir()

            export_calls = []

            def fake_export(argv=None):
                export_calls.append(argv)
                exported_path.write_text(
                    json.dumps({"content": "hello"}, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return 0

            def fake_build_report_data_payload(input_path=None, **_kwargs):
                self.assertEqual(input_path, str(exported_path))
                payload_path.write_text(
                    json.dumps({
                        "schema_version": "report-data.v1",
                        "artifacts": {"payload_path": str(payload_path)},
                    }),
                    encoding="utf-8",
                )
                return {"artifacts": {"payload_path": str(payload_path)}}

            original_builder = module.REPORT_DATA_MODULE.build_report_data_payload
            module.REPORT_DATA_MODULE.build_report_data_payload = fake_build_report_data_payload
            try:
                with mock.patch.object(
                    module.subprocess,
                    "run",
                    return_value=types.SimpleNamespace(returncode=0),
                ) as run_mock:
                    result = module.run_dashboard(
                        project_dir=str(project_dir),
                        days=7,
                        export_output=str(data_dir),
                        export_main=fake_export,
                        skip_install=True,
                        port=4180,
                    )
            finally:
                module.REPORT_DATA_MODULE.build_report_data_payload = original_builder

        self.assertEqual(export_calls, [["--days", "7", "--output", str(data_dir)]])
        self.assertEqual(result["input_path"], str(exported_path))
        self.assertEqual(result["source_payload_path"], str(payload_path))
        self.assertEqual(result["port"], 4180)
        run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
