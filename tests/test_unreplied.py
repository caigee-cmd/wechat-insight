import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "analyze" / "unreplied.py"


def load_module():
    spec = importlib.util.spec_from_file_location("unreplied", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def msg(chat, ts, direction, content="hi", is_group=False):
    return {
        "timestamp": ts,
        "datetime": "2026-04-24 09:00:00",
        "chat_name": chat,
        "sender_name": chat if direction == "inbound" else "我",
        "content": content,
        "msg_type_label": "text",
        "is_group": is_group,
        "is_self": direction == "outbound",
        "direction": direction,
    }


class FindUnrepliedTests(unittest.TestCase):
    def test_last_message_inbound_is_unreplied(self):
        module = load_module()
        messages = [
            msg("客户A", 100, "inbound", "在吗"),
            msg("客户A", 200, "outbound", "在的"),
            msg("客户A", 300, "inbound", "那报价发我"),  # 最后一条我没回
            msg("客户B", 150, "inbound", "你好"),
            msg("客户B", 250, "outbound", "你好呀"),  # 我回了，不算
        ]
        items = module.find_unreplied(messages)
        names = [item["chat_name"] for item in items]
        self.assertEqual(names, ["客户A"])

    def test_groups_excluded_by_default(self):
        module = load_module()
        messages = [msg("技术群", 100, "inbound", "发版了", is_group=True)]
        self.assertEqual(module.find_unreplied(messages), [])
        included = module.find_unreplied(messages, include_groups=True)
        self.assertEqual([i["chat_name"] for i in included], ["技术群"])

    def test_system_messages_do_not_count_as_last(self):
        module = load_module()
        messages = [
            msg("客户A", 100, "inbound", "在吗"),
            msg("客户A", 200, "outbound", "在"),
            {  # 系统消息晚于我的回复，但不应让会话变成"未回复"
                "timestamp": 300,
                "chat_name": "客户A",
                "content": "对方撤回了一条消息",
                "msg_type_label": "system",
                "is_group": False,
                "direction": "system",
            },
        ]
        self.assertEqual(module.find_unreplied(messages), [])

    def test_days_window_filters_old_unreplied(self):
        module = load_module()
        day = module.DAY_SECONDS
        messages = [
            msg("近期客户", 100 * day, "inbound", "最近的"),
            msg("很久以前", 10 * day, "inbound", "很久以前的"),
        ]
        # 锚点为最新一条 = 100 天，window=7 天则只保留近期
        items = module.find_unreplied(messages, days=7)
        self.assertEqual([i["chat_name"] for i in items], ["近期客户"])

    def test_sorted_by_recency_desc(self):
        module = load_module()
        messages = [
            msg("早", 100, "inbound"),
            msg("晚", 300, "inbound"),
            msg("中", 200, "inbound"),
        ]
        items = module.find_unreplied(messages)
        self.assertEqual([i["chat_name"] for i in items], ["晚", "中", "早"])


class AnalyzeUnrepliedTests(unittest.TestCase):
    def _write(self, tmpdir, rows):
        path = pathlib.Path(tmpdir) / "messages_test.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return str(path)

    def _write_labels(self, tmpdir, contacts):
        path = pathlib.Path(tmpdir) / "labels.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"contacts": contacts}, f, ensure_ascii=False)
        return str(path)

    def test_exclude_ad_filters_and_counts(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            data = self._write(
                tmpdir,
                [
                    msg("真客户", 300, "inbound", "报价发我"),
                    msg("营销号", 200, "inbound", "点击领取优惠"),
                ],
            )
            labels = self._write_labels(
                tmpdir, {"营销号": {"role": "ad"}, "真客户": {"role": "customer"}}
            )

            with_ad = module.analyze_unreplied(input_path=data, labels_path=labels)
            self.assertEqual(len(with_ad["items"]), 2)

            no_ad = module.analyze_unreplied(
                input_path=data, labels_path=labels, exclude_ad=True
            )
            self.assertEqual([i["chat_name"] for i in no_ad["items"]], ["真客户"])
            self.assertEqual(no_ad["skipped_ad"], 1)

    def test_output_file_written(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            data = self._write(tmpdir, [msg("客户A", 300, "inbound", "报价发我")])
            out = str(pathlib.Path(tmpdir) / "out.md")
            result = module.analyze_unreplied(input_path=data, output_file=out)
            self.assertEqual(result["report_path"], out)
            content = pathlib.Path(out).read_text(encoding="utf-8")
            self.assertIn("客户A", content)
            self.assertIn("未回复会话数：1", content)


if __name__ == "__main__":
    unittest.main()
