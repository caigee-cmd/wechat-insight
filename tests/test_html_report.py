import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "html_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("html_report", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HtmlReportTests(unittest.TestCase):
    def test_generate_html_report_builds_single_file_dashboard_from_payload(self):
        module = load_module()

        payload = {
            "schema_version": "report-data.v1",
            "generated_at": "2026-04-26T10:30:00",
            "overview": {
                "total_messages": 3,
                "text_messages": 3,
                "active_chat_count": 2,
                "group_message_count": 1,
                "private_message_count": 2,
                "total_private_contacts": 1,
                "business_contact_count": 1,
                "pending_followup_count": 1,
                "generated_contact_labels": 1,
                "dominant_emotion": "positive",
                "mbti_type": "ENTJ",
                "avg_message_length": 5.25,
                "median_response_latency_minutes": 10,
            },
            "sources": {
                "input_files": ["/tmp/messages.jsonl"],
                "config_path": "/tmp/wechat-insight.json",
            },
            "artifacts": {
                "payload_path": "/tmp/report_payload.json",
                "daily_report_path": "/tmp/daily_20260424.md",
                "customer_report_path": "/tmp/customer_report.md",
                "emotion_report_path": "/tmp/emotion_20260424.md",
                "mbti_report_path": "/tmp/mbti_20260424.md",
                "speech_report_path": "/tmp/speech_20260424.md",
                "social_report_path": "/tmp/social_20260424.md",
                "labels_path": "/tmp/contacts_labels.json",
                "feature_files": {
                    "messages_enriched": "/tmp/messages_enriched.jsonl",
                    "daily_features": "/tmp/daily_features.jsonl",
                    "chat_features": "/tmp/chat_features.jsonl",
                    "contact_features": "/tmp/contact_features.jsonl",
                },
            },
            "sections": {
                "daily": {
                    "summary_lines": ["今天共记录 3 条消息，主要集中在 09时（2条）。"],
                    "top_chats": [["客户A", 2], ["技术群", 1]],
                    "top_contacts": [["客户A", 2]],
                    "top_hours": [["09", 2], ["21", 1]],
                    "pending_followups": [
                        {
                            "chat_name": "客户A",
                            "content": "明天下午把报价发我，可以吗？",
                            "labels": ["商业", "问题"],
                            "datetime": "2026-04-24 09:00:00",
                        }
                    ],
                },
                "customer": {
                    "top_opportunities": [
                        {
                            "contact_name": "客户A",
                            "opportunity_score": 15,
                            "quote_signal_count": 1,
                            "business_signal_count": 1,
                            "action_signal_count": 0,
                            "role": "customer",
                            "stage": "negotiating",
                        }
                    ],
                    "top_support_risks": [
                        {
                            "contact_name": "客户B",
                            "risk_score": 9,
                            "support_signal_count": 1,
                            "negative_signal_count": 1,
                            "role": "unknown",
                            "stage": "supporting",
                        }
                    ],
                    "pending_followups": [
                        {
                            "contact_name": "客户A",
                            "pending_followup": {
                                "content": "明天下午把报价发我，可以吗？",
                                "labels": ["商业", "问题"],
                                "datetime": "2026-04-24 09:00:00",
                            },
                        }
                    ],
                    "role_counts": {
                        "customer": 1,
                        "vendor": 0,
                        "unknown": 1,
                    },
                },
                "labels": {
                    "generated_contacts": 1,
                    "total_private_contacts": 1,
                    "applied_suggestions": 0,
                },
                "features": {
                    "output_dir": "/tmp/features",
                    "chat_leaderboard": [
                        {
                            "chat_id": "group-1",
                            "chat_name": "技术群",
                            "chat_type": "group",
                            "total_messages": 1,
                            "business_signal_count": 1,
                            "support_signal_count": 0,
                        }
                    ],
                    "contact_leaderboard": [
                        {
                            "contact_id": "contact-1",
                            "contact_name": "客户A",
                            "total_messages": 2,
                            "business_signal_count": 1,
                            "support_signal_count": 0,
                        }
                    ],
                },
                "emotion": {
                    "emotion_distribution": {
                        "positive": 2,
                        "negative": 0,
                        "neutral": 1,
                        "anxious": 0,
                        "angry": 0,
                    },
                    "dominant_emotion": "positive",
                    "daily_emotions": [
                        {"date": "2026-04-24", "positive": 2, "negative": 0, "neutral": 1, "anxious": 0, "angry": 0},
                    ],
                    "persona_modes": {
                        "work": {"dominant_emotion": "positive"},
                        "life": None,
                    },
                },
                "mbti": {
                    "mbti_type": "ENTJ",
                    "dimensions": {
                        "EI": {"letter": "E"},
                        "SN": {"letter": "N"},
                        "TF": {"letter": "T"},
                        "JP": {"letter": "J"},
                    },
                    "persona_modes": {
                        "work": {"mbti_type": "ENTJ"},
                        "life": None,
                    },
                },
                "speech": {
                    "repeated_phrases": [{"text": "收到", "count": 2}],
                    "punctuation_counts": {"question": 1, "exclamation": 1, "ellipsis": 0},
                    "avg_message_length": 5.25,
                    "persona_modes": {
                        "work": {"repeated_phrases": [{"text": "收到", "count": 2}]},
                        "life": None,
                    },
                },
                "social": {
                    "group_message_count": 1,
                    "private_message_count": 2,
                    "median_response_latency_minutes": 10,
                    "top_chats": [["客户A", 2], ["技术群", 1]],
                    "persona_modes": {
                        "work": {"top_chats": [["客户A", 2]]},
                        "life": None,
                    },
                },
            },
        }

        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            payload_path = temp_dir / "report_payload.json"
            output_path = temp_dir / "dashboard.html"
            payload_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = module.generate_html_report(
                payload_path=str(payload_path),
                output_file=str(output_path),
            )

            self.assertEqual(result["payload_path"], str(payload_path))
            self.assertEqual(result["report_path"], str(output_path))
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("<title>WeChat Insight Dashboard</title>", html)
            self.assertIn("微信洞察 Dashboard", html)
            self.assertIn("总消息", html)
            self.assertIn("客户A", html)
            self.assertIn("技术群", html)
            self.assertIn("明天下午把报价发我，可以吗？", html)
            self.assertIn("ENTJ", html)
            self.assertIn("推进中", html)
            self.assertIn("售后处理中", html)
            self.assertIn("客户", html)
            self.assertIn("未知", html)
            self.assertIn("2026-04-26 10:30", html)
            self.assertIn("收到", html)
            self.assertIn("10", html)
            self.assertIn("工作人格", html)
            self.assertIn("社交关系图", html)
            self.assertIn("关系摘要", html)
            self.assertIn("relationship-inspector", html)
            self.assertIn("重置到中心", html)
            self.assertIn("report-payload", html)
            self.assertIn("report-data.v1", html)
            self.assertNotIn(">customer<", html)
            self.assertNotIn(">vendor<", html)
            self.assertNotIn(">negotiating<", html)
            self.assertNotIn(">supporting<", html)
            self.assertNotIn(">positive<", html)


if __name__ == "__main__":
    unittest.main()
