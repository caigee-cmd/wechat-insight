import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "customer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("customer", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CustomerAnalyzerTests(unittest.TestCase):
    def test_analyze_customer_builds_business_report(self):
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
                "chat_name": "客户A",
                "sender_name": "我",
                "content": "可以，我晚点整理方案",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": True,
                "direction": "outbound",
            },
            {
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "客户B",
                "sender_name": "客户B",
                "content": "系统报错了，不能用，尽快看下",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1777037400,
                "datetime": "2026-04-24 21:30:00",
                "chat_name": "朋友C",
                "sender_name": "朋友C",
                "content": "晚上喝酒不",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1777037700,
                "datetime": "2026-04-24 21:35:00",
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

            result = module.analyze_customer(str(input_path))

        report = result["report_markdown"]
        self.assertEqual(result["total_private_contacts"], 3)
        self.assertIn("# 客户与商业分析", report)
        self.assertIn("## customer 分组", report)
        self.assertIn("## vendor 分组", report)
        self.assertIn("## unknown 分组", report)
        self.assertIn("客户A", report)
        self.assertIn("客户B", report)
        self.assertIn("报价", report)
        self.assertIn("报错", report)
        self.assertIn("系统报错了，不能用，尽快看下", report)

    def test_analyze_customer_respects_contact_labels(self):
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
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "朋友C",
                "sender_name": "朋友C",
                "content": "帮我看下这个报价",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1777037400,
                "datetime": "2026-04-24 21:30:00",
                "chat_name": "广告号D",
                "sender_name": "广告号D",
                "content": "您好，明天正常上班，最快当天放款",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        labels = {
            "contacts": {
                "朋友C": {"role": "friend"},
                "广告号D": {"role": "ad"},
            }
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            labels_path = pathlib.Path(td) / "contacts_labels.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            labels_path.write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")

            result = module.analyze_customer(
                str(input_path),
                labels_path=str(labels_path),
            )

        report = result["report_markdown"]
        self.assertEqual(result["business_scope_contacts"], 1)
        self.assertIn("客户A", report)
        self.assertNotIn("朋友C", report)
        self.assertNotIn("广告号D", report)
        self.assertIn("已排除标签联系人：2", report)

    def test_analyze_customer_separates_contacts_by_role(self):
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
                "timestamp": 1777035600,
                "datetime": "2026-04-24 21:00:00",
                "chat_name": "供应商B",
                "sender_name": "供应商B",
                "content": "合同已经发你了，确认下",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
            {
                "timestamp": 1777037400,
                "datetime": "2026-04-24 21:30:00",
                "chat_name": "未知C",
                "sender_name": "未知C",
                "content": "看下这个方案",
                "msg_type_label": "text",
                "is_group": False,
                "is_self": False,
                "direction": "inbound",
            },
        ]

        labels = {
            "contacts": {
                "客户A": {"role": "customer"},
                "供应商B": {"role": "vendor"},
            }
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = pathlib.Path(td) / "messages_20260424_20260424.jsonl"
            labels_path = pathlib.Path(td) / "contacts_labels.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            labels_path.write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")

            result = module.analyze_customer(
                str(input_path),
                labels_path=str(labels_path),
            )

        report = result["report_markdown"]
        customer_section = report.split("## customer 分组", 1)[1].split("## vendor 分组", 1)[0]
        vendor_section = report.split("## vendor 分组", 1)[1].split("## unknown 分组", 1)[0]
        unknown_section = report.split("## unknown 分组", 1)[1]

        self.assertIn("客户A", customer_section)
        self.assertNotIn("供应商B", customer_section)
        self.assertNotIn("未知C", customer_section)

        self.assertIn("供应商B", vendor_section)
        self.assertNotIn("客户A", vendor_section)
        self.assertNotIn("未知C", vendor_section)

        self.assertIn("未知C", unknown_section)
        self.assertNotIn("客户A", unknown_section)
        self.assertNotIn("供应商B", unknown_section)


if __name__ == "__main__":
    unittest.main()
