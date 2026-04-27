import importlib.util
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "extract_keys.py"


def load_module():
    spec = importlib.util.spec_from_file_location("extract_keys", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExtractKeysTests(unittest.TestCase):
    def test_build_frida_script_hooks_commoncrypto_and_openssl_pbkdf(self):
        module = load_module()
        script = module.build_frida_script()

        self.assertIn("CCKeyDerivationPBKDF", script)
        self.assertIn("PKCS5_PBKDF2_HMAC", script)
        self.assertIn("this.passwordLen = args[2].toInt32();", script)
        self.assertIn("this.derivedKeyLen = args[8].toInt32();", script)
        self.assertIn("nativePtr = ptr(ptrValue);", script)
        self.assertIn("nativePtr.add(i).readU8()", script)
        self.assertNotIn("Array.from(bytes)", script)

    def test_pick_db_base_prefers_newest_message_db(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            older = pathlib.Path(td) / "older" / "message"
            newer = pathlib.Path(td) / "newer" / "message"
            older.mkdir(parents=True)
            newer.mkdir(parents=True)
            older_db = older / "message_0.db"
            newer_db = newer / "message_0.db"
            older_db.write_text("older")
            newer_db.write_text("newer")

            older_ts = 1_700_000_000
            newer_ts = 1_800_000_000
            os.utime(older_db, (older_ts, older_ts))
            os.utime(newer_db, (newer_ts, newer_ts))

            chosen = module.pick_db_base([
                str(older.parent),
                str(newer.parent),
            ])

            self.assertEqual(chosen, str(newer.parent))

    def test_find_db_key_matches_by_database_salt(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as td:
            db_path = pathlib.Path(td) / "message_0.db"
            salt = bytes.fromhex("13b2f1e978274d1ba72b43c13d6afcc4")
            db_path.write_bytes(salt + b"\x00" * 32)

            keys = [
                {
                    "rounds": 2,
                    "salt": salt.hex(),
                    "dk": "00" * 32,
                },
                {
                    "rounds": 256000,
                    "salt": salt.hex(),
                    "dk": "ab" * 32,
                },
            ]

            self.assertEqual(module.find_db_key(str(db_path), keys), "ab" * 32)


if __name__ == "__main__":
    unittest.main()
