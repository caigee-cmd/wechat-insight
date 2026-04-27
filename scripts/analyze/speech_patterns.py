#!/usr/bin/env python3
"""Speech pattern analysis for WeChat Insight."""

import argparse
import pathlib
import re
import sys
from collections import Counter


CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from common import build_date_ranged_output_path, build_persona_modes, load_messages, resolve_input_files, self_text_messages, write_text


STOPWORDS = {
    "这个", "那个", "一下", "已经", "还是", "然后", "就是", "我们", "你们", "他们",
    "可以", "今天", "明天", "现在", "这里", "那里", "自己", "一下子", "不是", "好的",
}


def extract_terms(text):
    cleaned = re.sub(r"\[[^\]]+\]", " ", text or "")
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,6}", cleaned)
    return [item for item in candidates if item not in STOPWORDS]


def is_phrase_candidate(content):
    if not content or content.startswith("["):
        return False
    if content.startswith("@"):
        return False
    if re.fullmatch(r"[A-Za-z]{1,3}", content):
        return False
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", content):
        return False
    return True


def build_speech_stats(messages, include_persona_modes=True):
    rows = self_text_messages(messages)
    if not rows:
        raise ValueError("输入消息为空，无法生成口癖统计")

    phrase_counter = Counter()
    punctuation_counts = {"question": 0, "exclamation": 0, "ellipsis": 0}
    term_counter = Counter()
    total_length = 0

    for message in rows:
        content = (message.get("content") or "").strip()
        if not content:
            continue
        total_length += len(content)
        if 2 <= len(content) <= 20 and is_phrase_candidate(content):
            phrase_counter[content] += 1

        punctuation_counts["question"] += content.count("?") + content.count("？")
        punctuation_counts["exclamation"] += content.count("!") + content.count("！")
        punctuation_counts["ellipsis"] += content.count("...") + content.count("…")

        for term in extract_terms(content):
            term_counter[term] += 1

    repeated_phrases = [
        {"text": text, "count": count}
        for text, count in sorted(
            phrase_counter.items(),
            key=lambda item: (-item[1], len(item[0]), item[0]),
        )
        if count >= 2
    ]

    top_terms = [
        {"text": text, "count": count}
        for text, count in term_counter.most_common(12)
    ]

    result = {
        "total_self_messages": len(rows),
        "avg_message_length": round(total_length / len(rows), 2),
        "repeated_phrases": repeated_phrases[:10],
        "punctuation_counts": punctuation_counts,
        "top_terms": top_terms,
    }
    if include_persona_modes:
        result["persona_modes"] = build_persona_modes(
            rows,
            lambda items: build_speech_stats(items, include_persona_modes=False),
        )
    return result


def render_speech_report(stats):
    lines = [
        "# 口癖与语言风格分析",
        "",
        f"- 样本消息数：{stats['total_self_messages']}",
        f"- 平均消息长度：{stats['avg_message_length']}",
        f"- 问号：{stats['punctuation_counts']['question']}",
        f"- 感叹号：{stats['punctuation_counts']['exclamation']}",
        f"- 省略号：{stats['punctuation_counts']['ellipsis']}",
        "",
        "## 重复口癖",
    ]
    if stats["repeated_phrases"]:
        for item in stats["repeated_phrases"][:8]:
            lines.append(f"- {item['text']}（{item['count']}次）")
    else:
        lines.append("- 暂无明显重复口癖")

    lines.extend(["", "## 高频表达"])
    if stats["top_terms"]:
        for item in stats["top_terms"][:8]:
            lines.append(f"- {item['text']}（{item['count']}次）")
    else:
        lines.append("- 暂无高频表达")
    lines.extend(["", "## 双模式画像"])
    for label, key in [("工作人格", "work"), ("日常人格", "life")]:
        mode_stats = stats.get("persona_modes", {}).get(key)
        if mode_stats is None:
            lines.append(f"- {label}：样本不足")
            continue
        top_phrase = mode_stats["repeated_phrases"][0]["text"] if mode_stats["repeated_phrases"] else "无明显口癖"
        lines.append(
            f"- {label}：{top_phrase} / 平均长度 {mode_stats['avg_message_length']} / "
            f"问号 {mode_stats['punctuation_counts']['question']} / 感叹号 {mode_stats['punctuation_counts']['exclamation']}"
        )
    lines.append("")
    return "\n".join(lines)


def analyze_speech_patterns(input_path=None, output_file=None, config_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    stats = build_speech_stats(messages)
    report_markdown = render_speech_report(stats)
    report_path = output_file or build_date_ranged_output_path("speech", paths, config_path=config_path)
    write_text(report_path, report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="口癖与语言风格分析")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_speech_patterns(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
    )

    print("=" * 50)
    print("口癖与语言风格分析")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"报告路径: {result['report_path']}")
    print(f"平均消息长度: {result['avg_message_length']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
