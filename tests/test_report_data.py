import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "report_data.py"


def load_module():
    spec = importlib.util.spec_from_file_location("report_data", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReportDataTests(unittest.TestCase):
    def test_build_report_data_payload_outputs_unified_json_payload(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_id": "customer_a",
                "chat_name": "客户A",
                "sender_id": "customer_a",
                "sender_name": "客户A",
                "content": "明天下午把报价发我，可以吗？",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_id": "customer_a",
                "chat_name": "客户A",
                "sender_id": "__self__",
                "sender_name": "我",
                "content": "可以，我晚点整理方案",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_id": "group_x",
                "chat_name": "技术群",
                "sender_id": "wxid_zhangsan",
                "sender_name": "张三",
                "content": "今天发版完成了",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": True,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            input_path = temp_dir / "messages_20260424_20260424.jsonl"
            config_path = temp_dir / "wechat-insight.json"
            labels_path = temp_dir / "contacts_labels.json"
            report_output_path = temp_dir / "reports" / "report_payload.json"
            feature_dir = temp_dir / "features"
            report_dir = temp_dir / "reports"
            data_dir = temp_dir / "data"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            config_path.write_text(json.dumps({
                "data_dir": str(data_dir),
                "feature_dir": str(feature_dir),
                "report_dir": str(report_dir),
                "contacts_labels_path": str(labels_path),
            }, ensure_ascii=False), encoding="utf-8")

            result = module.build_report_data_payload(
                input_path=str(input_path),
                output_file=str(report_output_path),
                config_path=str(config_path),
                labels_path=str(labels_path),
            )

            self.assertEqual(result["schema_version"], "report-data.v1")
            self.assertEqual(result["overview"]["total_messages"], 3)
            self.assertEqual(result["overview"]["business_contact_count"], 1)
            self.assertEqual(result["overview"]["pending_followup_count"], 0)
            self.assertEqual(result["overview"]["date_span_days"], 1)
            self.assertEqual(result["sources"]["input_files"], [str(input_path)])
            self.assertEqual(result["artifacts"]["payload_path"], str(report_output_path))
            self.assertTrue(pathlib.Path(result["artifacts"]["daily_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["customer_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["emotion_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["mbti_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["speech_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["social_report_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["labels_path"]).exists())
            self.assertTrue(pathlib.Path(result["artifacts"]["feature_files"]["daily_features"]).exists())
            self.assertEqual(len(result["sections"]["features"]["daily_activity"]), 1)
            self.assertEqual(result["sections"]["features"]["daily_activity"][0]["total_messages"], 3)
            self.assertEqual(result["sections"]["features"]["available_dates"], ["2026-04-24"])
            self.assertEqual(result["sections"]["features"]["chat_leaderboard"][0]["chat_name"], "客户A")
            self.assertIn("emotion", result["sections"])
            self.assertIn("mbti", result["sections"])
            self.assertIn("speech", result["sections"])
            self.assertIn("social", result["sections"])
            self.assertIn("persona_modes", result["sections"]["mbti"])
            self.assertIn("persona_modes", result["sections"]["emotion"])
            self.assertIn("persona_modes", result["sections"]["speech"])
            self.assertIn("persona_modes", result["sections"]["social"])

            payload = json.loads(report_output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "report-data.v1")
            self.assertIn("daily", payload["sections"])
            self.assertIn("customer", payload["sections"])
            self.assertIn("labels", payload["sections"])
            self.assertIn("features", payload["sections"])
            self.assertIn("emotion", payload["sections"])
            self.assertIn("mbti", payload["sections"])
            self.assertIn("speech", payload["sections"])
            self.assertIn("social", payload["sections"])
            self.assertIn("persona_modes", payload["sections"]["mbti"])
            self.assertEqual(payload["sections"]["daily"]["total_messages"], 3)
            self.assertEqual(payload["sections"]["customer"]["business_contact_count"], 1)
            self.assertEqual(payload["sections"]["features"]["daily_activity"][0]["date"], "2026-04-24")


if __name__ == "__main__":
    unittest.main()
