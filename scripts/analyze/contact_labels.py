#!/usr/bin/env python3
"""
联系人标签引导文件生成器

从导出消息中提取私聊联系人，生成可编辑的 contacts_labels.json。
"""

import argparse
import glob
import importlib.util
import json
import os
import pathlib
from collections import defaultdict


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_LABELS_PATH = os.path.expanduser("~/.config/wechat-insight-contacts_labels.json")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
FAMILY_HINTS = ["老婆", "老公", "妈妈", "爸爸", "弟弟", "妹妹", "儿子", "女儿"]
AD_HINTS = ["审批", "放款", "福利", "优惠", "助手", "经理", "银行", "贷款", "推广"]
VENDOR_HINTS = ["供应商", "服务商", "知识付费", "顾问", "合作方"]


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"data_dir": DEFAULT_DATA_DIR}


def load_message_rules_module():
    path = CURRENT_DIR.parent / "features" / "message_rules.py"
    spec = importlib.util.spec_from_file_location("message_rules", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MESSAGE_RULES = load_message_rules_module()


def find_latest_export_file(data_dir):
    pattern = os.path.join(os.path.expanduser(data_dir), "messages_*.jsonl")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (os.path.getmtime(path), path))


def resolve_input_files(input_path=None, config_path=None):
    config = load_config(config_path)

    if input_path:
        expanded = os.path.expanduser(input_path)
        matches = glob.glob(expanded)
        if matches:
            return sorted(matches)
        if os.path.exists(expanded):
            return [expanded]
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    latest = find_latest_export_file(config.get("data_dir", DEFAULT_DATA_DIR))
    if not latest:
        raise FileNotFoundError("未找到可分析的消息文件，请先执行 export")
    return [latest]


def load_messages(paths):
    messages = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    messages.sort(key=lambda item: item.get("timestamp", 0))
    return messages


def default_output_path(config_path=None):
    config = load_config(config_path)
    return os.path.expanduser(config.get("contacts_labels_path", DEFAULT_LABELS_PATH))


def load_existing_labels(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("contacts", {})


def infer_suggested_role(contact_name, stats):
    reasons = []
    if any(keyword in contact_name for keyword in FAMILY_HINTS):
        return "family", ["name_hint:family"]
    if any(keyword in contact_name for keyword in AD_HINTS):
        return "ad", ["name_hint:ad"]
    if any(keyword in contact_name for keyword in VENDOR_HINTS):
        return "vendor", ["name_hint:vendor"]
    if stats["quote_signal_count"] > 0 or stats["business_signal_count"] > 0:
        if stats["quote_signal_count"] > 0:
            reasons.append("quote_signal")
        if stats["business_signal_count"] > 0:
            reasons.append("business_signal")
        return "customer", reasons
    if stats["support_signal_count"] > 0:
        return "customer", ["support_signal"]
    return "unknown", []


def compute_review_priority_score(stats, suggested_role):
    score = 0
    if suggested_role == "customer":
        score += 40
    elif suggested_role == "vendor":
        score += 30
    elif suggested_role == "unknown":
        score += 5

    if suggested_role in {"family", "ad"}:
        score -= 10

    score += stats["quote_signal_count"] * 15
    score += stats["business_signal_count"] * 10
    score += stats["support_signal_count"] * 8
    score += stats["negative_signal_count"] * 3
    score += min(stats["inbound_messages"], 8)
    score += min(stats["total_messages"], 10)
    return score


def summarize_contact(contact_name, items, existing_entry=None):
    existing_entry = existing_entry or {}
    inbound_messages = sum(1 for item in items if item.get("direction") == "inbound")
    outbound_messages = sum(1 for item in items if item.get("direction") == "outbound")
    text_messages = [item for item in items if item.get("msg_type_label") == "text"]

    business_signal_count = 0
    quote_signal_count = 0
    support_signal_count = 0
    negative_signal_count = 0

    for message in text_messages:
        rule_result = MESSAGE_RULES.analyze_message_rules(message)
        business_signal_count += int(rule_result["is_business_signal"])
        quote_signal_count += int(rule_result["is_quote_signal"])
        support_signal_count += int(rule_result["is_support_signal"])
        negative_signal_count += int(rule_result["is_negative_signal"])

    stats = {
        "total_messages": len(items),
        "inbound_messages": inbound_messages,
        "outbound_messages": outbound_messages,
        "last_message_at": items[-1].get("datetime"),
        "business_signal_count": business_signal_count,
        "quote_signal_count": quote_signal_count,
        "support_signal_count": support_signal_count,
        "negative_signal_count": negative_signal_count,
    }
    suggested_role, suggested_role_reason = infer_suggested_role(contact_name, stats)

    entry = dict(existing_entry)
    entry["role"] = existing_entry.get("role", "unknown")
    entry["suggested_role"] = suggested_role
    entry["suggested_role_reason"] = suggested_role_reason
    entry["notes"] = existing_entry.get("notes", "")
    entry["review_priority_score"] = compute_review_priority_score(stats, suggested_role)
    entry.update(stats)
    return entry


def apply_role_suggestion(entry):
    role = entry.get("role", "unknown")
    suggested_role = entry.get("suggested_role", "unknown")
    if role not in {"", "unknown", None}:
        return False
    if suggested_role in {"", "unknown", None}:
        return False
    entry["role"] = suggested_role
    return True


def build_contacts_payload(messages, existing_contacts=None, limit=None, apply_suggestions=False):
    grouped = defaultdict(list)
    for message in messages:
        if message.get("is_group"):
            continue
        grouped[message.get("chat_name", "未知联系人")].append(message)

    existing_contacts = existing_contacts or {}
    summarized_contacts = []
    for contact_name, items in grouped.items():
        entry = summarize_contact(
            contact_name,
            items,
            existing_entry=existing_contacts.get(contact_name),
        )
        summarized_contacts.append((contact_name, entry))

    summarized_contacts.sort(
        key=lambda item: (
            -item[1]["review_priority_score"],
            -item[1]["total_messages"],
            item[0],
        ),
    )
    if limit is not None:
        summarized_contacts = summarized_contacts[:limit]

    contacts_payload = {}
    applied_suggestions = 0
    for contact_name, entry in summarized_contacts:
        if apply_suggestions and apply_role_suggestion(entry):
            applied_suggestions += 1
        contacts_payload[contact_name] = entry
    return contacts_payload, applied_suggestions


def bootstrap_contact_labels(input_path=None, output_file=None, config_path=None, limit=None,
                             apply_suggestions=False):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    resolved_output = os.path.expanduser(output_file or default_output_path(config_path))
    existing_contacts = load_existing_labels(resolved_output)
    contacts_payload, applied_suggestions = build_contacts_payload(
        messages,
        existing_contacts=existing_contacts,
        limit=limit,
        apply_suggestions=apply_suggestions,
    )

    output_dir = os.path.dirname(resolved_output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    payload = {"contacts": contacts_payload}
    with open(resolved_output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return {
        "input_files": paths,
        "output_path": resolved_output,
        "total_private_contacts": len({m.get('chat_name', '未知联系人') for m in messages if not m.get('is_group')}),
        "generated_contacts": len(contacts_payload),
        "applied_suggestions": applied_suggestions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成联系人标签引导文件")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出标签文件路径")
    parser.add_argument("--limit", type=int, help="只生成最活跃的前 N 个联系人")
    parser.add_argument("--apply-suggestions", action="store_true", help="将 suggested_role 自动写入空白 role")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = bootstrap_contact_labels(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        limit=args.limit,
        apply_suggestions=args.apply_suggestions,
    )

    print("=" * 50)
    print("联系人标签引导文件")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"输出路径: {result['output_path']}")
    print(f"私聊联系人: {result['total_private_contacts']}")
    print(f"生成联系人: {result['generated_contacts']}")
    print(f"自动应用建议: {result['applied_suggestions']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
