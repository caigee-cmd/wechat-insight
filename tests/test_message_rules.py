import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "features" / "message_rules.py"


def load_module():
    spec = importlib.util.spec_from_file_location("message_rules", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MessageRulesTests(unittest.TestCase):
    def test_rule_flags_cover_schedule_action_and_topic(self):
        module = load_module()
        message = {
            "content": "明天下午3点发我报价方案，可以吗？",
            "msg_type_label": "text",
        }

        result = module.analyze_message_rules(message)

        self.assertTrue(result["is_question"])
        self.assertTrue(result["is_action_item"])
        self.assertTrue(result["is_schedule"])
        self.assertTrue(result["is_business_signal"])
        self.assertTrue(result["is_quote_signal"])
        self.assertIn("customer", result["topic_tags"])
        self.assertIn("明天", result["keyword_hits"])

    def test_rule_flags_detect_support_and_negative_signal(self):
        module = load_module()
        message = {
            "content": "系统报错了，真的很离谱，不能用",
            "msg_type_label": "text",
        }

        result = module.analyze_message_rules(message)

        self.assertTrue(result["is_support_signal"])
        self.assertTrue(result["is_negative_signal"])
        self.assertFalse(result["is_quote_signal"])

    def test_schedule_flag_is_not_triggered_by_random_digits_or_links(self):
        module = load_module()
        message = {
            "content": "看看这个链接 https://example.com/a1b2c3/profile42",
            "msg_type_label": "text",
        }

        result = module.analyze_message_rules(message)

        self.assertFalse(result["is_schedule"])


if __name__ == "__main__":
    unittest.main()
