#!/usr/bin/env python3
"""
客户与商业分析报告

基于已导出的 JSONL 消息文件生成客户机会、售后风险和待跟进报告。
"""

import argparse
import glob
import importlib.util
import json
import os
import pathlib
from collections import Counter, defaultdict


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.wechat-insight/data")
DEFAULT_REPORT_DIR = os.path.expanduser("~/.wechat-insight/reports")
DEFAULT_LABELS_PATH = os.path.expanduser("~/.config/wechat-insight-contacts_labels.json")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
BUSINESS_SCOPE_ROLES = {"customer", "vendor", "unknown"}
ROLE_ORDER = ["customer", "vendor", "unknown"]


def load_config(config_path=None):
    path = os.path.expanduser(config_path or CONFIG_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "data_dir": DEFAULT_DATA_DIR,
        "report_dir": DEFAULT_REPORT_DIR,
    }


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


def clip_text(text, limit=42):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


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


def detect_pending_followup(contact_messages):
    last_outbound_ts = -1
    pending = None

    for message in contact_messages:
        timestamp = message.get("timestamp") or 0
        direction = message.get("direction")

        if direction == "outbound":
            last_outbound_ts = timestamp
            if pending and pending["timestamp"] < timestamp:
                pending = None
            continue

        if direction != "inbound" or message.get("msg_type_label") != "text":
            continue

        rule_result = MESSAGE_RULES.analyze_message_rules(message)
        labels = build_followup_labels(rule_result)
        if not labels or timestamp <= last_outbound_ts:
            continue

        pending = {
            "timestamp": timestamp,
            "datetime": message.get("datetime"),
            "content": message.get("content", ""),
            "labels": labels,
        }

    return pending


def infer_stage(metrics):
    if metrics["support_signal_count"] > 0:
        return "supporting"
    if metrics["quote_signal_count"] > 0 or metrics["business_signal_count"] > 0:
        return "negotiating"
    if metrics["pending_followup"] is not None:
        return "follow_up"
    return "unknown"


def analyze_contacts(messages, contact_labels=None):
    private_messages = [message for message in messages if not message.get("is_group")]
    grouped = defaultdict(list)
    for message in private_messages:
        grouped[message.get("chat_name", "未知联系人")].append(message)

    contact_labels = contact_labels or {}
    contacts = []
    for contact_name, items in grouped.items():
        label_info = contact_labels.get(contact_name, {})
        inbound_messages = sum(1 for item in items if item.get("direction") == "inbound")
        outbound_messages = sum(1 for item in items if item.get("direction") == "outbound")
        text_messages = [item for item in items if item.get("msg_type_label") == "text"]

        business_signal_count = 0
        quote_signal_count = 0
        support_signal_count = 0
        negative_signal_count = 0
        action_signal_count = 0
        signal_counter = Counter()

        for message in text_messages:
            rule_result = MESSAGE_RULES.analyze_message_rules(message)
            if rule_result["is_business_signal"]:
                business_signal_count += 1
                signal_counter["商业"] += 1
            if rule_result["is_quote_signal"]:
                quote_signal_count += 1
                signal_counter["报价"] += 1
            if rule_result["is_support_signal"]:
                support_signal_count += 1
                signal_counter["报错"] += 1
            if rule_result["is_negative_signal"]:
                negative_signal_count += 1
                signal_counter["负面"] += 1
            if rule_result["is_action_item"]:
                action_signal_count += 1
                signal_counter["待办"] += 1

        pending_followup = detect_pending_followup(items)
        opportunity_score = (
            quote_signal_count * 6
            + business_signal_count * 4
            + action_signal_count * 2
            + (3 if pending_followup else 0)
            + min(inbound_messages, 5)
        )
        risk_score = (
            support_signal_count * 6
            + negative_signal_count * 3
            + (3 if pending_followup else 0)
        )

        metrics = {
            "contact_name": contact_name,
            "role": label_info.get("role", "unknown"),
            "total_messages": len(items),
            "inbound_messages": inbound_messages,
            "outbound_messages": outbound_messages,
            "business_signal_count": business_signal_count,
            "quote_signal_count": quote_signal_count,
            "support_signal_count": support_signal_count,
            "negative_signal_count": negative_signal_count,
            "action_signal_count": action_signal_count,
            "opportunity_score": opportunity_score,
            "risk_score": risk_score,
            "pending_followup": pending_followup,
            "last_message_at": items[-1].get("datetime"),
            "signal_counter": signal_counter,
        }
        metrics["stage"] = infer_stage(metrics)
        contacts.append(metrics)

    contacts.sort(key=lambda item: (item["opportunity_score"], item["risk_score"], item["total_messages"]), reverse=True)
    return contacts


def build_stats(messages, contact_labels=None):
    if not messages:
        raise ValueError("输入消息为空，无法生成客户报告")

    contacts = analyze_contacts(messages, contact_labels=contact_labels)
    private_contacts = len(contacts)
    scoped_contacts = [
        contact for contact in contacts
        if contact["role"] in BUSINESS_SCOPE_ROLES
    ]
    business_contacts = [
        contact for contact in scoped_contacts
        if contact["opportunity_score"] > 0 or contact["risk_score"] > 0
    ]
    top_opportunities = sorted(
        business_contacts,
        key=lambda item: (item["opportunity_score"], item["quote_signal_count"], item["business_signal_count"]),
        reverse=True,
    )[:5]
    top_support_risks = sorted(
        business_contacts,
        key=lambda item: (item["risk_score"], item["support_signal_count"], item["negative_signal_count"]),
        reverse=True,
    )[:5]
    pending_followups = [
        contact for contact in business_contacts
        if contact["pending_followup"] is not None
    ]
    pending_followups.sort(
        key=lambda item: (
            item["pending_followup"]["timestamp"],
            item["opportunity_score"] + item["risk_score"],
        ),
        reverse=True,
    )

    grouped_contacts = {
        role: [contact for contact in business_contacts if contact["role"] == role]
        for role in ROLE_ORDER
    }
    grouped_opportunities = {
        role: sorted(
            grouped_contacts[role],
            key=lambda item: (
                item["opportunity_score"],
                item["quote_signal_count"],
                item["business_signal_count"],
            ),
            reverse=True,
        )[:5]
        for role in ROLE_ORDER
    }
    grouped_risks = {
        role: sorted(
            grouped_contacts[role],
            key=lambda item: (
                item["risk_score"],
                item["support_signal_count"],
                item["negative_signal_count"],
            ),
            reverse=True,
        )[:5]
        for role in ROLE_ORDER
    }
    grouped_pending_followups = {
        role: [
            contact for contact in pending_followups
            if contact["role"] == role
        ][:5]
        for role in ROLE_ORDER
    }
    role_counts = {
        role: len([contact for contact in scoped_contacts if contact["role"] == role])
        for role in ROLE_ORDER
    }

    return {
        "total_private_contacts": private_contacts,
        "business_scope_contacts": len(scoped_contacts),
        "business_contact_count": len(business_contacts),
        "excluded_contact_count": private_contacts - len(scoped_contacts),
        "top_opportunities": top_opportunities,
        "top_support_risks": top_support_risks,
        "pending_followups": pending_followups,
        "role_counts": role_counts,
        "grouped_opportunities": grouped_opportunities,
        "grouped_risks": grouped_risks,
        "grouped_pending_followups": grouped_pending_followups,
    }


def render_summary_lines(stats):
    lines = [
        f"- 私聊联系人总数：{stats['total_private_contacts']}",
        f"- 纳入商业分析范围：{stats['business_scope_contacts']}",
        f"- 已排除标签联系人：{stats['excluded_contact_count']}",
        f"- customer：{stats['role_counts']['customer']}，vendor：{stats['role_counts']['vendor']}，unknown：{stats['role_counts']['unknown']}",
        f"- 有商业/售后信号的联系人：{stats['business_contact_count']}",
        f"- 待跟进联系人：{len(stats['pending_followups'])}",
    ]
    if stats["top_opportunities"]:
        top = stats["top_opportunities"][0]
        lines.append(
            f"- 当前最值得推进的是 {top['contact_name']}，机会分 {top['opportunity_score']}。"
        )
    if stats["top_support_risks"]:
        risk = stats["top_support_risks"][0]
        lines.append(
            f"- 当前风险最高的是 {risk['contact_name']}，风险分 {risk['risk_score']}。"
        )
    return lines


def render_opportunity_lines(items):
    if not items:
        return ["- 暂无明显商业机会"]
    lines = []
    for item in items:
        lines.append(
            f"- {item['contact_name']}（机会分 {item['opportunity_score']}，"
            f"报价 {item['quote_signal_count']}，商业 {item['business_signal_count']}，"
            f"待办 {item['action_signal_count']}，角色 {item['role']}，阶段 {item['stage']}）"
        )
    return lines


def render_risk_lines(items):
    if not items:
        return ["- 暂无明显售后风险"]
    lines = []
    for item in items:
        lines.append(
            f"- {item['contact_name']}（风险分 {item['risk_score']}，"
            f"报错 {item['support_signal_count']}，负面 {item['negative_signal_count']}，"
            f"角色 {item['role']}，阶段 {item['stage']}）"
        )
    return lines


def render_pending_followup_lines(items):
    if not items:
        return ["- 暂无待跟进客户"]
    lines = []
    for item in items[:5]:
        followup = item["pending_followup"]
        lines.append(
            f"- {item['contact_name']}：{clip_text(followup['content'])}"
            f"（{' / '.join(followup['labels'])}，{followup['datetime']}）"
        )
    return lines


def render_role_group_section(role, stats):
    lines = [
        f"## {role} 分组",
        "",
        "### 高意向机会",
    ]
    lines.extend(render_opportunity_lines(stats["grouped_opportunities"][role]))
    lines.extend([
        "",
        "### 售后风险",
    ])
    lines.extend(render_risk_lines(stats["grouped_risks"][role]))
    lines.extend([
        "",
        "### 待跟进",
    ])
    lines.extend(render_pending_followup_lines(stats["grouped_pending_followups"][role]))
    return lines


def render_customer_report(stats):
    lines = [
        "# 客户与商业分析",
        "",
        "## 总览",
    ]
    lines.extend(render_summary_lines(stats))
    for role in ROLE_ORDER:
        lines.extend([
            "",
        ])
        lines.extend(render_role_group_section(role, stats))
    lines.append("")
    return "\n".join(lines)


def build_default_output_path(config_path=None):
    config = load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, "customer_report.md")


def analyze_customer(input_path=None, output_file=None, config_path=None, labels_path=None):
    paths = resolve_input_files(input_path=input_path, config_path=config_path)
    messages = load_messages(paths)
    contact_labels, resolved_labels_path = load_contact_labels(
        labels_path=labels_path,
        config_path=config_path,
    )
    stats = build_stats(messages, contact_labels=contact_labels)
    report_markdown = render_customer_report(stats)

    report_path = os.path.expanduser(output_file) if output_file else build_default_output_path(
        config_path=config_path
    )
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    result = dict(stats)
    result["input_files"] = paths
    result["labels_path"] = resolved_labels_path
    result["report_path"] = report_path
    result["report_markdown"] = report_markdown
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="客户与商业分析")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = analyze_customer(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        labels_path=args.labels,
    )

    print("=" * 50)
    print("客户与商业分析")
    print("=" * 50)
    print(f"输入文件: {', '.join(result['input_files'])}")
    print(f"标签文件: {result['labels_path']}")
    print(f"报告路径: {result['report_path']}")
    print(f"私聊联系人: {result['total_private_contacts']}")
    print(f"纳入范围联系人: {result['business_scope_contacts']}")
    print(f"待跟进联系人: {len(result['pending_followups'])}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
