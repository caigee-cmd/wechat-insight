import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()
