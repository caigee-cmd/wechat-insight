import importlib.util
import json
import pathlib
import sqlite3
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "export_messages.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_messages", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExportMessagesTests(unittest.TestCase):
    def test_detect_self_sender_id_from_group_messages(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            db_path = pathlib.Path(td) / "message.db"
            db = sqlite3.connect(db_path)
            table = "Msg_grouphash"
            db.execute(
                f"""
                CREATE TABLE [{table}] (
                    local_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_type INTEGER,
                    real_sender_id INTEGER,
                    create_time INTEGER,
                    message_content TEXT
                )
                """
            )
            db.execute(
                f"INSERT INTO [{table}] (local_type, real_sender_id, create_time, message_content) VALUES (?, ?, ?, ?)",
                (1, 3, 1, "我发的消息"),
            )
            db.execute(
                f"INSERT INTO [{table}] (local_type, real_sender_id, create_time, message_content) VALUES (?, ?, ?, ?)",
                (1, 88, 2, "wxid_other:\n别人发的消息"),
            )
            db.commit()
            db.close()

            contacts = {"group@chatroom": "测试群"}
            hash_map = {"grouphash": "group@chatroom"}

            self_sender_id = module.detect_self_sender_id(
                str(db_path), contacts, hash_map
            )

            self.assertEqual(self_sender_id, 3)

    def test_resolve_sender_info_marks_private_self_as_outbound(self):
        module = load_module()

        sender_id, sender_name, content, is_self, direction = module.resolve_sender_info(
            uname="wxid_friend",
            display="朋友",
            is_group=False,
            real_sender_id=3,
            local_type=1,
            decoded_content="我发的",
            contacts={},
            self_sender_id=3,
        )

        self.assertEqual(sender_id, "__self__")
        self.assertEqual(sender_name, "我")
        self.assertEqual(content, "我发的")
        self.assertTrue(is_self)
        self.assertEqual(direction, "outbound")

    def test_resolve_sender_info_marks_group_other_as_inbound(self):
        module = load_module()

        sender_id, sender_name, content, is_self, direction = module.resolve_sender_info(
            uname="group@chatroom",
            display="测试群",
            is_group=True,
            real_sender_id=88,
            local_type=1,
            decoded_content="wxid_other:\n你好",
            contacts={"wxid_other": "张三"},
            self_sender_id=3,
        )

        self.assertEqual(sender_id, "wxid_other")
        self.assertEqual(sender_name, "张三")
        self.assertEqual(content, "你好")
        self.assertFalse(is_self)
        self.assertEqual(direction, "inbound")

    def test_export_messages_writes_is_self_and_direction(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            db_path = pathlib.Path(td) / "message.db"
            out_path = pathlib.Path(td) / "messages.jsonl"
            db = sqlite3.connect(db_path)
            table = "Msg_privatehash"
            db.execute(
                f"""
                CREATE TABLE [{table}] (
                    local_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    create_time INTEGER,
                    local_type INTEGER,
                    real_sender_id INTEGER,
                    message_content TEXT,
                    source TEXT
                )
                """
            )
            db.execute(
                f"INSERT INTO [{table}] (create_time, local_type, real_sender_id, message_content, source) VALUES (1, 1, 3, '我发的', '')"
            )
            db.execute(
                f"INSERT INTO [{table}] (create_time, local_type, real_sender_id, message_content, source) VALUES (2, 1, 9, '对方发的', '')"
            )
            db.commit()
            db.close()

            stats = module.export_messages(
                str(db_path),
                contacts={"wxid_friend": "朋友"},
                hash_map={"privatehash": "wxid_friend"},
                output_path=str(out_path),
                self_sender_id=3,
            )

            self.assertEqual(stats["total_messages"], 2)
            rows = [
                json.loads(line)
                for line in out_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(rows[0]["is_self"])
            self.assertEqual(rows[0]["direction"], "outbound")
            self.assertFalse(rows[1]["is_self"])
            self.assertEqual(rows[1]["direction"], "inbound")


if __name__ == "__main__":
    unittest.main()
