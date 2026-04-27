#!/usr/bin/env python3
"""Build enriched features from exported WeChat messages JSONL."""

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import pathlib
import re
from collections import Counter, defaultdict
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_FEATURE_DIR = os.path.expanduser("~/.wechat-insight/features")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent


def load_message_rules_module():
    path = CURRENT_DIR / "message_rules.py"
    spec = importlib.util.spec_from_file_location("message_rules", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MESSAGE_RULES = load_message_rules_module()


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "data_dir": DEFAULT_DATA_DIR,
        "feature_dir": DEFAULT_FEATURE_DIR,
    }


def find_latest_export_file(data_dir):
    pattern = os.path.join(os.path.expanduser(data_dir), "messages_*.jsonl")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (os.path.getmtime(path), path))


def resolve_input_paths(input_paths=None, config_path=None):
    config = load_config(config_path)
    if input_paths:
        resolved = []
        for input_path in input_paths:
            expanded = os.path.expanduser(input_path)
            matches = glob.glob(expanded)
            if matches:
                resolved.extend(sorted(matches))
            elif os.path.exists(expanded):
                resolved.append(expanded)
            else:
                raise FileNotFoundError(f"未找到输入文件: {input_path}")
        return resolved

    latest = find_latest_export_file(config.get("data_dir", DEFAULT_DATA_DIR))
    if not latest:
        raise FileNotFoundError("未找到可分析的消息文件，请先执行 export")
    return [latest]


def load_messages(paths):
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    rows.sort(key=lambda item: item.get("timestamp", 0))
    return rows


def normalize_content(content):
    text = (content or "").replace("\u3000", " ").replace("\n", " ")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[!！]{2,}", "！", text)
    text = re.sub(r"[?？]{2,}", "？", text)
    return text.strip()


def build_message_id(message):
    payload = "|".join([
        str(message.get("chat_id", "")),
        str(message.get("timestamp", "")),
        str(message.get("sender_id", "")),
        str(message.get("msg_type", "")),
        str(message.get("content", "")),
    ])
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def enrich_message(message):
    enriched = dict(message)
    timestamp = enriched.get("timestamp")
    dt = datetime.fromtimestamp(timestamp) if timestamp is not None else None
    content_clean = normalize_content(enriched.get("content"))
    rule_result = MESSAGE_RULES.analyze_message_rules(enriched)

    if dt is not None:
        enriched["date"] = dt.strftime("%Y-%m-%d")
        enriched["hour"] = dt.hour
        enriched["weekday"] = dt.weekday()
    else:
        enriched["date"] = None
        enriched["hour"] = None
        enriched["weekday"] = None

    enriched["message_id"] = build_message_id(enriched)
    enriched["chat_type"] = "group" if enriched.get("is_group") else "private"
    enriched["content_clean"] = content_clean
    enriched["content_length"] = len(content_clean)
    enriched["has_question"] = "？" in content_clean or "?" in content_clean
    enriched["has_exclamation"] = "！" in content_clean or "!" in content_clean
    enriched["has_link"] = "http://" in (enriched.get("content") or "") or "https://" in (enriched.get("content") or "")
    enriched["emoji_count"] = 0
    enriched["is_self"] = message.get("is_self")
    enriched["direction"] = (
        message.get("direction")
        or ("system" if enriched.get("msg_type_label") == "system" else "unknown")
    )
    enriched.update(rule_result)
    return enriched


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_direction_metrics(items):
    total = len(items)
    self_messages = sum(1 for item in items if item.get("is_self") is True)
    inbound_messages = sum(1 for item in items if item.get("direction") == "inbound")
    outbound_messages = sum(1 for item in items if item.get("direction") == "outbound")
    system_messages = sum(1 for item in items if item.get("direction") == "system")
    unknown_direction_messages = sum(
        1
        for item in items
        if item.get("direction") not in {"inbound", "outbound", "system"}
    )
    return {
        "self_messages": self_messages,
        "inbound_messages": inbound_messages,
        "outbound_messages": outbound_messages,
        "system_messages": system_messages,
        "unknown_direction_messages": unknown_direction_messages,
        "self_ratio": round(self_messages / total, 4) if total else 0.0,
        "inbound_ratio": round(inbound_messages / total, 4) if total else 0.0,
        "outbound_ratio": round(outbound_messages / total, 4) if total else 0.0,
    }


def aggregate_daily(messages):
    grouped = defaultdict(list)
    for message in messages:
        grouped[message.get("date")].append(message)

    rows = []
    for date in sorted(grouped):
        items = grouped[date]
        hour_counter = Counter(item.get("hour") for item in items if item.get("hour") is not None)
        chat_counter = Counter(item.get("chat_name", "未知会话") for item in items)
        private_chats = {item.get("chat_id") for item in items if not item.get("is_group")}
        row = {
            "date": date,
            "total_messages": len(items),
            "text_messages": sum(1 for item in items if item.get("msg_type_label") == "text"),
            "group_messages": sum(1 for item in items if item.get("is_group")),
            "private_messages": sum(1 for item in items if not item.get("is_group")),
            "active_chats": len({item.get("chat_id") for item in items}),
            "active_contacts": len(private_chats),
            "night_messages": sum(1 for item in items if (item.get("hour") or 0) < 6),
            "peak_hour": hour_counter.most_common(1)[0][0] if hour_counter else None,
            "top_chat": chat_counter.most_common(1)[0][0] if chat_counter else None,
            "business_signal_count": sum(1 for item in items if item.get("is_business_signal")),
            "support_signal_count": sum(1 for item in items if item.get("is_support_signal")),
            "action_signal_count": sum(1 for item in items if item.get("is_action_item")),
        }
        row.update(build_direction_metrics(items))
        rows.append(row)
    return rows


def aggregate_chat(messages):
    grouped = defaultdict(list)
    for message in messages:
        grouped[(message.get("chat_id"), message.get("chat_name"))].append(message)

    rows = []
    for key in sorted(grouped, key=lambda item: (item[1] or "", item[0] or "")):
        items = grouped[key]
        chat_id, chat_name = key
        total = len(items)
        row = {
            "chat_id": chat_id,
            "chat_name": chat_name,
            "chat_type": items[0].get("chat_type"),
            "total_messages": total,
            "text_messages": sum(1 for item in items if item.get("msg_type_label") == "text"),
            "active_days": len({item.get("date") for item in items}),
            "last_active_at": max(item.get("datetime") for item in items if item.get("datetime")),
            "question_ratio": round(sum(1 for item in items if item.get("is_question")) / total, 4),
            "action_signal_count": sum(1 for item in items if item.get("is_action_item")),
            "business_signal_count": sum(1 for item in items if item.get("is_business_signal")),
            "support_signal_count": sum(1 for item in items if item.get("is_support_signal")),
            "avg_message_length": round(sum(item.get("content_length", 0) for item in items) / total, 2),
        }
        row.update(build_direction_metrics(items))
        rows.append(row)
    return rows


def aggregate_contact(messages):
    grouped = defaultdict(list)
    for message in messages:
        if not message.get("is_group"):
            grouped[(message.get("chat_id"), message.get("chat_name"))].append(message)

    rows = []
    for key in sorted(grouped, key=lambda item: (item[1] or "", item[0] or "")):
        items = grouped[key]
        contact_id, contact_name = key
        total = len(items)
        row = {
            "contact_id": contact_id,
            "contact_name": contact_name,
            "role": "unknown",
            "stage": "unknown",
            "total_messages": total,
            "active_days": len({item.get("date") for item in items}),
            "question_ratio": round(sum(1 for item in items if item.get("is_question")) / total, 4),
            "action_signal_count": sum(1 for item in items if item.get("is_action_item")),
            "business_signal_count": sum(1 for item in items if item.get("is_business_signal")),
            "quote_signal_count": sum(1 for item in items if item.get("is_quote_signal")),
            "support_signal_count": sum(1 for item in items if item.get("is_support_signal")),
            "negative_signal_count": sum(1 for item in items if item.get("is_negative_signal")),
        }
        row.update(build_direction_metrics(items))
        rows.append(row)
    return rows


def build_output_paths(input_paths, output_dir):
    base_names = []
    for path in input_paths:
        name = pathlib.Path(path).stem
        if name.startswith("messages_"):
            base_names.append(name[len("messages_"):])
        else:
            base_names.append(name)
    suffix = "__".join(base_names) if base_names else "latest"
    return {
        "messages_enriched": os.path.join(output_dir, f"messages_enriched_{suffix}.jsonl"),
        "daily_features": os.path.join(output_dir, f"daily_features_{suffix}.jsonl"),
        "chat_features": os.path.join(output_dir, f"chat_features_{suffix}.jsonl"),
        "contact_features": os.path.join(output_dir, f"contact_features_{suffix}.jsonl"),
    }


def build_features(input_paths=None, output_dir=None, config_path=None):
    resolved_input_paths = resolve_input_paths(input_paths=input_paths, config_path=config_path)
    config = load_config(config_path)
    resolved_output_dir = os.path.expanduser(
        output_dir or config.get("feature_dir", DEFAULT_FEATURE_DIR)
    )
    os.makedirs(resolved_output_dir, exist_ok=True)

    messages = load_messages(resolved_input_paths)
    enriched_messages = [enrich_message(message) for message in messages]

    output_paths = build_output_paths(resolved_input_paths, resolved_output_dir)
    write_jsonl(output_paths["messages_enriched"], enriched_messages)
    write_jsonl(output_paths["daily_features"], aggregate_daily(enriched_messages))
    write_jsonl(output_paths["chat_features"], aggregate_chat(enriched_messages))
    write_jsonl(output_paths["contact_features"], aggregate_contact(enriched_messages))

    return {
        "input_files": resolved_input_paths,
        "output_dir": resolved_output_dir,
        **output_paths,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成 WeChat Insight features 层")
    parser.add_argument(
        "--input",
        "-i",
        action="append",
        help="输入 JSONL 文件路径或 glob，可重复传入；默认取最新导出文件",
    )
    parser.add_argument("--output-dir", "-o", help="输出目录")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = build_features(
        input_paths=args.input,
        output_dir=args.output_dir,
        config_path=args.config,
    )

    print("=" * 50)
    print("WeChat Insight Features")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"输出目录: {result['output_dir']}")
    print(f"enriched: {result['messages_enriched']}")
    print(f"daily: {result['daily_features']}")
    print(f"chat: {result['chat_features']}")
    print(f"contact: {result['contact_features']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
