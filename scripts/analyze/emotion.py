#!/usr/bin/env python3
"""Emotion trend analysis for WeChat Insight."""

import argparse
import importlib.util
import pathlib
import sys
from collections import Counter, defaultdict

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from common import build_date_ranged_output_path, build_persona_modes, load_messages, resolve_input_files, self_text_messages, write_text


POSITIVE_HINTS = [
    "谢谢", "太棒", "顺利", "开心", "赞", "高兴", "舒服", "支持", "感谢",
    "哈哈", "牛逼", "好吃", "稳", "好耶", "非常可以", "可以", "哇",
]
ANXIOUS_HINTS = ["焦虑", "担心", "紧张", "来不及", "赶不上", "怕", "压力", "不安", "急", "慌"]
ANGRY_HINTS = [
    "气死", "离谱", "火大", "生气", "崩了", "烦死", "恼火", "受不了",
    "妈的", "特么", "服了", "麻烦死", "咬牙切齿", "砸烂", "卧槽",
]
NEGATIVE_HINTS = ["烦", "难受", "不行", "不对", "糟糕", "崩溃", "失望", "失败", "冒险", "划不来", "不可靠"]


def load_message_rules_module():
    path = CURRENT_DIR.parent / "features" / "message_rules.py"
    spec = importlib.util.spec_from_file_location("message_rules", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MESSAGE_RULES = load_message_rules_module()


def detect_emotion_label(message):
    content = (message.get("content") or "").strip()
    rule_result = MESSAGE_RULES.analyze_message_rules(message)
    scores = {
        "positive": sum(1 for keyword in POSITIVE_HINTS if keyword in content),
        "anxious": sum(1 for keyword in ANXIOUS_HINTS if keyword in content),
        "angry": sum(1 for keyword in ANGRY_HINTS if keyword in content),
        "negative": sum(1 for keyword in NEGATIVE_HINTS if keyword in content),
    }
    if rule_result.get("is_negative_signal"):
        scores["negative"] += 1

    best_label, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_label
    if rule_result.get("is_negative_signal"):
        return "negative"
    return "neutral"


def build_emotion_stats(messages, include_persona_modes=True):
    rows = self_text_messages(messages)
    if not rows:
        raise ValueError("输入消息为空，无法生成情绪分析")

    distribution = Counter()
    daily_distribution = defaultdict(lambda: Counter())
    chat_distribution = defaultdict(lambda: Counter())

    for message in rows:
        label = detect_emotion_label(message)
        distribution[label] += 1
        date = message.get("datetime", "")[:10] or "unknown"
        chat_name = message.get("chat_name", "未知会话")
        daily_distribution[date][label] += 1
        chat_distribution[chat_name][label] += 1

    emotional_distribution = {
        key: distribution[key]
        for key in ["positive", "negative", "anxious", "angry"]
        if distribution[key] > 0
    }
    if emotional_distribution:
        dominant_emotion = max(
            emotional_distribution.items(),
            key=lambda item: (item[1], item[0]),
        )[0]
    else:
        dominant_emotion = distribution.most_common(1)[0][0]
    daily_rows = []
    for date in sorted(daily_distribution):
        counts = daily_distribution[date]
        daily_rows.append({
            "date": date,
            "positive": counts["positive"],
            "negative": counts["negative"],
            "neutral": counts["neutral"],
            "anxious": counts["anxious"],
            "angry": counts["angry"],
            "total_messages": sum(counts.values()),
        })

    top_emotional_chats = []
    for chat_name, counts in chat_distribution.items():
        top_emotional_chats.append({
            "chat_name": chat_name,
            "positive": counts["positive"],
            "negative": counts["negative"],
            "neutral": counts["neutral"],
            "anxious": counts["anxious"],
            "angry": counts["angry"],
            "emotion_score": counts["positive"] - counts["negative"] - counts["anxious"] - counts["angry"],
        })
    top_emotional_chats.sort(
        key=lambda item: (
            abs(item["emotion_score"]),
            item["negative"] + item["anxious"] + item["angry"],
            item["positive"],
            item["chat_name"],
        ),
        reverse=True,
    )

    result = {
        "total_text_messages": len(rows),
        "emotion_distribution": {
            "positive": distribution["positive"],
            "negative": distribution["negative"],
            "neutral": distribution["neutral"],
            "anxious": distribution["anxious"],
            "angry": distribution["angry"],
        },
        "dominant_emotion": dominant_emotion,
        "daily_emotions": daily_rows,
        "top_emotional_chats": top_emotional_chats[:8],
    }
    if include_persona_modes:
        result["persona_modes"] = build_persona_modes(
            rows,
            lambda items: build_emotion_stats(items, include_persona_modes=False),
        )
    return result


def render_emotion_report(stats):
    distribution = stats["emotion_distribution"]
    lines = [
        "# 情绪周期分析",
        "",
        f"- 文本消息数：{stats['total_text_messages']}",
        f"- 主导情绪：{stats['dominant_emotion']}",
        f"- positive：{distribution['positive']}",
        f"- negative：{distribution['negative']}",
        f"- anxious：{distribution['anxious']}",
        f"- angry：{distribution['angry']}",
        f"- neutral：{distribution['neutral']}",
        "",
        "## 每日情绪趋势",
    ]
    if stats["daily_emotions"]:
        for item in stats["daily_emotions"]:
            lines.append(
                f"- {item['date']}：positive {item['positive']} / negative {item['negative']} / "
                f"anxious {item['anxious']} / angry {item['angry']} / neutral {item['neutral']}"
            )
    else:
        lines.append("- 暂无情绪趋势数据")

    lines.extend(["", "## 情绪波动会话"])
    if stats["top_emotional_chats"]:
        for item in stats["top_emotional_chats"][:5]:
            lines.append(
                f"- {item['chat_name']}：positive {item['positive']} / negative {item['negative']} / "
                f"anxious {item['anxious']} / angry {item['angry']}（score {item['emotion_score']}）"
            )
    else:
        lines.append("- 暂无明显情绪波动会话")
    lines.extend(["", "## 双模式画像"])
    for label, key in [("工作人格", "work"), ("日常人格", "life")]:
        mode_stats = stats.get("persona_modes", {}).get(key)
        if mode_stats is None:
            lines.append(f"- {label}：样本不足")
            continue
        lines.append(
            f"- {label}：{mode_stats['dominant_emotion']} / positive {mode_stats['emotion_distribution']['positive']} / "
            f"negative {mode_stats['emotion_distribution']['negative']} / angry {mode_stats['emotion_distribution']['angry']}"
        )
    lines.append("")
    return "\n".join(lines)


def analyze_emotion(input_path=None, output_file=None, config_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    stats = build_emotion_stats(messages)
    report_markdown = render_emotion_report(stats)
    report_path = output_file or build_date_ranged_output_path("emotion", paths, config_path=config_path)
    write_text(report_path, report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="情绪周期分析")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_emotion(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
    )

    print("=" * 50)
    print("情绪周期分析")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"报告路径: {result['report_path']}")
    print(f"主导情绪: {result['dominant_emotion']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
