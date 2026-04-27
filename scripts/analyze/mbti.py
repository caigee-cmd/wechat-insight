#!/usr/bin/env python3
"""MBTI heuristic analysis for WeChat Insight."""

import argparse
import pathlib
import sys


CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from common import (
    build_date_ranged_output_path,
    build_persona_modes,
    clip_text,
    load_messages,
    resolve_input_files,
    substantive_self_text_messages,
    write_text,
)


DIMENSIONS = {
    "EI": {
        "positive_letter": "E",
        "negative_letter": "I",
        "positive_keywords": {
            "大家": 1, "一起": 1, "同步": 1, "我来": 2, "安排": 1, "推进": 1, "确认": 1,
            "开会": 1, "沟通": 1, "对齐": 1, "直接": 1, "找我": 1, "分享": 1, "帮": 1,
        },
        "negative_keywords": {
            "我先看": 2, "想想": 1, "研究下": 1, "整理下": 1, "安静": 1, "观察": 1, "复盘": 1, "先消化": 2,
        },
        "label": "能量来源",
    },
    "SN": {
        "positive_letter": "N",
        "negative_letter": "S",
        "positive_keywords": {
            "方向": 1, "长期": 2, "策略": 2, "模型": 2, "框架": 2, "趋势": 1, "可能性": 1,
            "抽象": 2, "原则": 1, "愿景": 1, "工作流": 2, "大模型": 3, "部署": 2,
            "提示词": 2, "服务商": 2, "B端": 2, "业务": 1, "公司": 1,
        },
        "negative_keywords": {
            "具体": 1, "细节": 1, "步骤": 1, "清单": 1, "位置": 1, "装修": 1, "材料": 1,
            "几点": 1, "多少": 1, "今天": 1, "明天": 1,
        },
        "label": "信息偏好",
    },
    "TF": {
        "positive_letter": "T",
        "negative_letter": "F",
        "positive_keywords": {
            "逻辑": 2, "数据": 2, "判断": 2, "效率": 2, "分析": 2, "方案": 2, "成本": 2,
            "风险": 3, "优先级": 2, "结论": 2, "年化": 2, "利息": 2, "可靠": 2,
            "划不来": 2, "多少钱": 2, "部署": 2, "业务": 2, "赚钱": 2,
        },
        "negative_keywords": {
            "喜欢": 1, "理解": 1, "辛苦": 1, "抱抱": 2, "关心": 1, "在乎": 1, "爱你": 2,
            "开心": 1, "难过": 1, "委屈": 1, "感谢": 1,
        },
        "label": "决策方式",
    },
    "JP": {
        "positive_letter": "J",
        "negative_letter": "P",
        "positive_keywords": {
            "安排": 2, "确认": 2, "计划": 2, "今天": 1, "明天": 1, "先做": 2, "优先": 2,
            "推进": 2, "截止": 2, "落地": 2, "直接": 1, "肯定": 1, "现在": 1, "我就会": 2,
        },
        "negative_keywords": {
            "看情况": 2, "再说": 2, "到时候": 2, "灵活": 1, "随意": 1, "试试看": 2,
            "先等等": 2, "不着急": 1, "慢慢来": 1, "以后再看": 2, "随缘": 2,
        },
        "label": "行动节奏",
    },
}


def count_keyword_hits(content, keywords):
    lowered = content.lower()
    hits = []
    score = 0
    for keyword, weight in keywords.items():
        if keyword.lower() in lowered:
            hits.append(keyword)
            score += weight
    return hits, score


def build_mbti_stats(messages, include_persona_modes=True):
    rows = substantive_self_text_messages(messages)
    if not rows:
        raise ValueError("输入消息为空，无法生成 MBTI 推测")

    dimensions = {}
    dimension_evidence = []

    for key, config in DIMENSIONS.items():
        positive_score = 0
        negative_score = 0

        for message in rows:
            content = (message.get("content") or "").strip()
            if not content:
                continue
            positive_hits, positive_delta = count_keyword_hits(content, config["positive_keywords"])
            negative_hits, negative_delta = count_keyword_hits(content, config["negative_keywords"])
            positive_score += positive_delta
            negative_score += negative_delta

            if positive_hits or negative_hits:
                dimension_evidence.append({
                    "dimension": key,
                    "content": clip_text(content, limit=56),
                    "positive_hits": positive_hits,
                    "negative_hits": negative_hits,
                    "signal_strength": positive_delta + negative_delta,
                })

        if key == "EI":
            unique_chats = len({message.get("chat_name", "未知会话") for message in rows})
            group_ratio = (
                sum(1 for message in rows if message.get("is_group")) / len(rows)
                if rows else 0
            )
            if unique_chats >= 4:
                positive_score += 2
            if group_ratio >= 0.45:
                positive_score += 1

        letter = config["positive_letter"] if positive_score >= negative_score else config["negative_letter"]
        confidence = round((abs(positive_score - negative_score) + 1) / (positive_score + negative_score + 2), 2)
        dimensions[key] = {
            "label": config["label"],
            "letter": letter,
            "scores": {
                config["positive_letter"]: positive_score,
                config["negative_letter"]: negative_score,
            },
            "confidence": confidence,
        }

    mbti_type = "".join(dimensions[key]["letter"] for key in ["EI", "SN", "TF", "JP"])
    dimension_evidence.sort(
        key=lambda item: (
            item["signal_strength"],
            item["dimension"],
            item["content"],
        ),
        reverse=True,
    )

    result = {
        "total_self_messages": len(rows),
        "mbti_type": mbti_type,
        "dimensions": dimensions,
        "evidence": dimension_evidence[:12],
    }
    if include_persona_modes:
        result["persona_modes"] = build_persona_modes(
            rows,
            lambda items: build_mbti_stats(items, include_persona_modes=False),
        )
    return result


def render_mbti_report(stats):
    lines = [
        "# MBTI 性格推测",
        "",
        f"- 样本消息数：{stats['total_self_messages']}",
        f"- 推测类型：{stats['mbti_type']}",
        "- 说明：基于聊天表达风格的启发式估计，仅供参考。",
        "",
        "## 四维拆解",
    ]
    for key in ["EI", "SN", "TF", "JP"]:
        item = stats["dimensions"][key]
        scores = item["scores"]
        letters = list(scores.keys())
        lines.append(
            f"- {key} / {item['label']}：{item['letter']} "
            f"（{letters[0]} {scores[letters[0]]} vs {letters[1]} {scores[letters[1]]}，confidence {item['confidence']:.2f}）"
        )

    lines.extend(["", "## 关键证据"])
    if stats["evidence"]:
        for item in stats["evidence"][:6]:
            hits = item["positive_hits"] + item["negative_hits"]
            lines.append(f"- {item['dimension']}：{item['content']} / 命中 {', '.join(hits)}")
    else:
        lines.append("- 样本过少，暂无明显语言证据")
    lines.extend(["", "## 双模式画像"])
    for label, key in [("工作人格", "work"), ("日常人格", "life")]:
        mode_stats = stats.get("persona_modes", {}).get(key)
        if mode_stats is None:
            lines.append(f"- {label}：样本不足")
            continue
        lines.append(
            f"- {label}：{mode_stats['mbti_type']} / "
            f"EI {mode_stats['dimensions']['EI']['letter']} / "
            f"SN {mode_stats['dimensions']['SN']['letter']} / "
            f"TF {mode_stats['dimensions']['TF']['letter']} / "
            f"JP {mode_stats['dimensions']['JP']['letter']}"
        )
    lines.append("")
    return "\n".join(lines)


def analyze_mbti(input_path=None, output_file=None, config_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    stats = build_mbti_stats(messages)
    report_markdown = render_mbti_report(stats)
    report_path = output_file or build_date_ranged_output_path("mbti", paths, config_path=config_path)
    write_text(report_path, report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="MBTI 性格推测")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_mbti(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
    )

    print("=" * 50)
    print("MBTI 性格推测")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"报告路径: {result['report_path']}")
    print(f"推测类型: {result['mbti_type']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
