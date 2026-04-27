#!/usr/bin/env python3
"""
微信消息导出工具
从加密的微信数据库提取聊天记录，导出为标准 JSONL 格式

用法:
    python3 export_messages.py                           # 导出全部数据
    python3 export_messages.py --days 30                 # 导出最近30天
    python3 export_messages.py --start 2025-01-01 --end 2025-03-31
    python3 export_messages.py --chats "群名1,群名2"       # 仅导出指定群聊
    python3 export_messages.py --contacts "联系人1"        # 仅导出指定联系人
    python3 export_messages.py --list-chats              # 列出所有群聊和联系人
"""
import sqlite3
import struct
import os
import sys
import json
import hashlib
import argparse
from datetime import datetime, timedelta
from Crypto.Cipher import AES
import zstandard as zstd

# === 常量 ===
PAGE_SIZE = 4096
RESERVE = 80
IV_SIZE = 16
KEYS_FILE = os.path.expanduser("~/.config/wechat-keys.json")
CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
TMP_DIR = os.path.expanduser("~/tmp/wechat_insight")
SELF_SENDER_FALLBACK = 3
SELF_SENDER_ID = "__self__"
SELF_SENDER_NAME = "我"
SYSTEM_SENDER_IDS = {22}

MSG_TYPE_LABELS = {
    1: "text",          # 文本
    3: "image",         # 图片
    34: "voice",        # 语音
    42: "card",         # 名片
    43: "video",        # 视频
    47: "sticker",      # 表情
    48: "location",     # 位置
    49: "link",         # 链接/小程序
    10000: "system",    # 系统消息
}

ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'
_zstd_decompressor = zstd.ZstdDecompressor()


# === 配置加载 ===

def load_config(config_path=None):
    path = config_path or CONFIG_FILE
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "wxid": None,
        "db_base_path": None,
        "data_dir": os.path.expanduser("~/.wechat-insight/data"),
        "report_dir": os.path.expanduser("~/.wechat-insight/reports"),
    }


def get_db_base(config):
    if config.get("db_base_path"):
        return os.path.expanduser(config["db_base_path"])
    if config.get("wxid"):
        return os.path.expanduser(
            f"~/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
            f"xwechat_files/{config['wxid']}/db_storage"
        )
    print("[ERROR] 未配置 wxid 或 db_base_path，请先运行 extract_keys.py")
    return None


def load_keys():
    with open(KEYS_FILE) as f:
        return json.load(f)


# === 数据库解密 ===

def decrypt_db(db_path, key_hex, out_path):
    key = bytes.fromhex(key_hex)
    with open(db_path, "rb") as f:
        data = f.read()
    total_pages = len(data) // PAGE_SIZE
    result = bytearray()
    for pn in range(total_pages):
        page = data[pn * PAGE_SIZE:(pn + 1) * PAGE_SIZE]
        enc_start = 16 if pn == 0 else 0
        enc_size = PAGE_SIZE - RESERVE - enc_start
        iv = page[PAGE_SIZE - RESERVE:PAGE_SIZE - RESERVE + IV_SIZE]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = cipher.decrypt(page[enc_start:enc_start + enc_size])
        dp = bytearray(PAGE_SIZE)
        if pn == 0:
            dp[:16] = page[:16]
            dp[16:16 + len(dec)] = dec
        else:
            dp[:len(dec)] = dec
        result.extend(dp)
    result[:16] = b"SQLite format 3\x00"
    result[16:18] = struct.pack(">H", PAGE_SIZE)
    with open(out_path, "wb") as f:
        f.write(result)


def decrypt_databases(db_base, tmp_dir):
    """解密所有需要的数据库"""
    keys = load_keys()
    os.makedirs(tmp_dir, exist_ok=True)

    paths = {
        "message_0": os.path.join(db_base, "message", "message_0.db"),
        "contact": os.path.join(db_base, "contact", "contact.db"),
    }

    decrypted = {}
    for name, key_hex in keys.items():
        if name in paths and os.path.exists(paths[name]):
            out_path = os.path.join(tmp_dir, f"{name}.db")
            decrypt_db(paths[name], key_hex, out_path)
            decrypted[name] = out_path
            print(f"  ✓ 解密 {name}.db")

    return decrypted


# === 联系人解析 ===

def get_contact_map(db_path):
    db = sqlite3.connect(db_path)
    contacts = {}
    try:
        for row in db.execute("SELECT userName, remark, nick_name FROM contact"):
            contacts[row[0]] = row[1] or row[2] or row[0]
    except sqlite3.OperationalError:
        # Fallback: try alternative column names
        try:
            for row in db.execute("SELECT userName, nickName, remark FROM Contact"):
                contacts[row[0]] = row[2] or row[1] or row[0]
        except:
            pass
    db.close()
    return contacts


def get_hash_map(db_path):
    db = sqlite3.connect(db_path)
    mapping = {}
    try:
        for row in db.execute("SELECT user_name FROM Name2Id"):
            mapping[hashlib.md5(row[0].encode()).hexdigest()] = row[0]
    except sqlite3.OperationalError:
        pass
    db.close()
    return mapping


# === 消息解码 ===

def decode_content(content):
    """解码消息内容，处理 zstd 压缩"""
    if isinstance(content, bytes):
        if content[:4] == ZSTD_MAGIC:
            try:
                content = _zstd_decompressor.decompress(content, max_output_size=100000)
            except:
                return None
        try:
            content = content.decode("utf-8", errors="replace")
        except:
            return None
    if not content or len(content.strip()) == 0:
        return None
    return content.strip()


def parse_group_sender(content, contacts):
    """解析群聊消息的发送者"""
    if content and ':\n' in content:
        parts = content.split(':\n', 1)
        sender_id = parts[0]
        text = parts[1] if len(parts) > 1 else ""
        sender_name = contacts.get(sender_id, sender_id)
        return sender_id, sender_name, text
    return None, None, content


def detect_self_sender_id(db_path, contacts, hash_map):
    """Detect the sender id used for self messages in group chats."""
    db = sqlite3.connect(db_path)
    counter = {}

    tables = [t[0] for t in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
    ).fetchall()]

    for table in tables:
        hash_id = table.replace("Msg_", "")
        uname = hash_map.get(hash_id, hash_id)
        if "@chatroom" not in uname:
            continue

        try:
            rows = db.execute(
                f"SELECT real_sender_id, message_content FROM [{table}] "
                "WHERE local_type = 1 ORDER BY create_time DESC LIMIT 200"
            ).fetchall()
        except sqlite3.OperationalError:
            continue

        for real_sender_id, message_content in rows:
            decoded = decode_content(message_content)
            if not decoded or ":\n" in decoded:
                continue
            if real_sender_id in (None, 0) or real_sender_id in SYSTEM_SENDER_IDS:
                continue
            counter[real_sender_id] = counter.get(real_sender_id, 0) + 1

    db.close()

    if not counter:
        return SELF_SENDER_FALLBACK
    return max(counter.items(), key=lambda item: item[1])[0]


def infer_direction(local_type, real_sender_id, self_sender_id):
    if local_type == 10000 or real_sender_id in SYSTEM_SENDER_IDS:
        return None, "system"

    is_self = real_sender_id == self_sender_id if real_sender_id is not None else None
    if is_self is None:
        return None, "unknown"
    return is_self, "outbound" if is_self else "inbound"


def resolve_sender_info(uname, display, is_group, real_sender_id, local_type,
                        decoded_content, contacts, self_sender_id):
    is_self, direction = infer_direction(local_type, real_sender_id, self_sender_id)

    if is_group:
        if is_self:
            return SELF_SENDER_ID, SELF_SENDER_NAME, decoded_content, True, direction
        sender_id, sender_name, text = parse_group_sender(decoded_content, contacts)
        return sender_id or "unknown", sender_name or "unknown", text, False, direction

    if is_self:
        return SELF_SENDER_ID, SELF_SENDER_NAME, decoded_content, True, direction

    if direction == "system":
        return uname, display, decoded_content, None, direction

    return uname, display, decoded_content, False, direction


# === 消息导出 ===

def export_messages(db_path, contacts, hash_map, output_path,
                    start_ts=None, end_ts=None,
                    target_chats=None, target_contacts=None,
                    self_sender_id=SELF_SENDER_FALLBACK):
    """
    导出消息为 JSONL 格式

    每行 JSON:
    {
        "timestamp": 1712345678,
        "datetime": "2024-04-05 12:34:56",
        "chat_id": "xxx@chatroom",
        "chat_name": "群聊名称",
        "sender_id": "wxid_xxx",
        "sender_name": "昵称",
        "content": "消息内容",
        "msg_type": 1,
        "msg_type_label": "text",
        "is_group": true
    }
    """
    db = sqlite3.connect(db_path)

    # Get all message tables
    tables = [t[0] for t in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
    ).fetchall()]

    total_messages = 0
    total_text_messages = 0
    chat_stats = {}

    with open(output_path, "w", encoding="utf-8") as f:
        for t in tables:
            hash_id = t.replace("Msg_", "")
            uname = hash_map.get(hash_id, hash_id)
            display = contacts.get(uname, uname)
            is_group = "@chatroom" in uname

            # Skip if filtering by target chats/contacts
            if target_chats and is_group and display not in target_chats:
                continue
            if target_contacts and not is_group and display not in target_contacts:
                continue
            if (target_chats or target_contacts) and not target_chats and is_group:
                # If only contacts specified, skip groups
                continue
            if (target_chats or target_contacts) and not target_contacts and not is_group:
                # If only chats specified, skip contacts
                continue

            # Build query
            query = (
                f"SELECT create_time, local_type, real_sender_id, message_content, source "
                f"FROM [{t}]"
            )
            params = ()
            conditions = []

            if start_ts is not None:
                conditions.append("create_time >= ?")
                params += (start_ts,)
            if end_ts is not None:
                conditions.append("create_time <= ?")
                params += (end_ts,)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY create_time"

            try:
                rows = db.execute(query, params).fetchall()
            except:
                continue

            if not rows:
                continue

            chat_stats[display] = {"count": len(rows), "is_group": is_group}

            for ct, local_type, real_sender_id, content, source in rows:
                total_messages += 1

                msg_type_label = MSG_TYPE_LABELS.get(local_type, "other")
                decoded = decode_content(content)
                is_self, direction = infer_direction(local_type, real_sender_id, self_sender_id)

                # Build base record
                record = {
                    "timestamp": ct,
                    "datetime": datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M:%S"),
                    "chat_id": uname,
                    "chat_name": display,
                    "msg_type": local_type,
                    "msg_type_label": msg_type_label,
                    "is_group": is_group,
                    "real_sender_id": real_sender_id,
                    "is_self": is_self,
                    "direction": direction,
                }

                if local_type == 1 and decoded:
                    # Text message
                    total_text_messages += 1
                    sender_id, sender_name, text, _, _ = resolve_sender_info(
                        uname=uname,
                        display=display,
                        is_group=is_group,
                        real_sender_id=real_sender_id,
                        local_type=local_type,
                        decoded_content=decoded,
                        contacts=contacts,
                        self_sender_id=self_sender_id,
                    )
                    record["sender_id"] = sender_id
                    record["sender_name"] = sender_name
                    record["content"] = text
                elif decoded:
                    # Non-text with content
                    sender_id, sender_name, _, _, _ = resolve_sender_info(
                        uname=uname,
                        display=display,
                        is_group=is_group,
                        real_sender_id=real_sender_id,
                        local_type=local_type,
                        decoded_content=decoded,
                        contacts=contacts,
                        self_sender_id=self_sender_id,
                    )
                    record["sender_id"] = sender_id
                    record["sender_name"] = sender_name
                    record["content"] = f"[{msg_type_label}] {decoded[:100]}"
                else:
                    # Non-text without content
                    sender_id, sender_name, _, _, _ = resolve_sender_info(
                        uname=uname,
                        display=display,
                        is_group=is_group,
                        real_sender_id=real_sender_id,
                        local_type=local_type,
                        decoded_content="",
                        contacts=contacts,
                        self_sender_id=self_sender_id,
                    )
                    record["sender_id"] = sender_id
                    record["sender_name"] = sender_name
                    record["content"] = f"[{msg_type_label}]"

                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    db.close()

    return {
        "total_messages": total_messages,
        "total_text_messages": total_text_messages,
        "chat_count": len(chat_stats),
        "chat_stats": chat_stats,
    }


# === 列出群聊和联系人 ===

def list_all_chats(db_path, contacts, hash_map):
    db = sqlite3.connect(db_path)

    week_ago = int((datetime.now() - timedelta(days=7)).timestamp())
    tables = [t[0] for t in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
    ).fetchall()]

    groups = []
    contacts_list = []

    for t in tables:
        hash_id = t.replace("Msg_", "")
        uname = hash_map.get(hash_id, hash_id)
        display = contacts.get(uname, uname)
        is_group = "@chatroom" in uname

        try:
            count = db.execute(
                f"SELECT COUNT(*) FROM [{t}] WHERE create_time > ?", (week_ago,)
            ).fetchone()[0]
        except:
            count = 0

        entry = {"name": display, "id": uname, "msg_count_7d": count}
        if is_group:
            groups.append(entry)
        else:
            contacts_list.append(entry)

    db.close()

    groups.sort(key=lambda x: x["msg_count_7d"], reverse=True)
    contacts_list.sort(key=lambda x: x["msg_count_7d"], reverse=True)

    print("\n" + "=" * 60)
    print("群聊列表（最近7天消息数）")
    print("=" * 60)
    for i, g in enumerate(groups, 1):
        print(f"  {i}. {g['name']} — {g['msg_count_7d']}条")
    print(f"\n共 {len(groups)} 个群聊")

    print("\n" + "=" * 60)
    print("联系人列表（最近7天消息数，Top 50）")
    print("=" * 60)
    for i, c in enumerate(contacts_list[:50], 1):
        print(f"  {i}. {c['name']} — {c['msg_count_7d']}条")
    if len(contacts_list) > 50:
        print(f"  ... 还有 {len(contacts_list) - 50} 个联系人")
    print(f"\n共 {len(contacts_list)} 个联系人")

    return groups, contacts_list


# === 主入口 ===

def main(argv=None):
    parser = argparse.ArgumentParser(description="微信消息导出工具")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--output", "-o", help="输出目录", default=None)
    parser.add_argument("--days", "-d", type=int, help="导出最近 N 天的消息")
    parser.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--chats", help="指定群聊名称，逗号分隔")
    parser.add_argument("--contacts", help="指定联系人名称，逗号分隔")
    parser.add_argument("--list-chats", action="store_true", help="列出所有群聊和联系人")
    args = parser.parse_args(argv)

    # Load config
    config = load_config(args.config)
    db_base = get_db_base(config)
    if not db_base:
        return 1

    # Decrypt databases
    print("解密数据库...")
    decrypted = decrypt_databases(db_base, TMP_DIR)
    if "message_0" not in decrypted or "contact" not in decrypted:
        print("[ERROR] 未能解密必要的数据库")
        return 1

    contacts = get_contact_map(decrypted["contact"])
    hash_map = get_hash_map(decrypted["message_0"])
    self_sender_id = detect_self_sender_id(decrypted["message_0"], contacts, hash_map)
    print(f"检测到 self_sender_id: {self_sender_id}")

    # List mode
    if args.list_chats:
        list_all_chats(decrypted["message_0"], contacts, hash_map)
        return 0

    # Determine time range
    start_ts = None
    end_ts = None

    if args.days:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=args.days)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        print(f"时间范围: {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')}")
    elif args.start or args.end:
        if args.start:
            start_ts = int(datetime.strptime(args.start, "%Y-%m-%d").timestamp())
        if args.end:
            end_dt = datetime.strptime(args.end, "%Y-%m-%d") + timedelta(days=1)
            end_ts = int(end_dt.timestamp())
        print(f"时间范围: {args.start or '全部'} → {args.end or '全部'}")
    else:
        print("时间范围: 全部历史")

    # Determine target chats/contacts
    target_chats = None
    target_contacts = None
    if args.chats:
        target_chats = set(name.strip() for name in args.chats.split(","))
        print(f"指定群聊: {', '.join(target_chats)}")
    if args.contacts:
        target_contacts = set(name.strip() for name in args.contacts.split(","))
        print(f"指定联系人: {', '.join(target_contacts)}")

    # Determine output path
    output_dir = args.output or config.get("data_dir", os.path.expanduser("~/.wechat-insight/data"))
    os.makedirs(output_dir, exist_ok=True)

    # Build filename
    if start_ts and end_ts:
        filename = f"messages_{datetime.fromtimestamp(start_ts).strftime('%Y%m%d')}_{datetime.fromtimestamp(end_ts).strftime('%Y%m%d')}.jsonl"
    elif args.days:
        filename = f"messages_last{args.days}d.jsonl"
    else:
        filename = f"messages_all.jsonl"

    output_path = os.path.join(output_dir, filename)

    # Export
    print(f"\n导出消息到 {output_path}...")
    stats = export_messages(
        decrypted["message_0"], contacts, hash_map,
        output_path,
        start_ts=start_ts, end_ts=end_ts,
        target_chats=target_chats,
        target_contacts=target_contacts,
        self_sender_id=self_sender_id,
    )

    # Write metadata
    meta = {
        "export_time": datetime.now().isoformat(),
        "output_file": filename,
        "total_messages": stats["total_messages"],
        "total_text_messages": stats["total_text_messages"],
        "chat_count": stats["chat_count"],
        "time_range": {
            "start": datetime.fromtimestamp(start_ts).isoformat() if start_ts else None,
            "end": datetime.fromtimestamp(end_ts).isoformat() if end_ts else None,
        },
        "chat_stats": stats["chat_stats"],
    }
    meta_path = os.path.join(output_dir, "export_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "=" * 50)
    print("导出完成！")
    print("=" * 50)
    print(f"  文件: {output_path}")
    print(f"  总消息数: {stats['total_messages']}")
    print(f"  文本消息: {stats['total_text_messages']}")
    print(f"  涉及会话: {stats['chat_count']}")
    print(f"  元数据: {meta_path}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
