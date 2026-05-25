import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "share_card.py"


def load_module():
    spec = importlib.util.spec_from_file_location("share_card", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SAMPLE_PAYLOAD = {
    "overview": {
        "total_messages": 1234,
        "active_chat_count": 9,
        "date_span_days": 30,
        "business_contact_count": 6,
        "pending_followup_count": 3,
        "median_response_latency_minutes": 13,
        "dominant_emotion": "positive",
        "mbti_type": "ESFJ",
    },
    "sections": {
        "mbti": {
            "mbti_type": "ESFJ",
            "dimensions": {
                "EI": {"label": "能量来源", "letter": "E"},
                "SN": {"label": "信息偏好", "letter": "S"},
                "TF": {"label": "决策方式", "letter": "F"},
                "JP": {"label": "行动节奏", "letter": "J"},
            },
        },
        "emotion": {"dominant_emotion": "positive"},
        "speech": {"top_terms": [{"text": "收到", "count": 19}, {"text": "放心", "count": 17}]},
        "daily": {"top_hours": [["17", 56], ["11", 51]]},
    },
}


class ShareCardTests(unittest.TestCase):
    def test_build_html_contains_key_highlights(self):
        module = load_module()
        out = module.build_share_card_html(SAMPLE_PAYLOAD)

        self.assertIn("<!doctype html>", out)
        self.assertIn("我的微信关系画像", out)
        self.assertIn("ESFJ", out)
        self.assertIn("1,234", out)          # 千分位格式化
        self.assertIn("积极", out)            # 情绪标签翻译
        self.assertIn("17:00", out)           # 最活跃时段
        self.assertIn("收到", out)            # 口头禅
        self.assertIn("github.com/caigee-cmd/wechat-insight", out)  # 水印
        self.assertIn("启发式", out)          # 免责声明

    def test_handles_empty_payload_without_crashing(self):
        module = load_module()
        out = module.build_share_card_html({})
        self.assertIn("我的微信关系画像", out)
        self.assertIn("数据不足", out)

    def test_generate_writes_file_from_payload(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = pathlib.Path(tmp) / "report_payload_20260524.json"
            payload_path.write_text(
                __import__("json").dumps(SAMPLE_PAYLOAD, ensure_ascii=False),
                encoding="utf-8",
            )
            result = module.generate_share_card(payload_path=str(payload_path))
            card_path = pathlib.Path(result["card_path"])
            self.assertTrue(card_path.exists())
            self.assertEqual(card_path.name, "share_card_20260524.html")
            self.assertIn("ESFJ", card_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
