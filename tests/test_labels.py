import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "contact_labels.py"


def load_module():
    spec = importlib.util.spec_from_file_location("contact_labels", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContactLabelsBootstrapTests(unittest.TestCase):
    def test_bootstrap_labels_generates_editable_contacts_file(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "明天下午把报价发我，可以吗？",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_name": "朋友B",
                "sender_name": "朋友B",
                "content": "晚上喝酒不",
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
        ]

        existing_labels = {
            "contacts": {
                "客户A": {
                    "role": "customer",
                    "notes": "已确认客户",
                }
            }
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            labels_path = pathlib.Path(td) / "contacts_labels.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            labels_path.write_text(
                json.dumps(existing_labels, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = module.bootstrap_contact_labels(
                input_path=str(input_path),
                output_file=str(labels_path),
            )

            payload = json.loads(labels_path.read_text(encoding="utf-8"))

        self.assertEqual(result["total_private_contacts"], 2)
        self.assertEqual(result["generated_contacts"], 2)
        self.assertEqual(payload["contacts"]["客户A"]["role"], "customer")
        self.assertEqual(payload["contacts"]["客户A"]["notes"], "已确认客户")
        self.assertEqual(payload["contacts"]["朋友B"]["role"], "unknown")
        self.assertIn("suggested_role", payload["contacts"]["朋友B"])
        self.assertEqual(payload["contacts"]["朋友B"]["total_messages"], 1)
        self.assertNotIn("技术群", payload["contacts"])

    def test_bootstrap_labels_can_apply_suggestions_without_overwriting_existing_roles(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "晚上回家吃饭",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_name": "产品审批部-吴经理",
                "sender_name": "产品审批部-吴经理",
                "content": "您好，明天正常上班，最快当天放款",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "把报价发我",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        existing_labels = {
            "contacts": {
                "客户A": {
                    "role": "customer",
                    "notes": "手动确认",
                }
            }
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            labels_path = pathlib.Path(td) / "contacts_labels.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            labels_path.write_text(
                json.dumps(existing_labels, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = module.bootstrap_contact_labels(
                input_path=str(input_path),
                output_file=str(labels_path),
                apply_suggestions=True,
            )

            payload = json.loads(labels_path.read_text(encoding="utf-8"))

        self.assertEqual(result["applied_suggestions"], 2)
        self.assertEqual(payload["contacts"]["老婆"]["role"], "family")
        self.assertEqual(payload["contacts"]["产品审批部-吴经理"]["role"], "ad")
        self.assertEqual(payload["contacts"]["客户A"]["role"], "customer")
        self.assertEqual(payload["contacts"]["客户A"]["notes"], "手动确认")

    def test_bootstrap_labels_adds_reasons_and_prioritizes_business_contacts(self):
        module = load_module()

        rows = [
            {
                "timestamp": 1776992400,
                "datetime": "2026-04-24 09:00:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "明天下午把报价发我，可以吗？",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992460,
                "datetime": "2026-04-24 09:01:00",
                "chat_name": "客户A",
                "sender_name": "客户A",
                "content": "方案也一起发我",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992700,
                "datetime": "2026-04-24 09:05:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "晚上回家吃饭",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1776992760,
                "datetime": "2026-04-24 09:06:00",
                "chat_name": "老婆",
                "sender_name": "老婆",
                "content": "记得带水果",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            labels_path = pathlib.Path(td) / "contacts_labels.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            module.bootstrap_contact_labels(
                input_path=str(input_path),
                output_file=str(labels_path),
            )

            payload = json.loads(labels_path.read_text(encoding="utf-8"))
            ordered_names = list(payload["contacts"].keys())

        self.assertEqual(ordered_names[0], "客户A")
        self.assertIn("suggested_role_reason", payload["contacts"]["客户A"])
        self.assertIn("quote_signal", payload["contacts"]["客户A"]["suggested_role_reason"])
        self.assertIn("business_signal", payload["contacts"]["客户A"]["suggested_role_reason"])
        self.assertIn("review_priority_score", payload["contacts"]["客户A"])
        self.assertGreater(
            payload["contacts"]["客户A"]["review_priority_score"],
            payload["contacts"]["老婆"]["review_priority_score"],
        )


if __name__ == "__main__":
    unittest.main()
