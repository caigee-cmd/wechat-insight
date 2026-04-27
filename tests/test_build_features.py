import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "features" / "build_features.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_features", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildFeaturesTests(unittest.TestCase):
    def test_build_features_suffixes_all_output_files(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_id": "contact_a",
                "chat_name": "老婆",
                "sender_id": "contact_a",
                "sender_name": "老婆",
                "content": "明天下午3点发我报价方案，可以吗？",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
            }
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            output_dir = pathlib.Path(td) / "features"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.build_features(
                input_paths=[str(input_path)],
                output_dir=str(output_dir),
            )

            self.assertTrue(result["messages_enriched"].endswith("messages_enriched_20260424_20260424.jsonl"))
            self.assertTrue(result["daily_features"].endswith("daily_features_20260424_20260424.jsonl"))
            self.assertTrue(result["chat_features"].endswith("chat_features_20260424_20260424.jsonl"))
            self.assertTrue(result["contact_features"].endswith("contact_features_20260424_20260424.jsonl"))

    def test_build_features_generates_enriched_and_aggregate_files(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_id": "contact_a",
                "chat_name": "老婆",
                "sender_id": "contact_a",
                "sender_name": "老婆",
                "content": "明天下午3点发我报价方案，可以吗？",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_id": "group_x",
                "chat_name": "AI编辑器技术讨论",
                "sender_id": "wxid_zhangsan",
                "sender_name": "张三",
                "content": "今天上线完成了",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": True,
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            output_dir = pathlib.Path(td) / "features"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.build_features(
                input_paths=[str(input_path)],
                output_dir=str(output_dir),
            )

            enriched_path = pathlib.Path(result["messages_enriched"])
            daily_path = pathlib.Path(result["daily_features"])
            chat_path = pathlib.Path(result["chat_features"])
            contact_path = pathlib.Path(result["contact_features"])

            self.assertTrue(enriched_path.exists())
            self.assertTrue(daily_path.exists())
            self.assertTrue(chat_path.exists())
            self.assertTrue(contact_path.exists())

            enriched_rows = [
                json.loads(line)
                for line in enriched_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(enriched_rows), 2)
            self.assertIn("message_id", enriched_rows[0])
            self.assertIn("content_clean", enriched_rows[0])
            self.assertIn("topic_tags", enriched_rows[0])
            self.assertEqual(enriched_rows[0]["chat_type"], "private")

            daily_rows = [
                json.loads(line)
                for line in daily_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(daily_rows[0]["total_messages"], 2)
            self.assertEqual(daily_rows[0]["private_messages"], 1)
            self.assertEqual(daily_rows[0]["group_messages"], 1)
            self.assertEqual(daily_rows[0]["business_signal_count"], 1)

            chat_rows = [
                json.loads(line)
                for line in chat_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(chat_rows), 2)
            self.assertEqual(chat_rows[0]["chat_type"] in {"group", "private"}, True)

            contact_rows = [
                json.loads(line)
                for line in contact_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(contact_rows), 1)
            self.assertEqual(contact_rows[0]["contact_name"], "老婆")

    def test_build_features_preserves_existing_is_self_and_direction(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_id": "contact_a",
                "chat_name": "老婆",
                "sender_id": "__self__",
                "sender_name": "我",
                "content": "我发的",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            }
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            output_dir = pathlib.Path(td) / "features"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.build_features(
                input_paths=[str(input_path)],
                output_dir=str(output_dir),
            )

            enriched_path = pathlib.Path(result["messages_enriched"])
            enriched_rows = [
                json.loads(line)
                for line in enriched_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(enriched_rows[0]["is_self"])
            self.assertEqual(enriched_rows[0]["direction"], "outbound")

    def test_build_features_aggregates_direction_and_self_metrics(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_id": "contact_a",
                "chat_name": "老婆",
                "sender_id": "__self__",
                "sender_name": "我",
                "content": "我发的",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1776992460,
                "datetime": "2026-04-24 09:01:00",
                "chat_id": "contact_a",
                "chat_name": "老婆",
                "sender_id": "contact_a",
                "sender_name": "老婆",
                "content": "她回的",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776996000,
                "datetime": "2026-04-24 10:00:00",
                "chat_id": "group_x",
                "chat_name": "技术群",
                "sender_id": "wxid_zhangsan",
                "sender_name": "张三",
                "content": "别人发的",
                "msg_type": 1,
                "msg_type_label": "text",
                "is_group": True,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776996060,
                "datetime": "2026-04-24 10:01:00",
                "chat_id": "group_x",
                "chat_name": "技术群",
                "sender_id": "unknown",
                "sender_name": "unknown",
                "content": "[system] 撤回了一条消息",
                "msg_type": 10000,
                "msg_type_label": "system",
                "is_group": True,
                "is_self": None,
                "direction": "system",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            output_dir = pathlib.Path(td) / "features"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            result = module.build_features(
                input_paths=[str(input_path)],
                output_dir=str(output_dir),
            )

            daily_rows = [
                json.loads(line)
                for line in pathlib.Path(result["daily_features"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(daily_rows[0]["self_messages"], 1)
            self.assertEqual(daily_rows[0]["inbound_messages"], 2)
            self.assertEqual(daily_rows[0]["outbound_messages"], 1)
            self.assertEqual(daily_rows[0]["system_messages"], 1)

            chat_rows = {
                row["chat_name"]: row
                for row in (
                    json.loads(line)
                    for line in pathlib.Path(result["chat_features"]).read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            }
            self.assertEqual(chat_rows["老婆"]["self_messages"], 1)
            self.assertEqual(chat_rows["老婆"]["inbound_messages"], 1)
            self.assertEqual(chat_rows["老婆"]["outbound_messages"], 1)
            self.assertEqual(chat_rows["技术群"]["system_messages"], 1)

            contact_rows = [
                json.loads(line)
                for line in pathlib.Path(result["contact_features"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(contact_rows[0]["self_messages"], 1)
            self.assertEqual(contact_rows[0]["inbound_messages"], 1)
            self.assertEqual(contact_rows[0]["outbound_messages"], 1)
            self.assertEqual(contact_rows[0]["system_messages"], 0)


if __name__ == "__main__":
    unittest.main()
