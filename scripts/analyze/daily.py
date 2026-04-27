#!/usr/bin/env python3
"""
微信聊天日报分析器

基于已导出的 JSONL 消息文件生成 Markdown 日报。
"""

import argparse
import glob
import importlib.util
import json
import os
import pathlib
from collections import Counter, defaultdict
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_REPORT_DIR = os.path.expanduser("~/.wechat-insight/reports")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "data_dir": DEFAULT_DATA_DIR,
        "report_dir": DEFAULT_REPORT_DIR,
    }


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
                if not line:
                    continue
                messages.append(json.loads(line))
    messages.sort(key=lambda item: item.get("timestamp", 0))
    return messages


def get_repeated_phrases(messages, limit=5):
    phrases = Counter()
    for message in messages:
        content = (message.get("content") or "").strip()
        if (
            message.get("msg_type_label") == "text"
            and 2 <= len(content) <= 20
            and not content.startswith("[")
        ):
            phrases[content] += 1

    return [
        (text, count)
        for text, count in phrases.most_common(limit)
        if count >= 2
    ]


def build_direction_counts(messages):
    direction_counter = Counter(
        (message.get("direction") or "unknown")
        for message in messages
    )
    return {
        "self_messages": sum(1 for message in messages if message.get("is_self") is True),
        "inbound_messages": direction_counter["inbound"],
        "outbound_messages": direction_counter["outbound"],
        "system_messages": direction_counter["system"],
        "unknown_direction_messages": direction_counter["unknown"],
    }


def build_direction_breakdown(messages, include_groups=None):
    grouped = defaultdict(list)
    for message in messages:
        is_group = bool(message.get("is_group"))
        if include_groups is None or is_group == include_groups:
            grouped[message.get("chat_name", "未知会话")].append(message)
    return {
        name: build_direction_counts(items)
        for name, items in grouped.items()
    }


def format_ratio(count, total):
    if not total:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def build_followup_labels(rule_result):
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


def build_followup_priority(rule_result):
    score = 0
    if rule_result.get("is_support_signal"):
        score += 50
    if rule_result.get("is_quote_signal") or rule_result.get("is_business_signal"):
        score += 40
    if rule_result.get("is_action_item"):
        score += 30
    if rule_result.get("is_schedule"):
        score += 20
    if rule_result.get("is_question"):
        score += 10
    if rule_result.get("is_negative_signal"):
        score += 15
    return score


def clip_text(text, limit=36):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def extract_pending_followups(messages):
    last_outbound_ts_by_chat = {}
    pending_by_chat = {}

    for message in messages:
        chat_name = message.get("chat_name", "未知会话")
        timestamp = message.get("timestamp") or 0
        direction = message.get("direction")

        if direction == "outbound":
            last_outbound_ts_by_chat[chat_name] = timestamp
            existing = pending_by_chat.get(chat_name)
            if existing and existing["timestamp"] < timestamp:
                pending_by_chat.pop(chat_name, None)
            continue

        if direction != "inbound" or message.get("msg_type_label") != "text":
            continue

        rule_result = MESSAGE_RULES.analyze_message_rules(message)
        labels = build_followup_labels(rule_result)
        if not labels:
            continue
        if last_outbound_ts_by_chat.get(chat_name, -1) >= timestamp:
            continue

        pending_by_chat[chat_name] = {
            "chat_name": chat_name,
            "timestamp": timestamp,
            "datetime": message.get("datetime"),
            "content": message.get("content", ""),
            "labels": labels,
            "priority": build_followup_priority(rule_result),
            "is_group": bool(message.get("is_group")),
        }

    return sorted(
        pending_by_chat.values(),
        key=lambda item: (item["priority"], item["timestamp"]),
        reverse=True,
    )


def build_stats(messages):
    if not messages:
        raise ValueError("输入消息为空，无法生成日报")

    text_messages = [m for m in messages if m.get("msg_type_label") == "text"]
    chat_counter = Counter(m.get("chat_name", "未知会话") for m in messages)
    contact_counter = Counter(
        m.get("chat_name", "未知联系人") for m in messages if not m.get("is_group")
    )
    hour_counter = Counter(
        datetime.fromtimestamp(m["timestamp"]).strftime("%H")
        for m in messages
        if m.get("timestamp") is not None
    )

    group_messages = sum(1 for m in messages if m.get("is_group"))
    private_messages = len(messages) - group_messages
    night_messages = sum(
        1
        for m in messages
        if m.get("timestamp") is not None
        and datetime.fromtimestamp(m["timestamp"]).hour < 6
    )

    start_dt = datetime.fromtimestamp(messages[0]["timestamp"])
    end_dt = datetime.fromtimestamp(messages[-1]["timestamp"])
    top_chat_name, top_chat_count = chat_counter.most_common(1)[0]
    top_hour, top_hour_count = hour_counter.most_common(1)[0]

    top_contact = contact_counter.most_common(1)
    top_contact_name, top_contact_count = top_contact[0] if top_contact else ("无", 0)

    repeated_phrases = get_repeated_phrases(messages)
    repeated_phrase_text = (
        f"{repeated_phrases[0][0]}（{repeated_phrases[0][1]}次）"
        if repeated_phrases else "无明显重复短句"
    )
    has_direction_metrics = any(message.get("direction") for message in messages)
    direction_counts = build_direction_counts(messages)
    summary_lines = [
        f"今天共记录 {len(messages)} 条消息，主要集中在 {top_hour}时（{top_hour_count}条）。",
        f"最活跃会话是 {top_chat_name}（{top_chat_count}条），最活跃联系人是 {top_contact_name}（{top_contact_count}条）。",
        f"高频短句：{repeated_phrase_text}。",
    ]

    if has_direction_metrics:
        summary_lines.append(
            "互动结构上，"
            f"主动发出 {direction_counts['outbound_messages']} 条（{format_ratio(direction_counts['outbound_messages'], len(messages))}），"
            f"收到 {direction_counts['inbound_messages']} 条（{format_ratio(direction_counts['inbound_messages'], len(messages))}），"
            f"系统消息 {direction_counts['system_messages']} 条（{format_ratio(direction_counts['system_messages'], len(messages))}）。"
        )
    pending_followups = extract_pending_followups(messages)
    if pending_followups:
        summary_lines.append(
            f"当前有 {len(pending_followups)} 个待跟进会话，优先关注 {pending_followups[0]['chat_name']}。"
        )

    return {
        "start_dt": start_dt,
        "end_dt": end_dt,
        "total_messages": len(messages),
        "text_messages": len(text_messages),
        "chat_count": len(chat_counter),
        "group_messages": group_messages,
        "private_messages": private_messages,
        "night_messages": night_messages,
        "top_chats": chat_counter.most_common(5),
        "top_contacts": contact_counter.most_common(5),
        "top_hours": hour_counter.most_common(5),
        "repeated_phrases": repeated_phrases,
        "summary_lines": summary_lines,
        "has_direction_metrics": has_direction_metrics,
        "chat_direction_breakdown": build_direction_breakdown(messages, include_groups=None),
        "contact_direction_breakdown": build_direction_breakdown(messages, include_groups=False),
        "pending_followups": pending_followups,
        **direction_counts,
    }


def render_rank_lines(items, suffix):
    if not items:
        return ["- 暂无数据"]
    return [f"- {name}（{count}{suffix}）" for name, count in items]


def render_direction_rank_lines(items, breakdowns, suffix):
    if not items:
        return ["- 暂无数据"]
    lines = []
    for name, count in items:
        metrics = breakdowns.get(name)
        if not metrics:
            lines.append(f"- {name}（{count}{suffix}）")
            continue
        lines.append(
            f"- {name}（{count}{suffix}，"
            f"发出 {metrics['outbound_messages']} / "
            f"收到 {metrics['inbound_messages']} / "
            f"系统 {metrics['system_messages']}）"
        )
    return lines


def render_pending_followup_lines(items):
    if not items:
        return ["- 暂无明显待跟进会话"]
    lines = [f"- 待跟进会话数：{len(items)}"]
    for item in items[:5]:
        lines.append(
            f"- {item['chat_name']}：{clip_text(item['content'])}"
            f"（{' / '.join(item['labels'])}，{item['datetime']}）"
        )
    return lines


def render_daily_report(stats):
    date_label = (
        stats["start_dt"].strftime("%Y-%m-%d")
        if stats["start_dt"].date() == stats["end_dt"].date()
        else (
            f"{stats['start_dt'].strftime('%Y-%m-%d')} ~ "
            f"{stats['end_dt'].strftime('%Y-%m-%d')}"
        )
    )

    lines = [
        "# 微信聊天日报",
        "",
        f"- 日期：{date_label}",
        f"- 统计范围：{stats['start_dt'].strftime('%Y-%m-%d %H:%M:%S')} ~ {stats['end_dt'].strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总消息数：{stats['total_messages']}",
        f"- 文本消息：{stats['text_messages']}",
        f"- 活跃会话：{stats['chat_count']}",
        f"- 群聊消息：{stats['group_messages']}",
        f"- 私聊消息：{stats['private_messages']}",
        f"- 深夜消息：{stats['night_messages']}",
        "",
        "## 今日摘要",
    ]
    lines.extend(f"- {line}" for line in stats["summary_lines"])
    if stats.get("has_direction_metrics"):
        lines.extend([
            "",
            "## 互动结构",
            f"- 主动发出：{stats['outbound_messages']}条（{format_ratio(stats['outbound_messages'], stats['total_messages'])}）",
            f"- 收到消息：{stats['inbound_messages']}条（{format_ratio(stats['inbound_messages'], stats['total_messages'])}）",
            f"- 系统消息：{stats['system_messages']}条（{format_ratio(stats['system_messages'], stats['total_messages'])}）",
            f"- 未知方向：{stats['unknown_direction_messages']}条（{format_ratio(stats['unknown_direction_messages'], stats['total_messages'])}）",
        ])
    lines.extend([
        "",
        "## 最活跃会话 Top 5",
    ])
    if stats.get("has_direction_metrics"):
        lines.extend(render_direction_rank_lines(
            stats["top_chats"],
            stats["chat_direction_breakdown"],
            "条",
        ))
    else:
        lines.extend(render_rank_lines(stats["top_chats"], "条"))
    lines.extend([
        "",
        "## 最活跃联系人 Top 5",
    ])
    if stats.get("has_direction_metrics"):
        lines.extend(render_direction_rank_lines(
            stats["top_contacts"],
            stats["contact_direction_breakdown"],
            "条",
        ))
    else:
        lines.extend(render_rank_lines(stats["top_contacts"], "条"))
    lines.extend([
        "",
        "## 活跃时段 Top 5",
    ])
    lines.extend(render_rank_lines(
        [(f"{hour}时", count) for hour, count in stats["top_hours"]],
        "条",
    ))
    lines.extend([
        "",
        "## 高频短句",
    ])
    lines.extend(render_rank_lines(stats["repeated_phrases"], "次"))
    lines.extend([
        "",
        "## 待跟进信号",
    ])
    lines.extend(render_pending_followup_lines(stats["pending_followups"]))
    lines.append("")
    return "\n".join(lines)


def build_default_output_path(stats, config_path=None):
    config = load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)

    if stats["start_dt"].date() == stats["end_dt"].date():
        filename = f"daily_{stats['start_dt'].strftime('%Y%m%d')}.md"
    else:
        filename = (
            f"daily_{stats['start_dt'].strftime('%Y%m%d')}_"
            f"{stats['end_dt'].strftime('%Y%m%d')}.md"
        )
    return os.path.join(report_dir, filename)


def analyze_daily(input_path=None, output_file=None, config_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    stats = build_stats(messages)
    report_markdown = render_daily_report(stats)

    report_path = os.path.expanduser(output_file) if output_file else build_default_output_path(
        stats, config_path=config_path
    )
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="微信聊天日报")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_daily(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
    )

    print("=" * 50)
    print("微信聊天日报")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"报告路径: {result['report_path']}")
    print(f"总消息数: {result['total_messages']}")
    print(f"最活跃会话: {result['top_chats'][0][0]}（{result['top_chats'][0][1]}条）")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
