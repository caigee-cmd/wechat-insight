#!/usr/bin/env python3
"""Shared helpers for WeChat Insight analyzers."""

import glob
import importlib.util
import json
import os
import pathlib
import re
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_REPORT_DIR = os.path.expanduser("~/.wechat-insight/reports")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
WORK_TOPIC_TAGS = {"work", "customer", "ai", "community"}
LIFE_TOPIC_TAGS = {"family", "leisure"}
WORK_CHAT_HINTS = ["客户", "技术", "开发", "AI", "Agent", "社区", "售后", "公司", "老板", "经理", "总", "群"]
LIFE_CHAT_HINTS = ["老婆", "弟弟", "妹妹", "妈妈", "爸爸", "家", "宝贝", "亲爱", "朋友"]
WORK_CONTENT_HINTS = ["模型", "部署", "工作流", "提示词", "报价", "方案", "客户", "业务", "公司", "合同", "年化", "API", "Codex", "Cursor", "Claude", "GPT"]
LIFE_CONTENT_HINTS = ["吃饭", "回家", "房子", "装修", "午饭", "晚饭", "周末", "自拍", "结婚", "老婆", "弟弟", "妹妹"]


def load_config(config_path=None, defaults=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    payload = dict(defaults or {})
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            payload.update(json.load(f))
    return payload


def find_latest_export_file(data_dir):
    pattern = os.path.join(os.path.expanduser(data_dir), "messages_*.jsonl")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (os.path.getmtime(path), path))


def resolve_input_files(input_path=None, config_path=None):
    config = load_config(config_path, defaults={"data_dir": DEFAULT_DATA_DIR})
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
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    rows.sort(key=lambda item: item.get("timestamp", 0))
    return rows


def text_messages(messages):
    return [message for message in messages if message.get("msg_type_label") == "text" and (message.get("content") or "").strip()]


def self_text_messages(messages):
    candidates = [
        message for message in text_messages(messages)
        if message.get("is_self") is True or message.get("direction") == "outbound"
    ]
    return candidates or text_messages(messages)


def load_message_rules_module():
    path = CURRENT_DIR.parent / "features" / "message_rules.py"
    spec = importlib.util.spec_from_file_location("message_rules", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MESSAGE_RULES = load_message_rules_module()


def substantive_self_text_messages(messages, min_length=6):
    rows = []
    for message in self_text_messages(messages):
        content = (message.get("content") or "").strip()
        compact = re.sub(r"\s+", "", content)
        if not compact:
            continue
        if content.startswith("[") and content.endswith("]"):
            continue
        if content.lower().startswith("http"):
            continue
        if content.startswith("@") and len(compact) <= 16:
            continue
        if len(compact) < min_length:
            continue
        if re.fullmatch(r"[A-Za-z0-9?？!！。，,.~\-\s]+", content) and len(compact) < 10:
            continue
        rows.append(message)
    return rows


def persona_mode_scores(message):
    content = (message.get("content") or "").strip()
    chat_name = str(message.get("chat_name") or "")
    lowered = content.lower()
    topic_tags = set(MESSAGE_RULES.analyze_message_rules(message).get("topic_tags", []))
    work_score = 0
    life_score = 0

    work_score += len(topic_tags & WORK_TOPIC_TAGS) * 2
    life_score += len(topic_tags & LIFE_TOPIC_TAGS) * 2

    if any(keyword.lower() in chat_name.lower() for keyword in WORK_CHAT_HINTS):
        work_score += 2
    if any(keyword.lower() in chat_name.lower() for keyword in LIFE_CHAT_HINTS):
        life_score += 2
    if any(keyword.lower() in lowered for keyword in WORK_CONTENT_HINTS):
        work_score += 2
    if any(keyword.lower() in lowered for keyword in LIFE_CONTENT_HINTS):
        life_score += 2
    if message.get("is_group") and not life_score:
        work_score += 1

    if work_score >= life_score and work_score >= 2:
        mode = "work"
    elif life_score > work_score and life_score >= 2:
        mode = "life"
    else:
        mode = None
    return {
        "mode": mode,
        "work_score": work_score,
        "life_score": life_score,
        "topic_tags": sorted(topic_tags),
    }


def split_persona_mode_messages(messages):
    buckets = {"work": [], "life": []}
    for message in messages:
        mode = persona_mode_scores(message)["mode"]
        if mode in buckets:
            buckets[mode].append(message)
    return buckets


def build_persona_modes(messages, build_fn):
    buckets = split_persona_mode_messages(messages)
    return {
        mode: build_fn(items) if items else None
        for mode, items in buckets.items()
    }


def build_date_ranged_output_path(prefix, paths, config_path=None, suffix="md"):
    config = load_config(config_path, defaults={"report_dir": DEFAULT_REPORT_DIR})
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)

    messages = load_messages(paths)
    if not messages:
        filename = f"{prefix}.{suffix}"
        return os.path.join(report_dir, filename)

    start_dt = datetime.fromtimestamp(messages[0]["timestamp"])
    end_dt = datetime.fromtimestamp(messages[-1]["timestamp"])
    if start_dt.date() == end_dt.date():
        filename = f"{prefix}_{start_dt.strftime('%Y%m%d')}.{suffix}"
    else:
        filename = f"{prefix}_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.{suffix}"
    return os.path.join(report_dir, filename)


def write_text(path, content):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def clip_text(text, limit=42):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
