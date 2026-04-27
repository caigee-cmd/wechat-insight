#!/usr/bin/env python3
"""Build a unified report payload for HTML or dashboard rendering."""

import argparse
import importlib.util
import json
import os
import pathlib
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_REPORT_DIR = os.path.expanduser("~/.wechat-insight/reports")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"report_dir": DEFAULT_REPORT_DIR}


def load_script_module(name, relative_path):
    path = CURRENT_DIR.parent.parent / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


FEATURES_MODULE = load_script_module("build_features", "scripts/features/build_features.py")
DAILY_MODULE = load_script_module("daily", "scripts/analyze/daily.py")
CUSTOMER_MODULE = load_script_module("customer", "scripts/analyze/customer.py")
LABELS_MODULE = load_script_module("contact_labels", "scripts/analyze/contact_labels.py")
EMOTION_MODULE = load_script_module("emotion", "scripts/analyze/emotion.py")
MBTI_MODULE = load_script_module("mbti", "scripts/analyze/mbti.py")
SPEECH_MODULE = load_script_module("speech_patterns", "scripts/analyze/speech_patterns.py")
SOCIAL_MODULE = load_script_module("social_graph", "scripts/analyze/social_graph.py")


def load_jsonl_rows(path):
    rows = []
    resolved_path = os.path.expanduser(path)
    if not os.path.exists(resolved_path):
        return rows
    with open(resolved_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_feature_section(features_result):
    daily_rows = sorted(
        load_jsonl_rows(features_result["daily_features"]),
        key=lambda item: item.get("date", ""),
    )
    chat_rows = sorted(
        load_jsonl_rows(features_result["chat_features"]),
        key=lambda item: (
            item.get("total_messages", 0),
            item.get("business_signal_count", 0),
            item.get("chat_name", ""),
        ),
        reverse=True,
    )
    contact_rows = sorted(
        load_jsonl_rows(features_result["contact_features"]),
        key=lambda item: (
            item.get("total_messages", 0),
            item.get("business_signal_count", 0),
            item.get("contact_name", ""),
        ),
        reverse=True,
    )

    return {
        "output_dir": features_result["output_dir"],
        "available_dates": [row.get("date") for row in daily_rows if row.get("date")],
        "daily_activity": daily_rows,
        "chat_leaderboard": chat_rows[:12],
        "contact_leaderboard": contact_rows[:12],
    }


def to_json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(to_json_safe(item) for item in value)
    return value


def build_default_output_path(daily_result, config_path=None):
    config = load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)

    start_dt = daily_result["start_dt"]
    end_dt = daily_result["end_dt"]
    if start_dt.date() == end_dt.date():
        filename = f"report_payload_{start_dt.strftime('%Y%m%d')}.json"
    else:
        filename = (
            f"report_payload_{start_dt.strftime('%Y%m%d')}_"
            f"{end_dt.strftime('%Y%m%d')}.json"
        )
    return os.path.join(report_dir, filename)


def build_overview(daily_result, customer_result, labels_result, emotion_result, mbti_result, speech_result, social_result):
    date_span_days = (daily_result["end_dt"].date() - daily_result["start_dt"].date()).days + 1
    return {
        "total_messages": daily_result["total_messages"],
        "text_messages": daily_result["text_messages"],
        "active_chat_count": daily_result["chat_count"],
        "group_message_count": daily_result["group_messages"],
        "private_message_count": daily_result["private_messages"],
        "total_private_contacts": customer_result["total_private_contacts"],
        "business_contact_count": customer_result["business_contact_count"],
        "pending_followup_count": len(customer_result["pending_followups"]),
        "generated_contact_labels": labels_result["generated_contacts"],
        "date_span_days": date_span_days,
        "dominant_emotion": emotion_result["dominant_emotion"],
        "mbti_type": mbti_result["mbti_type"],
        "avg_message_length": speech_result["avg_message_length"],
        "median_response_latency_minutes": social_result["median_response_latency_minutes"],
    }


def build_report_data_payload(input_path=None, output_file=None, config_path=None, labels_path=None):
    features_result = FEATURES_MODULE.build_features(
        input_paths=[input_path] if input_path else None,
        config_path=config_path,
    )
    labels_result = LABELS_MODULE.bootstrap_contact_labels(
        input_path=input_path,
        output_file=labels_path,
        config_path=config_path,
    )
    daily_result = DAILY_MODULE.analyze_daily(
        input_path=input_path,
        config_path=config_path,
    )
    emotion_result = EMOTION_MODULE.analyze_emotion(
        input_path=input_path,
        config_path=config_path,
    )
    mbti_result = MBTI_MODULE.analyze_mbti(
        input_path=input_path,
        config_path=config_path,
    )
    speech_result = SPEECH_MODULE.analyze_speech_patterns(
        input_path=input_path,
        config_path=config_path,
    )
    social_result = SOCIAL_MODULE.analyze_social_graph(
        input_path=input_path,
        config_path=config_path,
    )
    customer_result = CUSTOMER_MODULE.analyze_customer(
        input_path=input_path,
        config_path=config_path,
        labels_path=labels_result["output_path"],
    )
    feature_section = build_feature_section(features_result)

    payload = {
        "schema_version": "report-data.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "overview": build_overview(
            daily_result,
            customer_result,
            labels_result,
            emotion_result,
            mbti_result,
            speech_result,
            social_result,
        ),
        "sources": {
            "input_files": daily_result["input_files"],
            "config_path": os.path.expanduser(config_path) if config_path else None,
        },
        "artifacts": {
            "payload_path": None,
            "daily_report_path": daily_result["report_path"],
            "customer_report_path": customer_result["report_path"],
            "emotion_report_path": emotion_result["report_path"],
            "mbti_report_path": mbti_result["report_path"],
            "speech_report_path": speech_result["report_path"],
            "social_report_path": social_result["report_path"],
            "labels_path": labels_result["output_path"],
            "feature_files": {
                "messages_enriched": features_result["messages_enriched"],
                "daily_features": features_result["daily_features"],
                "chat_features": features_result["chat_features"],
                "contact_features": features_result["contact_features"],
            },
        },
        "sections": {
            "daily": to_json_safe(daily_result),
            "customer": to_json_safe(customer_result),
            "labels": to_json_safe(labels_result),
            "features": to_json_safe(feature_section),
            "emotion": to_json_safe(emotion_result),
            "mbti": to_json_safe(mbti_result),
            "speech": to_json_safe(speech_result),
            "social": to_json_safe(social_result),
        },
    }

    payload_path = os.path.expanduser(output_file) if output_file else build_default_output_path(
        daily_result,
        config_path=config_path,
    )
    payload["artifacts"]["payload_path"] = payload_path

    payload_dir = os.path.dirname(payload_path)
    if payload_dir:
        os.makedirs(payload_dir, exist_ok=True)
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成统一 report payload 数据")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 JSON 路径")
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = build_report_data_payload(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        labels_path=args.labels,
    )

    print("=" * 50)
    print("WeChat Insight Report Data")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['sources']['input_files'])}")
    print(f"输出路径: {result['artifacts']['payload_path']}")
    print(f"总消息数: {result['overview']['total_messages']}")
    print(f"商机联系人: {result['overview']['business_contact_count']}")
    print(f"待跟进联系人: {result['overview']['pending_followup_count']}")
    print(f"主导情绪: {result['overview']['dominant_emotion']}")
    print(f"MBTI 推测: {result['overview']['mbti_type']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
