#!/usr/bin/env python3
"""
未回复会话清单

基于已导出的 JSONL 消息文件，列出"最后一条是对方发来、你还没回"的会话。
与 daily 的"待跟进信号"不同，这里不依赖关键词，只看会话的最后一条消息方向，
因此能回答"有没有谁的消息我漏回了"。
"""

import argparse
import glob
import importlib.util
import json
import os
import pathlib
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_LABELS_PATH = os.path.expanduser("~/.config/wechat-insight-contacts_labels.json")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
DAY_SECONDS = 86400


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"data_dir": DEFAULT_DATA_DIR}


def load_contact_labels(labels_path=None, config_path=None):
    config = load_config(config_path)
    candidate = os.path.expanduser(
        labels_path
        or config.get("contacts_labels_path")
        or DEFAULT_LABELS_PATH
    )
    if not os.path.exists(candidate):
        return {}, candidate
    with open(candidate, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("contacts", {}), candidate


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


def clip_text(text, limit=40):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def build_context_labels(message):
    """给最后一条 inbound 消息打上规则标签，作为上下文提示（不作为过滤条件）。"""
    rule_result = MESSAGE_RULES.analyze_message_rules(message)
    labels = []
    if rule_result.get("is_support_signal"):
        labels.append("售后")
    if rule_result.get("is_quote_signal") or rule_result.get("is_business_signal"):
        labels.append("商业")
    if rule_result.get("is_action_item"):
        labels.append("待办")
    if rule_result.get("is_schedule"):
        labels.append("排期")
    if rule_result.get("is_question"):
        labels.append("问题")
    if rule_result.get("is_negative_signal"):
        labels.append("负面")
    return labels


def find_unreplied(
    messages,
    days=None,
    include_groups=False,
    contact_labels=None,
):
    """找出最后一条消息为 inbound（对方发来、你没回）的会话。

    "最后一条"基于完整历史判定（只看 inbound/outbound，忽略 system），
    这样你最后回过的会话不会被误报。--days 只用来过滤掉太久以前的未回复。
    每项会带上 labels 里的 role，广告过滤交给上层处理。
    """
    contact_labels = contact_labels or {}

    last_by_chat = {}
    for message in messages:
        direction = message.get("direction")
        if direction not in ("inbound", "outbound"):
            continue
        if not include_groups and message.get("is_group"):
            continue
        chat_name = message.get("chat_name", "未知会话")
        timestamp = message.get("timestamp") or 0
        existing = last_by_chat.get(chat_name)
        if existing is None or timestamp >= existing.get("timestamp", 0):
            last_by_chat[chat_name] = message

    if not last_by_chat:
        return []

    cutoff = None
    if days is not None:
        latest_ts = max(
            (msg.get("timestamp") or 0) for msg in last_by_chat.values()
        )
        cutoff = latest_ts - days * DAY_SECONDS

    results = []
    for chat_name, message in last_by_chat.items():
        if message.get("direction") != "inbound":
            continue
        timestamp = message.get("timestamp") or 0
        if cutoff is not None and timestamp < cutoff:
            continue

        role = (contact_labels.get(chat_name, {}) or {}).get("role", "unknown")
        results.append(
            {
                "chat_name": chat_name,
                "timestamp": timestamp,
                "datetime": message.get("datetime"),
                "content": message.get("content", ""),
                "msg_type_label": message.get("msg_type_label"),
                "is_group": bool(message.get("is_group")),
                "role": role,
                "context_labels": build_context_labels(message),
            }
        )

    results.sort(key=lambda item: item["timestamp"], reverse=True)
    return results


def render_unreplied_report(result):
    items = result["items"]
    lines = ["# 未回复会话", ""]
    lines.append(f"- 输入文件：{', '.join(result['input_files'])}")
    if result.get("days") is not None:
        lines.append(f"- 时间窗口：最近 {result['days']} 天")
    if result.get("exclude_ad"):
        lines.append(f"- 已过滤广告号：{result['skipped_ad']} 个")
    lines.append(f"- 未回复会话数：{len(items)}")
    lines.append("")

    if not items:
        lines.append("暂无未回复会话，全部消息都已回复。")
        return "\n".join(lines)

    for item in items:
        tags = "".join(f"[{label}]" for label in item["context_labels"])
        group_flag = "（群）" if item["is_group"] else ""
        role = item["role"]
        role_flag = f"（{role}）" if role and role != "unknown" else ""
        when = item.get("datetime") or ""
        content = clip_text(item.get("content"))
        lines.append(
            f"- {item['chat_name']}{group_flag}{role_flag} {tags} {when}：{content}".rstrip()
        )
    return "\n".join(lines)


def analyze_unreplied(
    input_path=None,
    days=None,
    include_groups=False,
    config_path=None,
    labels_path=None,
    exclude_ad=False,
    output_file=None,
):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    contact_labels, resolved_labels_path = load_contact_labels(
        labels_path=labels_path,
        config_path=config_path,
    )
    all_items = find_unreplied(
        messages,
        days=days,
        include_groups=include_groups,
        contact_labels=contact_labels,
    )
    if exclude_ad:
        items = [item for item in all_items if item["role"] != "ad"]
        skipped_ad = len(all_items) - len(items)
    else:
        items = all_items
        skipped_ad = 0

    result = {
        "items": items,
        "input_files": paths,
        "labels_path": resolved_labels_path,
        "days": days,
        "include_groups": include_groups,
        "exclude_ad": exclude_ad,
        "skipped_ad": skipped_ad,
    }
    report_markdown = render_unreplied_report(result)
    result["report_markdown"] = report_markdown

    if output_file:
        report_path = os.path.expanduser(output_file)
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        result["report_path"] = report_path

    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="列出最后一条是对方发来、你还没回的会话")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--days", type=int, default=None, help="只看最近 N 天内的未回复会话")
    parser.add_argument(
        "--include-groups",
        action="store_true",
        help="同时纳入群聊（默认只看私聊）",
    )
    parser.add_argument(
        "--exclude-ad",
        action="store_true",
        help="过滤掉 labels 中 role 为 ad 的广告/营销号",
    )
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--output", "-o", help="可选：将清单写入 Markdown 文件")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_unreplied(
        input_path=args.input,
        days=args.days,
        include_groups=args.include_groups,
        config_path=args.config,
        labels_path=args.labels,
        exclude_ad=args.exclude_ad,
        output_file=args.output,
    )

    print(result["report_markdown"])
    if result.get("report_path"):
        print(f"\n已写入：{result['report_path']}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
