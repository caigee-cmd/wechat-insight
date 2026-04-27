#!/usr/bin/env python3
"""Rule-based message tagging for WeChat Insight."""

import re

QUESTION_PATTERNS = [
    "？",
    "?",
    "吗",
    "呢",
    "是不是",
    "能不能",
    "可不可以",
    "要不要",
]

ACTION_PATTERNS = [
    "发我",
    "看下",
    "确认下",
    "跟进",
    "推进",
    "安排",
    "记得",
    "处理一下",
    "回复一下",
]

COMMITMENT_PATTERNS = [
    "我来",
    "我处理",
    "我晚点发",
    "我明天发",
    "我跟进",
    "我安排",
    "收到",
    "已发",
    "搞定",
    "完成",
    "确认了",
]

SCHEDULE_PATTERNS = [
    "明天",
    "后天",
    "待会",
    "今晚",
    "上午",
    "下午",
    "几点",
    "这周",
    "下周",
    "周一",
    "周二",
    "周三",
    "周四",
    "周五",
    "周六",
    "周日",
]

BUSINESS_PATTERNS = [
    "方案",
    "报价",
    "预算",
    "合同",
    "付款",
    "开票",
    "demo",
    "试用",
    "交付",
]

QUOTE_PATTERNS = [
    "报价",
    "价格",
    "多少钱",
    "预算",
    "费用",
    "怎么收费",
]

SUPPORT_PATTERNS = [
    "报错",
    "有问题",
    "不能用",
    "失败了",
    "异常",
    "退款",
    "没反应",
    "崩了",
]

NEGATIVE_PATTERNS = [
    "烦",
    "急",
    "无语",
    "离谱",
    "不行",
    "不对",
    "不满意",
    "生气",
    "崩溃",
]

TOPIC_KEYWORDS = {
    "work": ["上线", "需求", "开发", "排期", "接口", "发版", "测试", "修复"],
    "customer": ["报价", "合同", "预算", "方案", "付款", "客户", "合作"],
    "family": ["老婆", "妈妈", "弟弟", "妹妹", "回家", "吃饭"],
    "community": ["群", "社群", "活动", "拉群", "管理员"],
    "leisure": ["吃饭", "电影", "打球", "喝酒", "出去玩"],
    "ai": ["agent", "cursor", "claude", "gpt", "模型", "提示词", "工作流"],
}

SCHEDULE_REGEXES = [
    re.compile(r"\b\d{1,2}:\d{2}\b"),
    re.compile(r"\b\d{1,2}点(?:\d{1,2}分)?\b"),
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\b\d{1,2}月\d{1,2}日\b"),
]


def match_keywords(content, patterns):
    hits = []
    for pattern in patterns:
        if pattern.lower() in content.lower():
            hits.append(pattern)
    return hits


def analyze_message_rules(message):
    content = (message.get("content") or "").strip()
    msg_type_label = message.get("msg_type_label")

    if not content or msg_type_label != "text":
        return {
            "is_question": False,
            "is_action_item": False,
            "is_commitment": False,
            "is_schedule": False,
            "is_business_signal": False,
            "is_quote_signal": False,
            "is_support_signal": False,
            "is_negative_signal": False,
            "topic_tags": [],
            "keyword_hits": [],
            "emotion_label": "neutral",
        }

    keyword_hits = []

    def hits(patterns):
        matched = match_keywords(content, patterns)
        keyword_hits.extend(matched)
        return bool(matched)

    topic_tags = [
        tag
        for tag, patterns in TOPIC_KEYWORDS.items()
        if match_keywords(content, patterns)
    ]
    for tag in topic_tags:
        keyword_hits.extend(match_keywords(content, TOPIC_KEYWORDS[tag]))

    is_question = hits(QUESTION_PATTERNS)
    is_action_item = hits(ACTION_PATTERNS)
    is_commitment = hits(COMMITMENT_PATTERNS)
    is_schedule = hits(SCHEDULE_PATTERNS) or any(regex.search(content) for regex in SCHEDULE_REGEXES)
    is_business_signal = hits(BUSINESS_PATTERNS)
    is_quote_signal = hits(QUOTE_PATTERNS)
    is_support_signal = hits(SUPPORT_PATTERNS)
    is_negative_signal = hits(NEGATIVE_PATTERNS)

    if is_negative_signal:
        emotion_label = "negative"
    elif any(word in content for word in ["谢谢", "辛苦", "赞", "牛逼", "开心"]):
        emotion_label = "positive"
    else:
        emotion_label = "neutral"

    return {
        "is_question": is_question,
        "is_action_item": is_action_item,
        "is_commitment": is_commitment,
        "is_schedule": is_schedule,
        "is_business_signal": is_business_signal,
        "is_quote_signal": is_quote_signal,
        "is_support_signal": is_support_signal,
        "is_negative_signal": is_negative_signal,
        "topic_tags": sorted(set(topic_tags)),
        "keyword_hits": sorted(set(keyword_hits)),
        "emotion_label": emotion_label,
    }
