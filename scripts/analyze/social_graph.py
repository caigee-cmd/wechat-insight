#!/usr/bin/env python3
"""Social graph and temporal profile analysis for WeChat Insight."""

import argparse
import pathlib
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime


CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from common import build_date_ranged_output_path, build_persona_modes, load_messages, resolve_input_files, write_text


def build_social_stats(messages, include_persona_modes=True):
    if not messages:
        raise ValueError("输入消息为空，无法生成社交图谱")

    chat_counter = Counter()
    hour_counter = Counter()
    daily_activity = defaultdict(int)
    pending_inbound_by_chat = {}
    response_latency_minutes = []
    group_message_count = 0
    private_message_count = 0
    night_message_count = 0

    for message in messages:
        chat_name = message.get("chat_name", "未知会话")
        timestamp = message.get("timestamp") or 0
        dt = datetime.fromtimestamp(timestamp) if timestamp else None
        is_group = bool(message.get("is_group"))
        direction = message.get("direction")

        chat_counter[chat_name] += 1
        if dt:
            hour_counter[f"{dt.hour:02d}"] += 1
            daily_activity[dt.strftime("%Y-%m-%d")] += 1
            if dt.hour < 6:
                night_message_count += 1

        if is_group:
            group_message_count += 1
            continue

        private_message_count += 1
        if direction == "inbound" and not message.get("is_self"):
            pending_inbound_by_chat[chat_name] = timestamp
            continue

        if direction == "outbound" or message.get("is_self") is True:
            inbound_ts = pending_inbound_by_chat.get(chat_name)
            if inbound_ts and timestamp > inbound_ts:
                latency_seconds = timestamp - inbound_ts
                if 30 <= latency_seconds <= 12 * 3600:
                    response_latency_minutes.append(round(latency_seconds / 60, 2))
                pending_inbound_by_chat.pop(chat_name, None)

    median_latency = statistics.median(response_latency_minutes) if response_latency_minutes else None
    if isinstance(median_latency, float) and median_latency.is_integer():
        median_latency = int(median_latency)

    top_chats = sorted(chat_counter.items(), key=lambda item: (-item[1], item[0]))[:12]
    top_hours = sorted(hour_counter.items(), key=lambda item: (-item[1], item[0]))[:12]
    daily_rows = [
        {"date": date, "total_messages": count}
        for date, count in sorted(daily_activity.items())
    ]

    result = {
        "group_message_count": group_message_count,
        "private_message_count": private_message_count,
        "night_message_ratio": round(night_message_count / len(messages), 4) if messages else 0,
        "response_latency_minutes": response_latency_minutes,
        "median_response_latency_minutes": median_latency,
        "top_chats": top_chats,
        "top_hours": top_hours,
        "daily_activity": daily_rows,
    }
    if include_persona_modes:
        result["persona_modes"] = build_persona_modes(
            messages,
            lambda items: build_social_stats(items, include_persona_modes=False),
        )
    return result


def render_social_report(stats):
    median_text = (
        f"{stats['median_response_latency_minutes']} 分钟"
        if stats["median_response_latency_minutes"] is not None
        else "暂无可计算样本"
    )
    lines = [
        "# 社交图谱与时间画像",
        "",
        f"- 群聊消息：{stats['group_message_count']}",
        f"- 私聊消息：{stats['private_message_count']}",
        f"- 中位响应时延：{median_text}",
        f"- 熬夜消息占比：{stats['night_message_ratio']:.1%}",
        "",
        "## 高频会话",
    ]
    if stats["top_chats"]:
        for chat_name, count in stats["top_chats"][:8]:
            lines.append(f"- {chat_name}（{count}条）")
    else:
        lines.append("- 暂无高频会话")

    lines.extend(["", "## 活跃时段"])
    if stats["top_hours"]:
        for hour, count in stats["top_hours"][:8]:
            lines.append(f"- {hour}时（{count}条）")
    else:
        lines.append("- 暂无活跃时段数据")
    lines.extend(["", "## 双模式画像"])
    for label, key in [("工作人格", "work"), ("日常人格", "life")]:
        mode_stats = stats.get("persona_modes", {}).get(key)
        if mode_stats is None:
            lines.append(f"- {label}：样本不足")
            continue
        top_chat = mode_stats["top_chats"][0][0] if mode_stats["top_chats"] else "无"
        latency = mode_stats["median_response_latency_minutes"]
        latency_text = f"{latency} 分钟" if latency is not None else "暂无"
        lines.append(
            f"- {label}：高频会话 {top_chat} / 中位响应 {latency_text} / "
            f"群聊 {mode_stats['group_message_count']} / 私聊 {mode_stats['private_message_count']}"
        )
    lines.append("")
    return "\n".join(lines)


def analyze_social_graph(input_path=None, output_file=None, config_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    stats = build_social_stats(messages)
    report_markdown = render_social_report(stats)
    report_path = output_file or build_date_ranged_output_path("social", paths, config_path=config_path)
    write_text(report_path, report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="社交图谱与时间画像")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_social_graph(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
    )

    print("=" * 50)
    print("社交图谱与时间画像")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"报告路径: {result['report_path']}")
    print(f"中位响应时延: {result['median_response_latency_minutes']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
