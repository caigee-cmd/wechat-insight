#!/usr/bin/env python3
"""Generate a single-file HTML dashboard from report payload data."""

import argparse
import html
import importlib.util
import json
import math
import os
import pathlib


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


REPORT_DATA_MODULE = load_script_module("report_data", "scripts/analyze/report_data.py")


def clip_text(text, limit=48):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def escape_text(value):
    return html.escape(str(value if value is not None else ""))


def load_payload(payload_path):
    with open(os.path.expanduser(payload_path), encoding="utf-8") as f:
        return json.load(f)


def build_default_output_path(payload, payload_path=None, config_path=None):
    resolved_payload_path = payload_path or payload.get("artifacts", {}).get("payload_path")
    if resolved_payload_path:
        payload_file = pathlib.Path(os.path.expanduser(resolved_payload_path))
        name = payload_file.stem
        if name.startswith("report_payload_"):
            filename = f"dashboard_{name[len('report_payload_'):]}.html"
        else:
            filename = f"{name}.html"
        return str(payload_file.with_name(filename))

    config = load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, "dashboard.html")


def render_metric_card(label, value, tone="default", detail=None):
    detail_html = (
        f'<div class="metric-card__detail">{escape_text(detail)}</div>'
        if detail not in (None, "")
        else ""
    )
    return (
        f'<article class="metric-card metric-card--{tone}">'
        f'<div class="metric-card__label">{escape_text(label)}</div>'
        f'<div class="metric-card__value">{escape_text(value)}</div>'
        f"{detail_html}"
        "</article>"
    )


def render_bars(items, empty_text="暂无数据", suffix=""):
    if not items:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'

    max_value = max(int(item[1]) for item in items) if items else 1
    rows = []
    for name, value in items:
        safe_value = int(value)
        width = 0 if max_value == 0 else max(8, round(safe_value / max_value * 100))
        rows.append(
            '<li class="bar-list__item">'
            f'<div class="bar-list__header"><span>{escape_text(name)}</span><strong>{escape_text(str(safe_value) + suffix)}</strong></div>'
            f'<div class="bar-list__track"><span class="bar-list__fill" style="width:{width}%"></span></div>'
            "</li>"
        )
    return '<ul class="bar-list">' + "".join(rows) + "</ul>"


def render_bullet_list(items, empty_text="暂无数据"):
    if not items:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    return '<ul class="bullet-list">' + "".join(
        f"<li>{item}</li>" for item in items
    ) + "</ul>"


def render_summary_lines(summary_lines):
    return render_bullet_list(
        [escape_text(line) for line in summary_lines],
        empty_text="暂无摘要",
    )


def render_daily_followups(items):
    if not items:
        return '<div class="empty-state">暂无明显待跟进会话</div>'
    rows = []
    for item in items[:5]:
        labels = " / ".join(item.get("labels", []))
        rows.append(
            '<li class="signal-list__item">'
            f'<div class="signal-list__title">{escape_text(item.get("chat_name", "未知会话"))}</div>'
            f'<div class="signal-list__body">{escape_text(clip_text(item.get("content", "")))}</div>'
            f'<div class="signal-list__meta">{escape_text(labels)} · {escape_text(item.get("datetime", ""))}</div>'
            "</li>"
        )
    return '<ul class="signal-list">' + "".join(rows) + "</ul>"


def render_opportunity_list(items):
    if not items:
        return '<div class="empty-state">暂无明显商业机会</div>'
    rows = []
    for item in items[:5]:
        rows.append(
            '<li class="signal-list__item">'
            f'<div class="signal-list__title">{escape_text(item.get("contact_name", "未知联系人"))}</div>'
            f'<div class="signal-list__body">机会分 {escape_text(item.get("opportunity_score", 0))} · '
            f'报价 {escape_text(item.get("quote_signal_count", 0))} · '
            f'商业 {escape_text(item.get("business_signal_count", 0))}</div>'
            f'<div class="signal-list__meta">{escape_text(role_label(item.get("role", "unknown")))} · {escape_text(stage_label(item.get("stage", "unknown")))}</div>'
            "</li>"
        )
    return '<ul class="signal-list">' + "".join(rows) + "</ul>"


def render_risk_list(items):
    if not items:
        return '<div class="empty-state">暂无明显售后风险</div>'
    rows = []
    for item in items[:5]:
        rows.append(
            '<li class="signal-list__item">'
            f'<div class="signal-list__title">{escape_text(item.get("contact_name", "未知联系人"))}</div>'
            f'<div class="signal-list__body">风险分 {escape_text(item.get("risk_score", 0))} · '
            f'报错 {escape_text(item.get("support_signal_count", 0))} · '
            f'负面 {escape_text(item.get("negative_signal_count", 0))}</div>'
            f'<div class="signal-list__meta">{escape_text(role_label(item.get("role", "unknown")))} · {escape_text(stage_label(item.get("stage", "unknown")))}</div>'
            "</li>"
        )
    return '<ul class="signal-list">' + "".join(rows) + "</ul>"


def render_customer_followups(items):
    if not items:
        return '<div class="empty-state">暂无待跟进客户</div>'
    rows = []
    for item in items[:5]:
        followup = item.get("pending_followup") or {}
        labels = " / ".join(followup.get("labels", []))
        rows.append(
            '<li class="signal-list__item">'
            f'<div class="signal-list__title">{escape_text(item.get("contact_name", "未知联系人"))}</div>'
            f'<div class="signal-list__body">{escape_text(clip_text(followup.get("content", "")))}</div>'
            f'<div class="signal-list__meta">{escape_text(labels)} · {escape_text(followup.get("datetime", ""))}</div>'
            "</li>"
        )
    return '<ul class="signal-list">' + "".join(rows) + "</ul>"


def render_key_value_list(rows, empty_text="暂无数据"):
    filtered_rows = [(label, value) for label, value in rows if value not in (None, "", [], {})]
    if not filtered_rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    return '<ul class="meta-list">' + "".join(
        '<li class="meta-list__item">'
        f'<span>{escape_text(label)}</span><code>{escape_text(value)}</code>'
        "</li>"
        for label, value in filtered_rows
    ) + "</ul>"


def serialize_payload_for_script(payload):
    return json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")


EMOTION_LABELS = {
    "positive": "积极",
    "negative": "消极",
    "anxious": "焦虑",
    "angry": "愤怒",
    "neutral": "平稳",
    "unknown": "未知",
}

EMOTION_COLORS = {
    "positive": "#0f766e",
    "negative": "#b45309",
    "anxious": "#dc6803",
    "angry": "#b42318",
    "neutral": "#17313e",
}

ROLE_LABELS = {
    "customer": "客户",
    "vendor": "供应方",
    "unknown": "未知",
}

STAGE_LABELS = {
    "negotiating": "推进中",
    "follow_up": "待跟进",
    "supporting": "售后处理中",
    "unknown": "未知",
}

PHRASE_LAYOUT_PRESETS = [
    {"accent": "sea", "lane": "mid", "x": 14, "y": 33, "width": 27, "mobile_span": 2, "drift_x": -10, "drift_y": -6, "rotate": -1.8},
    {"accent": "ink", "lane": "mid", "x": 60, "y": 29, "width": 24, "mobile_span": 2, "drift_x": 8, "drift_y": 2, "rotate": 1.4},
    {"accent": "gold", "lane": "top", "x": 26, "y": 6, "width": 21, "mobile_span": 1, "drift_x": -5, "drift_y": 5, "rotate": -0.9},
    {"accent": "sea", "lane": "bottom", "x": 55, "y": 63, "width": 27, "mobile_span": 2, "drift_x": 6, "drift_y": -5, "rotate": 1.1},
    {"accent": "ink", "lane": "mid", "x": 2, "y": 59, "width": 21, "mobile_span": 1, "drift_x": -8, "drift_y": 4, "rotate": -1.2},
    {"accent": "gold", "lane": "top", "x": 76, "y": 8, "width": 17, "mobile_span": 1, "drift_x": 5, "drift_y": -4, "rotate": 1.2},
    {"accent": "sea", "lane": "bottom", "x": 34, "y": 76, "width": 18, "mobile_span": 1, "drift_x": -4, "drift_y": 6, "rotate": -0.7},
    {"accent": "ink", "lane": "top", "x": 43, "y": 0, "width": 18, "mobile_span": 1, "drift_x": 7, "drift_y": -3, "rotate": 0.8},
    {"accent": "gold", "lane": "mid", "x": 81, "y": 48, "width": 15, "mobile_span": 1, "drift_x": 6, "drift_y": 5, "rotate": -0.6},
    {"accent": "sea", "lane": "top", "x": 7, "y": 13, "width": 15, "mobile_span": 1, "drift_x": -3, "drift_y": 4, "rotate": 0.9},
    {"accent": "ink", "lane": "mid", "x": 23, "y": 56, "width": 17, "mobile_span": 1, "drift_x": 4, "drift_y": -5, "rotate": 0.5},
    {"accent": "gold", "lane": "bottom", "x": 63, "y": 80, "width": 17, "mobile_span": 1, "drift_x": -5, "drift_y": 4, "rotate": -0.8},
]

PHRASE_ACCENTS = ["sea", "ink", "gold"]


def format_number(value, digits=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value if value is not None else "")
    if digits > 0:
        text = f"{number:.{digits}f}"
        return text.rstrip("0").rstrip(".")
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def emotion_label(value):
    return EMOTION_LABELS.get(value, value or "未知")


def emotion_tone(value):
    return {
        "positive": "sea",
        "negative": "gold",
        "anxious": "gold",
        "angry": "rose",
        "neutral": "ink",
    }.get(value, "ink")


def resolve_phrase_accent_seed(text):
    source = str(text or "").strip()
    if not source:
        return PHRASE_ACCENTS[0]
    hash_value = 0
    for char in source:
        hash_value = (hash_value + ord(char)) % len(PHRASE_ACCENTS)
    return PHRASE_ACCENTS[hash_value]


def build_phrase_focus_summary(count, is_top, top_count, total_count):
    share = format_percent(count / total_count) if total_count else "--"
    if is_top:
        return "当前高频池里最突出的表达"
    if count == top_count:
        return f"与最高频并列，占当前高频池 {share}"
    return f"比最高频少 {top_count - count} 次，占当前高频池 {share}"


def format_percent(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value if value is not None else "")
    return f"{number * 100:.1f}%"


def format_datetime(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if "T" in text:
        date_text, _, time_text = text.partition("T")
        return f"{date_text} {time_text[:5]}".strip()
    if len(text) >= 16 and text[10] == " ":
        return text[:16]
    return text


def role_label(value):
    return ROLE_LABELS.get(value, value or "未知")


def stage_label(value):
    return STAGE_LABELS.get(value, value or "未知")


def build_html_data_attrs(attributes):
    parts = []
    for key, value in attributes.items():
        if value in (None, ""):
            continue
        safe_key = str(key).replace("_", "-")
        parts.append(f'data-{safe_key}="{escape_text(value)}"')
    return " ".join(parts)


def build_conic_gradient(segments):
    total = sum(max(0, int(value)) for _, value, _ in segments)
    if total <= 0:
        return "conic-gradient(#d9d8d2 0 360deg)"

    offset = 0.0
    stops = []
    for _, value, color in segments:
        safe_value = max(0, int(value))
        if safe_value <= 0:
            continue
        start = offset / total * 360
        offset += safe_value
        end = offset / total * 360
        stops.append(f"{color} {start:.2f}deg {end:.2f}deg")
    return "conic-gradient(" + ", ".join(stops) + ")"


def build_polyline_points(values, width=640, height=220, padding=24):
    if not values:
        return []
    safe_values = [max(0, float(value)) for value in values]
    max_value = max(max(safe_values), 1)
    step_x = 0 if len(safe_values) == 1 else (width - padding * 2) / (len(safe_values) - 1)
    points = []
    for index, value in enumerate(safe_values):
        x = padding + step_x * index
        y = height - padding - ((height - padding * 2) * value / max_value)
        points.append((x, y))
    return points


def render_kicker(title, subtitle):
    return (
        '<div class="section-kicker">'
        f'<span class="section-kicker__title">{escape_text(title)}</span>'
        f'<span class="section-kicker__subtitle">{escape_text(subtitle)}</span>'
        "</div>"
    )


def render_stat_chips(items):
    rows = []
    for label, value, tone in items:
        rows.append(
            f'<div class="stat-chip stat-chip--{tone}">'
            f'<span>{escape_text(label)}</span>'
            f'<strong>{escape_text(value)}</strong>'
            "</div>"
        )
    return '<div class="stat-chip-row">' + "".join(rows) + "</div>"


def render_donut_chart(rows, total_label="情绪样本", empty_text="暂无数据"):
    segments = [(label, value, color) for label, value, color in rows if int(value or 0) > 0]
    total = sum(int(value) for _, value, _ in segments)
    if total <= 0:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'

    legend_rows = []
    for label, value, color in segments:
        ratio = round(int(value) / total * 100)
        legend_rows.append(
            '<li class="legend-list__item">'
            f'<span class="legend-list__swatch" style="background:{escape_text(color)}"></span>'
            f'<span class="legend-list__label">{escape_text(label)}</span>'
            f'<strong>{escape_text(str(value))}</strong>'
            f'<em>{escape_text(str(ratio) + "%")}</em>'
            "</li>"
        )

    return (
        '<div class="donut-layout">'
        '<div class="donut">'
        f'<div class="donut__ring" style="background:{escape_text(build_conic_gradient(segments))}"></div>'
        '<div class="donut__core">'
        f'<strong>{escape_text(total)}</strong>'
        f'<span>{escape_text(total_label)}</span>'
        "</div>"
        "</div>"
        '<ul class="legend-list">' + "".join(legend_rows) + "</ul>"
        "</div>"
    )


def render_dimension_matrix(dimensions, empty_text="暂无 MBTI 维度数据"):
    order = ["EI", "SN", "TF", "JP"]
    rows = []
    for key in order:
        item = dimensions.get(key) or {}
        scores = item.get("scores", {})
        letters = list(scores.keys())
        if len(letters) == 2:
            left_letter, right_letter = letters[0], letters[1]
            left_score = max(0, int(scores.get(left_letter, 0)))
            right_score = max(0, int(scores.get(right_letter, 0)))
            total = max(left_score + right_score, 1)
            left_width = round(left_score / total * 100)
            right_width = 100 - left_width
            confidence = round(float(item.get("confidence", 0)) * 100)
        else:
            left_letter = item.get("letter", "?")
            right_letter = "·"
            left_score = 1
            right_score = 0
            left_width = 100
            right_width = 0
            confidence = round(float(item.get("confidence", 0)) * 100)
        rows.append(
            '<article class="dimension-card">'
            '<div class="dimension-card__head">'
            f'<span>{escape_text(item.get("label", key))}</span>'
            f'<strong>{escape_text(item.get("letter", "?"))}</strong>'
            "</div>"
            '<div class="dimension-card__meta">'
            f'<span>{escape_text(left_letter)} {escape_text(left_score)}</span>'
            f'<span>置信度 {escape_text(str(confidence) + "%")}</span>'
            f'<span>{escape_text(right_letter)} {escape_text(right_score)}</span>'
            "</div>"
            '<div class="dimension-card__track">'
            f'<span class="dimension-card__fill dimension-card__fill--left" style="width:{left_width}%"></span>'
            f'<span class="dimension-card__fill dimension-card__fill--right" style="width:{right_width}%"></span>'
            "</div>"
            "</article>"
        )
    if not rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    return '<div class="dimension-grid">' + "".join(rows) + "</div>"


def render_phrase_cloud(items, empty_text="暂无明显高频表达"):
    if not items:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    rows = sorted(
        [item for item in items if (item.get("text") or "").strip()],
        key=lambda item: int(item.get("count", 0) or 0),
        reverse=True,
    )[:12]
    if not rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    max_count = max(max(1, int(item.get("count", 1))) for item in rows)
    top_phrase = rows[0]
    top_count = max(1, int(top_phrase.get("count", 1)))
    total_count = sum(max(0, int(item.get("count", 0) or 0)) for item in rows)
    top_accent = resolve_phrase_accent_seed(top_phrase.get("text"))
    top_lane = PHRASE_LAYOUT_PRESETS[0].get("lane", "mid")
    top_summary = build_phrase_focus_summary(top_count, True, top_count, total_count)
    chips = []
    for index, item in enumerate(rows):
        text = (item.get("text") or "").strip()
        count = max(1, int(item.get("count", 1)))
        normalized = count / max_count
        size = 0.98 + normalized * 0.9
        weight = 540 + round(normalized * 180)
        preset = PHRASE_LAYOUT_PRESETS[index % len(PHRASE_LAYOUT_PRESETS)]
        accent = resolve_phrase_accent_seed(text)
        duration = 7.2 + index * 0.45
        delay = -index * 0.52
        data_attrs = build_html_data_attrs({
            "eyebrow": "Top Phrase" if index == 0 else "Phrase Focus",
            "title": text,
            "value": f"{count}次",
            "summary": build_phrase_focus_summary(count, index == 0, top_count, total_count),
            "accent": accent,
            "lane": preset.get("lane", "mid"),
        })
        chips.append(
            f'<article class="phrase-chip phrase-chip--{accent} {"phrase-chip--active" if index == 0 else ""}" {data_attrs} tabindex="0" '
            f'style="--x:{preset["x"]}%;--y:{preset["y"]}%;--width:{preset["width"]}%;'
            f'--span-mobile:{preset["mobile_span"]};'
            f'--drift-x:{preset["drift_x"]}px;--drift-y:{preset["drift_y"]}px;'
            f'--rotate:{preset["rotate"]}deg;--duration:{duration:.2f}s;'
            f'--delay:{delay:.2f}s;font-size:{size:.2f}rem;">'
            f'<span class="phrase-chip__label" style="font-weight:{weight};">{escape_text(text)}</span>'
            '<span class="phrase-chip__rail" aria-hidden="true"><i></i><i></i></span>'
            f'<em class="phrase-chip__count">{escape_text(str(count) + "次")}</em>'
            "</article>"
        )
    if not chips:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    cloud_attrs = build_html_data_attrs({
        "default_eyebrow": "Top Phrase",
        "default_title": top_phrase.get("text", ""),
        "default_value": f"{top_count}次",
        "default_summary": top_summary,
        "default_accent": top_accent,
        "default_lane": top_lane,
    })
    return (
        f'<div class="phrase-cloud phrase-cloud--lane-{top_lane} phrase-cloud--tone-{top_accent}" aria-label="口癖排版云" {cloud_attrs}>'
        '<svg class="phrase-cloud__paths" aria-hidden="true" viewBox="0 0 100 100" preserveAspectRatio="none">'
        '<path d="M2 22 C 18 12, 30 14, 43 26 S 72 40, 98 18"></path>'
        '<path d="M0 50 C 18 40, 31 43, 42 50 S 70 60, 100 48"></path>'
        '<path d="M5 82 C 22 72, 36 68, 46 66 S 73 72, 94 84"></path>'
        '<ellipse cx="50" cy="48" rx="15.5" ry="12.5"></ellipse>'
        "</svg>"
        '<div class="phrase-cloud__guides" aria-hidden="true"><span></span><span></span><span></span></div>'
        f'<div class="phrase-cloud__core phrase-cloud__core--{top_accent}"><span class="phrase-cloud__core-eyebrow">Top Phrase</span><strong class="phrase-cloud__core-title">{escape_text(top_phrase.get("text", ""))}</strong><b class="phrase-cloud__core-value">{escape_text(str(top_count) + "次")}</b><small class="phrase-cloud__core-summary">{escape_text(top_summary)}</small></div>'
        + "".join(chips)
        + "</div>"
    )


def render_line_chart(rows, title, primary_key="total_messages", secondary_key="outbound_messages", empty_text="暂无趋势数据"):
    if not rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'

    width = 680
    height = 248
    padding = 28
    primary_values = [row.get(primary_key, 0) for row in rows]
    secondary_values = [row.get(secondary_key, 0) for row in rows]
    primary_points = build_polyline_points(primary_values, width=width, height=height, padding=padding)
    secondary_points = build_polyline_points(secondary_values, width=width, height=height, padding=padding)

    if not primary_points:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'

    primary_polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in primary_points)
    secondary_polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in secondary_points)
    area_points = " ".join(
        [f"{primary_points[0][0]:.2f},{height - padding:.2f}"] +
        [f"{x:.2f},{y:.2f}" for x, y in primary_points] +
        [f"{primary_points[-1][0]:.2f},{height - padding:.2f}"]
    )

    labels = "".join(
        f'<span>{escape_text((row.get("date", "") or "--")[5:])}</span>'
        for row in rows
    )
    latest = rows[-1]
    delta = 0
    if len(rows) >= 2:
        delta = int(rows[-1].get(primary_key, 0)) - int(rows[-2].get(primary_key, 0))
    delta_prefix = "+" if delta > 0 else ""

    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4"></circle>'
        for x, y in primary_points
    )

    return (
        '<div class="trend-card">'
        '<div class="trend-card__head">'
        f'<div><span class="trend-card__eyebrow">Activity Pulse</span><h3>{escape_text(title)}</h3></div>'
        '<div class="trend-card__stats">'
        f'<div><strong>{escape_text(format_number(latest.get(primary_key, 0)))}</strong><span>最新消息量</span></div>'
        f'<div><strong>{escape_text(delta_prefix + format_number(delta))}</strong><span>较前一日变化</span></div>'
        "</div>"
        "</div>"
        '<svg class="trend-chart" viewBox="0 0 680 248" aria-hidden="true">'
        '<defs>'
        '<linearGradient id="trend-gradient" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#2bd4bf" stop-opacity="0.48"></stop>'
        '<stop offset="100%" stop-color="#2bd4bf" stop-opacity="0.04"></stop>'
        "</linearGradient>"
        "</defs>"
        f'<polyline class="trend-chart__area" fill="url(#trend-gradient)" points="{area_points}"></polyline>'
        f'<polyline class="trend-chart__line trend-chart__line--primary" fill="none" points="{primary_polyline}"></polyline>'
        f'<polyline class="trend-chart__line trend-chart__line--secondary" fill="none" points="{secondary_polyline}"></polyline>'
        f"{dots}"
        "</svg>"
        '<div class="trend-chart__labels">' + labels + "</div>"
        '<div class="trend-chart__legend">'
        '<span><i class="legend-dot legend-dot--sea"></i>总消息</span>'
        '<span><i class="legend-dot legend-dot--gold"></i>自己发出</span>'
        "</div>"
        "</div>"
    )


def render_day_story_cards(rows, empty_text="暂无日级特征数据"):
    if not rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    cards = []
    for row in rows[:6]:
        cards.append(
            '<article class="day-story">'
            f'<div class="day-story__date">{escape_text(row.get("date", "--"))}</div>'
            f'<div class="day-story__value">{escape_text(format_number(row.get("total_messages", 0)))}</div>'
            f'<div class="day-story__meta">峰值 {escape_text(str(row.get("peak_hour", "--")) + " 时")} · 活跃会话 {escape_text(format_number(row.get("active_chats", 0)))}</div>'
            f'<div class="day-story__body">{escape_text(clip_text(row.get("top_chat", "未知会话"), 24))}</div>'
            "</article>"
        )
    return '<div class="day-story-grid">' + "".join(cards) + "</div>"


def render_emotional_chat_list(rows, empty_text="暂无情绪热点会话"):
    if not rows:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'
    items = []
    for item in rows[:5]:
        score = int(item.get("emotion_score", 0))
        tone = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
        score_text = f"{score:+d}"
        items.append(
            '<li class="signal-list__item signal-list__item--compact">'
            f'<div class="signal-list__title">{escape_text(item.get("chat_name", "未知会话"))}</div>'
            '<div class="signal-list__body signal-list__body--tight">'
            f'<span class="score-badge score-badge--{escape_text(tone)}">{escape_text(score_text)}</span>'
            f'积极 {escape_text(item.get("positive", 0))} · 消极 {escape_text(item.get("negative", 0))} · 愤怒 {escape_text(item.get("angry", 0))}'
            "</div>"
            "</li>"
        )
    return '<ul class="signal-list">' + "".join(items) + "</ul>"


def render_persona_mode_card(title, mode, empty_text):
    mbti_mode = mode.get("mbti") or {}
    emotion_mode = mode.get("emotion") or {}
    speech_mode = mode.get("speech") or {}
    social_mode = mode.get("social") or {}
    rows = [
        ("MBTI", mbti_mode.get("mbti_type")),
        ("情绪底色", emotion_label(emotion_mode.get("dominant_emotion")) if emotion_mode.get("dominant_emotion") else None),
        ("高频表达", ((speech_mode.get("repeated_phrases") or [{}])[0].get("text"))),
        ("高频会话", ((social_mode.get("top_chats") or [[None]])[0][0])),
        ("响应时延", f"{format_number(social_mode.get('median_response_latency_minutes'), 2)} 分钟" if social_mode.get("median_response_latency_minutes") is not None else None),
    ]
    tone = emotion_tone(emotion_mode.get("dominant_emotion"))
    return (
        f'<article class="mode-card mode-card--{tone}">'
        f'<div class="mode-card__title">{escape_text(title)}</div>'
        f'{render_key_value_list(rows, empty_text=empty_text)}'
        "</article>"
    )


def spread_angles(start, end, count):
    if count <= 0:
        return []
    if count == 1:
        return [(start + end) / 2]
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def polar_point(cx, cy, radius, degrees):
    radians = math.radians(degrees)
    return (cx + math.cos(radians) * radius, cy + math.sin(radians) * radius)


def render_relationship_map(chat_rows, contact_rows, overview, social, empty_text="暂无社交关系图数据"):
    groups = [row for row in (chat_rows or []) if row.get("chat_type") == "group"][:5]
    contacts = (contact_rows or [])[:5]
    if not groups and not contacts:
        return f'<div class="empty-state">{escape_text(empty_text)}</div>'

    width = 860
    height = 520
    cx = 430
    cy = 250
    group_radius = 190
    contact_radius = 224
    center_width = 210
    center_height = 146
    group_max = max([max(1, int(row.get("total_messages", 1))) for row in groups] or [1])
    contact_max = max([max(1, int(row.get("total_messages", 1))) for row in contacts] or [1])
    group_angles = spread_angles(-146, -34, len(groups))
    contact_angles = spread_angles(146, 34, len(contacts))
    latency_value = social.get("median_response_latency_minutes")
    latency_text = f"{format_number(latency_value, 2)} 分钟响应" if latency_value is not None else "响应样本不足"

    line_rows = []
    node_rows = []
    default_subtitle = f"{overview.get('mbti_type') or '未知'} / {emotion_label(overview.get('dominant_emotion'))}"
    default_summary = f"{overview.get('total_messages', 0)} 条消息 · {latency_text}"
    default_attrs = build_html_data_attrs({
        "default_eyebrow": "Inspector",
        "default_title": "将鼠标移到节点上",
        "default_subtitle": default_subtitle,
        "default_summary": default_summary,
        "default_type": "会话中心",
        "default_messages": format_number(overview.get("total_messages", 0)),
        "default_business": format_number(overview.get("business_contact_count", 0)),
        "default_support": format_number(social.get("private_message_count", 0)),
        "default_active_days": format_number(overview.get("date_span_days", 0)),
        "default_self_ratio": "总览视角",
        "default_theme": "center",
    })

    for row, angle in zip(groups, group_angles):
        total = max(1, int(row.get("total_messages", 1)))
        ratio = total / group_max
        x, y = polar_point(cx, cy, group_radius, angle)
        width_px = 144 + ratio * 28
        height_px = 74 + ratio * 12
        left = x - width_px / 2
        top = y - height_px / 2
        business = int(row.get("business_signal_count", 0))
        support = int(row.get("support_signal_count", 0))
        thickness = 2.4 + ratio * 6.2
        line_rows.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" '
            f'class="relationship-map__line relationship-map__line--group" '
            f'style="stroke-width:{thickness:.2f}px"></line>'
        )
        badge_html = "".join(
            badge for badge in [
                f'<span class="relationship-node__badge relationship-node__badge--sea">商业 {business}</span>' if business else "",
                f'<span class="relationship-node__badge relationship-node__badge--gold">售后 {support}</span>' if support else "",
            ] if badge
        )
        data_attrs = build_html_data_attrs({
            "eyebrow": "Group Node",
            "title": row.get("chat_name", "未知群聊"),
            "subtitle": f"{total} 条消息 · 群聊场",
            "summary": f"活跃 {format_number(row.get('active_days', 0))} 天 · 平均 {format_number(row.get('avg_message_length', 0), 2)} 字 · 最近 {row.get('last_active_at') or '未知'}",
            "type": "高频群聊",
            "messages": total,
            "business": business,
            "support": support,
            "active_days": format_number(row.get("active_days", 0)),
            "self_ratio": format_percent(row.get("self_ratio", 0)),
            "theme": "group",
        })
        node_rows.append(
            f'<article class="relationship-node relationship-node--group" '
            f'tabindex="0" role="button" {data_attrs} '
            f'style="left:{left:.2f}px;top:{top:.2f}px;width:{width_px:.2f}px;height:{height_px:.2f}px;animation-delay:{angle / 36:.2f}s">'
            f'<div class="relationship-node__title">{escape_text(clip_text(row.get("chat_name", "未知群聊"), 18))}</div>'
            f'<div class="relationship-node__meta">{escape_text(str(total) + " 条消息")}</div>'
            f'<div class="relationship-node__badges">{badge_html}</div>'
            "</article>"
        )

    for row, angle in zip(contacts, contact_angles):
        total = max(1, int(row.get("total_messages", 1)))
        ratio = total / contact_max
        x, y = polar_point(cx, cy, contact_radius, angle)
        width_px = 132 + ratio * 26
        height_px = 70 + ratio * 10
        left = x - width_px / 2
        top = y - height_px / 2
        business = int(row.get("business_signal_count", 0))
        support = int(row.get("support_signal_count", 0))
        thickness = 2.0 + ratio * 5.4
        line_rows.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" '
            f'class="relationship-map__line relationship-map__line--contact" '
            f'style="stroke-width:{thickness:.2f}px"></line>'
        )
        badge_html = "".join(
            badge for badge in [
                f'<span class="relationship-node__badge relationship-node__badge--sea">商业 {business}</span>' if business else "",
                f'<span class="relationship-node__badge relationship-node__badge--gold">售后 {support}</span>' if support else "",
            ] if badge
        )
        data_attrs = build_html_data_attrs({
            "eyebrow": "Contact Node",
            "title": row.get("contact_name", "未知联系人"),
            "subtitle": f"{total} 条私聊 · 一对一关系",
            "summary": f"活跃 {format_number(row.get('active_days', 0))} 天 · 问题占比 {format_percent(row.get('question_ratio', 0))} · 自发 {format_percent(row.get('self_ratio', 0))}",
            "type": "高频私聊",
            "messages": total,
            "business": business,
            "support": support,
            "active_days": format_number(row.get("active_days", 0)),
            "self_ratio": format_percent(row.get("self_ratio", 0)),
            "theme": "contact",
        })
        node_rows.append(
            f'<article class="relationship-node relationship-node--contact" '
            f'tabindex="0" role="button" {data_attrs} '
            f'style="left:{left:.2f}px;top:{top:.2f}px;width:{width_px:.2f}px;height:{height_px:.2f}px;animation-delay:{angle / 42:.2f}s">'
            f'<div class="relationship-node__title">{escape_text(clip_text(row.get("contact_name", "未知联系人"), 16))}</div>'
            f'<div class="relationship-node__meta">{escape_text(str(total) + " 条私聊")}</div>'
            f'<div class="relationship-node__badges">{badge_html}</div>'
            "</article>"
        )

    center_left = cx - center_width / 2
    center_top = cy - center_height / 2
    return (
        f'<div class="relationship-map" {default_attrs}>'
        '<div class="relationship-map__ring relationship-map__ring--outer"></div>'
        '<div class="relationship-map__ring relationship-map__ring--inner"></div>'
        '<div class="relationship-map__label relationship-map__label--top">高频群聊场</div>'
        '<div class="relationship-map__label relationship-map__label--bottom">高频私聊场</div>'
        f'<svg class="relationship-map__svg" viewBox="0 0 {width} {height}" aria-hidden="true">'
        + "".join(line_rows) +
        f'<circle class="relationship-map__pulse" cx="{cx}" cy="{cy}" r="82"></circle>'
        "</svg>"
        f'<article class="relationship-node relationship-node--center" tabindex="0" role="button" data-reset-inspector="true" style="left:{center_left:.2f}px;top:{center_top:.2f}px;width:{center_width}px;height:{center_height}px">'
        '<div class="relationship-node__eyebrow">Self Core</div>'
        '<div class="relationship-node__self">你</div>'
        f'<div class="relationship-node__meta">{escape_text((overview.get("mbti_type") or "未知") + " / " + emotion_label(overview.get("dominant_emotion")))}</div>'
        f'<div class="relationship-node__summary">{escape_text(str(overview.get("total_messages", 0)) + " 条消息 · " + latency_text)}</div>'
        "</article>"
        '<aside class="relationship-inspector relationship-inspector--center">'
        '<div class="relationship-inspector__eyebrow">Inspector</div>'
        '<h3 class="relationship-inspector__title">将鼠标移到节点上</h3>'
        f'<div class="relationship-inspector__subtitle">{escape_text(default_subtitle)}</div>'
        f'<p class="relationship-inspector__summary">{escape_text(default_summary)}</p>'
        '<div class="relationship-inspector__grid">'
        '<div class="relationship-inspector__metric"><span>节点类型</span><strong data-inspector-field="type">会话中心</strong></div>'
        f'<div class="relationship-inspector__metric"><span>消息量</span><strong data-inspector-field="messages">{escape_text(format_number(overview.get("total_messages", 0)))}</strong></div>'
        f'<div class="relationship-inspector__metric"><span>商业</span><strong data-inspector-field="business">{escape_text(format_number(overview.get("business_contact_count", 0)))}</strong></div>'
        f'<div class="relationship-inspector__metric"><span>售后/私聊</span><strong data-inspector-field="support">{escape_text(format_number(social.get("private_message_count", 0)))}</strong></div>'
        f'<div class="relationship-inspector__metric"><span>观察天数</span><strong data-inspector-field="active_days">{escape_text(format_number(overview.get("date_span_days", 0)))}</strong></div>'
        '<div class="relationship-inspector__metric"><span>自发占比</span><strong data-inspector-field="self_ratio">总览视角</strong></div>'
        "</div>"
        '<button class="relationship-inspector__reset" type="button">重置到中心</button>'
        "</aside>"
        + "".join(node_rows) +
        "</div>"
    )


def render_html(payload):
    overview = payload.get("overview", {})
    sections = payload.get("sections", {})
    daily = sections.get("daily", {})
    customer = sections.get("customer", {})
    labels = sections.get("labels", {})
    features = sections.get("features", {})
    emotion = sections.get("emotion", {})
    mbti = sections.get("mbti", {})
    speech = sections.get("speech", {})
    social = sections.get("social", {})
    artifacts = payload.get("artifacts", {})
    activity_rows = features.get("daily_activity") or social.get("daily_activity") or []
    chat_leaderboard = features.get("chat_leaderboard") or []
    contact_leaderboard = features.get("contact_leaderboard") or []
    date_span_days = overview.get("date_span_days") or max(1, len(activity_rows) or 1)

    role_counts = customer.get("role_counts", {})
    role_rows = [
        (role_label("customer"), role_counts.get("customer", 0)),
        (role_label("vendor"), role_counts.get("vendor", 0)),
        (role_label("unknown"), role_counts.get("unknown", 0)),
    ]
    source_rows = [
        ("Payload", artifacts.get("payload_path")),
        ("日报", artifacts.get("daily_report_path")),
        ("客户报告", artifacts.get("customer_report_path")),
        ("情绪报告", artifacts.get("emotion_report_path")),
        ("MBTI 报告", artifacts.get("mbti_report_path")),
        ("口癖报告", artifacts.get("speech_report_path")),
        ("社交图谱", artifacts.get("social_report_path")),
        ("标签文件", artifacts.get("labels_path")),
        ("日特征", artifacts.get("feature_files", {}).get("daily_features")),
        ("会话特征", artifacts.get("feature_files", {}).get("chat_features")),
        ("联系人特征", artifacts.get("feature_files", {}).get("contact_features")),
    ]
    top_group_row = next((row for row in chat_leaderboard if row.get("chat_type") == "group"), None)
    top_contact_row = contact_leaderboard[0] if contact_leaderboard else None
    busiest_business_chat = max(chat_leaderboard, key=lambda row: int(row.get("business_signal_count", 0)), default=None)
    busiest_support_chat = max(chat_leaderboard, key=lambda row: int(row.get("support_signal_count", 0)), default=None)
    relationship_rows = [
        ("最强群聊", top_group_row and top_group_row.get("chat_name")),
        ("最强私聊", top_contact_row and top_contact_row.get("contact_name")),
        ("熬夜占比", format_percent(social.get("night_message_ratio", 0))),
        ("中位响应", f"{format_number(social.get('median_response_latency_minutes'), 2)} 分钟" if social.get("median_response_latency_minutes") is not None else None),
        ("商业密度群", busiest_business_chat and busiest_business_chat.get("chat_name")),
        ("售后压力群", busiest_support_chat and busiest_support_chat.get("chat_name")),
    ]
    emotion_rows = [
        ("positive", emotion.get("emotion_distribution", {}).get("positive", 0)),
        ("negative", emotion.get("emotion_distribution", {}).get("negative", 0)),
        ("anxious", emotion.get("emotion_distribution", {}).get("anxious", 0)),
        ("angry", emotion.get("emotion_distribution", {}).get("angry", 0)),
        ("neutral", emotion.get("emotion_distribution", {}).get("neutral", 0)),
    ]
    speech_rows = [
        f"{item.get('text', '')}（{item.get('count', 0)}次）"
        for item in speech.get("repeated_phrases", [])[:6]
    ]
    social_rows = [
        ("中位响应时延", None if social.get("median_response_latency_minutes") is None else f"{social.get('median_response_latency_minutes')} 分钟"),
        ("群聊消息", social.get("group_message_count")),
        ("私聊消息", social.get("private_message_count")),
        ("平均消息长度", overview.get("avg_message_length")),
        ("主导情绪", emotion_label(overview.get("dominant_emotion"))),
    ]
    mbti_rows = [
        ("推测类型", overview.get("mbti_type") or mbti.get("mbti_type")),
        ("EI", mbti.get("dimensions", {}).get("EI", {}).get("letter")),
        ("SN", mbti.get("dimensions", {}).get("SN", {}).get("letter")),
        ("TF", mbti.get("dimensions", {}).get("TF", {}).get("letter")),
        ("JP", mbti.get("dimensions", {}).get("JP", {}).get("letter")),
    ]
    work_mode = {
        "mbti": mbti.get("persona_modes", {}).get("work"),
        "emotion": emotion.get("persona_modes", {}).get("work"),
        "speech": speech.get("persona_modes", {}).get("work"),
        "social": social.get("persona_modes", {}).get("work"),
    }
    life_mode = {
        "mbti": mbti.get("persona_modes", {}).get("life"),
        "emotion": emotion.get("persona_modes", {}).get("life"),
        "speech": speech.get("persona_modes", {}).get("life"),
        "social": social.get("persona_modes", {}).get("life"),
    }

    emotion_chart_rows = [
        ("积极", emotion.get("emotion_distribution", {}).get("positive", 0), EMOTION_COLORS["positive"]),
        ("平稳", emotion.get("emotion_distribution", {}).get("neutral", 0), EMOTION_COLORS["neutral"]),
        ("消极", emotion.get("emotion_distribution", {}).get("negative", 0), EMOTION_COLORS["negative"]),
        ("焦虑", emotion.get("emotion_distribution", {}).get("anxious", 0), EMOTION_COLORS["anxious"]),
        ("愤怒", emotion.get("emotion_distribution", {}).get("angry", 0), EMOTION_COLORS["angry"]),
    ]
    hero_chips = render_stat_chips([
        ("观察区间", f"{format_number(date_span_days)} 天", "ink"),
        ("人格推测", overview.get("mbti_type", "未知"), "sea"),
        ("情绪底色", emotion_label(overview.get("dominant_emotion", "unknown")), emotion_tone(overview.get("dominant_emotion"))),
        ("响应时延", f"{format_number(overview.get('median_response_latency_minutes'), 2)} 分钟", "gold"),
    ])
    metric_cards = "".join([
        render_metric_card("总消息", format_number(overview.get("total_messages", 0)), tone="ink", detail="全量会话脉冲"),
        render_metric_card("文本消息", format_number(overview.get("text_messages", 0)), tone="sea", detail="可解析语义样本"),
        render_metric_card("活跃会话", format_number(overview.get("active_chat_count", 0)), tone="gold", detail="本周期触达范围"),
        render_metric_card("私聊联系人", format_number(overview.get("total_private_contacts", 0)), tone="ink", detail="一对一关系池"),
        render_metric_card("商机联系人", format_number(overview.get("business_contact_count", 0)), tone="sea", detail="高意向客群"),
        render_metric_card("待跟进", format_number(overview.get("pending_followup_count", 0)), tone="gold", detail="需要继续推进"),
    ])
    highlight_rows = render_key_value_list([
        ("群聊消息", format_number(overview.get("group_message_count", 0))),
        ("私聊消息", format_number(overview.get("private_message_count", 0))),
        ("平均长度", format_number(overview.get("avg_message_length"), 2)),
        ("生成时间", format_datetime(payload.get("generated_at"))),
    ], empty_text="暂无摘要指标")
    source_rows = [
        ("Payload", artifacts.get("payload_path")),
        ("日报", artifacts.get("daily_report_path")),
        ("客户报告", artifacts.get("customer_report_path")),
        ("情绪报告", artifacts.get("emotion_report_path")),
        ("MBTI 报告", artifacts.get("mbti_report_path")),
        ("口癖报告", artifacts.get("speech_report_path")),
        ("社交图谱", artifacts.get("social_report_path")),
        ("标签文件", artifacts.get("labels_path")),
    ]

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WeChat Insight Dashboard</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --bg-deep: #ece5d7;
      --panel: rgba(255, 250, 244, 0.74);
      --panel-strong: rgba(255, 250, 244, 0.92);
      --text: #172121;
      --muted: #5f6868;
      --ink: #17313e;
      --sea: #0f766e;
      --gold: #b7791f;
      --rose: #b42318;
      --aqua: #2bd4bf;
      --line: rgba(23, 33, 33, 0.08);
      --shadow: 0 28px 72px rgba(16, 24, 40, 0.10);
      --radius: 28px;
    }}
    * {{ box-sizing: border-box; }}
    html {{
      scroll-behavior: smooth;
    }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 10% 12%, rgba(43, 212, 191, 0.22), transparent 28%),
        radial-gradient(circle at 88% 14%, rgba(183, 121, 31, 0.18), transparent 26%),
        radial-gradient(circle at 50% 48%, rgba(23, 49, 62, 0.08), transparent 36%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
      min-height: 100vh;
    }}
    .page {{
      position: relative;
      width: min(1240px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }}
    .page::before,
    .page::after {{
      content: "";
      position: fixed;
      z-index: -1;
      inset: auto;
      width: 360px;
      height: 360px;
      border-radius: 999px;
      filter: blur(72px);
      opacity: 0.42;
      animation: drift 18s ease-in-out infinite;
      pointer-events: none;
    }}
    .page::before {{
      top: 48px;
      right: -70px;
      background: rgba(43, 212, 191, 0.30);
    }}
    .page::after {{
      left: -120px;
      top: 320px;
      background: rgba(183, 121, 31, 0.18);
      animation-delay: -6s;
    }}
    .hero {{
      position: relative;
      padding: 32px;
      border: 1px solid rgba(255,255,255,0.48);
      border-radius: 36px;
      background:
        radial-gradient(circle at 92% 24%, rgba(43, 212, 191, 0.18), transparent 22%),
        radial-gradient(circle at 78% 82%, rgba(183, 121, 31, 0.12), transparent 26%),
        linear-gradient(135deg, rgba(255,250,244,0.94), rgba(244,239,231,0.74));
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(120deg, rgba(255,255,255,0.18), transparent 40%),
        radial-gradient(circle at top right, rgba(23,49,62,0.06), transparent 26%);
      pointer-events: none;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -52px -68px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(15,118,110,0.18), transparent 72%);
      pointer-events: none;
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--sea);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .sr-only {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }}
    .hero__grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
      gap: 24px;
      position: relative;
      z-index: 1;
    }}
    h1 {{
      margin: 0;
      font-family: "Avenir Next", "IBM Plex Sans", sans-serif;
      font-size: clamp(36px, 6vw, 70px);
      line-height: 0.92;
      letter-spacing: -0.04em;
      max-width: 760px;
    }}
    .gradient-text {{
      background: linear-gradient(135deg, #17313e 0%, #0f766e 55%, #2bd4bf 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }}
    .hero__lead {{
      margin: 14px 0 0;
      color: var(--muted);
      font-size: 16px;
      max-width: 720px;
      line-height: 1.7;
    }}
    .hero__meta {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .stat-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }}
    .stat-chip {{
      min-width: 132px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.42);
      backdrop-filter: blur(10px);
      background: rgba(255,255,255,0.46);
      box-shadow: 0 10px 30px rgba(16, 24, 40, 0.08);
    }}
    .stat-chip span {{
      display: block;
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.82);
      margin-bottom: 8px;
    }}
    .stat-chip strong {{
      display: block;
      font-size: 20px;
      line-height: 1.1;
      letter-spacing: -0.04em;
      color: #fffaf1;
    }}
    .stat-chip--ink {{
      background: linear-gradient(135deg, #17313e, #264858);
    }}
    .stat-chip--sea {{
      background: linear-gradient(135deg, #0f766e, #0d9488);
    }}
    .stat-chip--gold {{
      background: linear-gradient(135deg, #b7791f, #d69e2e);
    }}
    .stat-chip--rose {{
      background: linear-gradient(135deg, #9f1d1d, #c2410c);
    }}
    .hero-orbit {{
      position: relative;
      padding: 22px;
      border-radius: 28px;
      background: linear-gradient(160deg, rgba(23,49,62,0.96), rgba(15,118,110,0.88));
      color: #f8f4ec;
      overflow: hidden;
      box-shadow: 0 20px 48px rgba(15, 23, 42, 0.24);
    }}
    .hero-orbit::before {{
      content: "";
      position: absolute;
      inset: -20% auto auto -18%;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(43,212,191,0.24), transparent 62%);
    }}
    .hero-orbit__eyebrow {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: rgba(248,244,236,0.74);
    }}
    .hero-orbit__value {{
      margin-top: 12px;
      font-size: clamp(44px, 8vw, 72px);
      line-height: 0.9;
      letter-spacing: -0.06em;
      font-weight: 700;
    }}
    .hero-orbit__caption {{
      margin-top: 10px;
      color: rgba(248,244,236,0.78);
      font-size: 14px;
      line-height: 1.6;
      max-width: 320px;
    }}
    .hero-orbit__spark {{
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid rgba(255,255,255,0.12);
    }}
    .hero-orbit__grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .orbit-chip {{
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.10);
    }}
    .orbit-chip span {{
      display: block;
      font-size: 12px;
      color: rgba(248,244,236,0.68);
      margin-bottom: 6px;
    }}
    .orbit-chip strong {{
      font-size: 18px;
      letter-spacing: -0.03em;
    }}
    .grid {{
      display: grid;
      gap: 18px;
      margin-top: 18px;
    }}
    .grid--metrics {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }}
    .grid--two {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .grid--story {{
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
      align-items: start;
    }}
    .grid--triple {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel);
      backdrop-filter: blur(12px);
      padding: 24px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}
    .panel::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 1px;
      background: linear-gradient(90deg, rgba(43,212,191,0), rgba(43,212,191,0.45), rgba(43,212,191,0));
      opacity: 0.9;
    }}
    .panel h2 {{
      margin: 0;
      font-size: 21px;
      letter-spacing: -0.03em;
    }}
    .panel__intro {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }}
    .metric-card {{
      min-height: 138px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.35);
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: var(--shadow);
    }}
    .metric-card--ink {{ background: linear-gradient(135deg, #1f3642, #254b59); color: #f7f2e9; }}
    .metric-card--sea {{ background: linear-gradient(135deg, #0f766e, #0d9488); color: #f7f2e9; }}
    .metric-card--gold {{ background: linear-gradient(135deg, #b7791f, #d69e2e); color: #fff9ef; }}
    .metric-card__label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      opacity: 0.82;
    }}
    .metric-card__value {{
      font-size: clamp(24px, 4vw, 36px);
      line-height: 1;
      font-weight: 700;
      letter-spacing: -0.06em;
    }}
    .metric-card__detail {{
      font-size: 12px;
      opacity: 0.82;
    }}
    .bar-list,
    .bullet-list,
    .signal-list,
    .meta-list,
    .legend-list {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .bar-list__item + .bar-list__item,
    .signal-list__item + .signal-list__item,
    .meta-list__item + .meta-list__item,
    .legend-list__item + .legend-list__item {{
      margin-top: 14px;
    }}
    .bar-list__header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 14px;
      margin-bottom: 8px;
    }}
    .bar-list__track {{
      width: 100%;
      height: 9px;
      border-radius: 999px;
      background: rgba(23,49,62,0.08);
      overflow: hidden;
    }}
    .bar-list__fill {{
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #2bd4bf, #17313e);
    }}
    .bullet-list li,
    .signal-list__item,
    .meta-list__item {{
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .bullet-list li:first-child,
    .signal-list__item:first-child,
    .meta-list__item:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .bullet-list li {{
      color: var(--muted);
      line-height: 1.7;
    }}
    .signal-list__title {{
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .signal-list__body {{
      color: var(--text);
      line-height: 1.6;
    }}
    .signal-list__meta {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .signal-list__item--compact {{
      padding-top: 10px;
    }}
    .signal-list__body--tight {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .meta-list__item {{
      display: grid;
      grid-template-columns: 84px 1fr;
      gap: 12px;
      align-items: start;
      font-size: 14px;
    }}
    .meta-list__item span {{
      color: var(--muted);
    }}
    code {{
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      font-size: 12px;
      background: rgba(23,33,33,0.04);
      border-radius: 10px;
      padding: 6px 8px;
      word-break: break-all;
    }}
    .empty-state {{
      color: var(--muted);
      font-size: 14px;
    }}
    .section-kicker {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 20px;
      margin: 34px 4px 10px;
    }}
    .section-kicker__title {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--sea);
      font-weight: 700;
    }}
    .section-kicker__subtitle {{
      font-size: 13px;
      color: var(--muted);
    }}
    .trend-card {{
      position: relative;
    }}
    .trend-card__head {{
      display: flex;
      gap: 20px;
      align-items: end;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .trend-card__eyebrow {{
      display: block;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--sea);
      margin-bottom: 8px;
    }}
    .trend-card__head h3 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: -0.04em;
    }}
    .trend-card__stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .trend-card__stats div {{
      min-width: 120px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(23,49,62,0.05);
    }}
    .trend-card__stats strong {{
      display: block;
      font-size: 22px;
      line-height: 1.05;
      letter-spacing: -0.04em;
    }}
    .trend-card__stats span {{
      display: block;
      margin-top: 6px;
      font-size: 12px;
      color: var(--muted);
    }}
    .trend-chart {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .trend-chart__area {{
      opacity: 1;
    }}
    .trend-chart__line {{
      stroke-width: 4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .trend-chart__line--primary {{
      stroke: #0f766e;
    }}
    .trend-chart__line--secondary {{
      stroke: #d69e2e;
      stroke-dasharray: 6 8;
      opacity: 0.92;
    }}
    .trend-chart circle {{
      fill: #0f766e;
      stroke: rgba(255,255,255,0.82);
      stroke-width: 2;
    }}
    .trend-chart__labels,
    .trend-chart__legend {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .trend-chart__labels {{
      justify-content: space-between;
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }}
    .trend-chart__legend {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }}
    .legend-dot {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      margin-right: 6px;
    }}
    .legend-dot--sea {{
      background: #0f766e;
    }}
    .legend-dot--gold {{
      background: #d69e2e;
    }}
    .day-story-grid {{
      display: grid;
      gap: 12px;
    }}
    .day-story {{
      padding: 16px;
      border-radius: 20px;
      background: rgba(255,255,255,0.54);
      border: 1px solid rgba(23,33,33,0.06);
    }}
    .day-story__date {{
      color: var(--sea);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .day-story__value {{
      margin-top: 10px;
      font-size: 34px;
      line-height: 0.92;
      letter-spacing: -0.05em;
      font-weight: 700;
    }}
    .day-story__meta {{
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted);
    }}
    .day-story__body {{
      margin-top: 12px;
      font-size: 14px;
      line-height: 1.6;
    }}
    .donut-layout {{
      display: grid;
      grid-template-columns: 210px minmax(0, 1fr);
      gap: 22px;
      align-items: center;
    }}
    .donut {{
      position: relative;
      width: 200px;
      height: 200px;
      margin: 0 auto;
    }}
    .donut__ring {{
      width: 100%;
      height: 100%;
      border-radius: 999px;
      box-shadow: inset 0 0 0 1px rgba(23,33,33,0.06);
    }}
    .donut__core {{
      position: absolute;
      inset: 24px;
      border-radius: 999px;
      background: rgba(255,250,244,0.92);
      display: grid;
      place-items: center;
      text-align: center;
      box-shadow: inset 0 0 0 1px rgba(23,33,33,0.04);
    }}
    .donut__core strong {{
      display: block;
      font-size: 34px;
      line-height: 0.9;
      letter-spacing: -0.05em;
    }}
    .donut__core span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    .legend-list__item {{
      display: grid;
      grid-template-columns: 14px 1fr auto auto;
      gap: 10px;
      align-items: center;
      font-size: 14px;
    }}
    .legend-list__swatch {{
      width: 14px;
      height: 14px;
      border-radius: 999px;
    }}
    .legend-list__label {{
      color: var(--muted);
    }}
    .legend-list__item em {{
      font-style: normal;
      color: var(--muted);
      font-size: 12px;
    }}
    .dimension-grid {{
      display: grid;
      gap: 14px;
    }}
    .dimension-card {{
      padding: 16px;
      border-radius: 20px;
      background: rgba(255,255,255,0.54);
      border: 1px solid rgba(23,33,33,0.06);
    }}
    .dimension-card__head,
    .dimension-card__meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}
    .dimension-card__head strong {{
      font-size: 28px;
      letter-spacing: -0.04em;
    }}
    .dimension-card__meta {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
    }}
    .dimension-card__track {{
      position: relative;
      display: flex;
      gap: 4px;
      margin-top: 14px;
      height: 10px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(23,33,33,0.06);
    }}
    .dimension-card__fill {{
      display: block;
      height: 100%;
    }}
    .dimension-card__fill--left {{
      background: linear-gradient(90deg, #0f766e, #2bd4bf);
    }}
    .dimension-card__fill--right {{
      background: linear-gradient(90deg, #d69e2e, #f5b546);
    }}
    .phrase-cloud {{
      --phrase-guide-color: rgba(23,33,33,0.12);
      --phrase-track-stroke: rgba(23,49,62,0.12);
      --phrase-ellipse-stroke: rgba(15,118,110,0.18);
      --phrase-active-line: rgba(15,118,110,0.62);
      --phrase-active-guide: rgba(15,118,110,0.34);
      --phrase-active-glow: rgba(43,212,191,0.16);
      position: relative;
      min-height: 520px;
      padding: 22px;
      border-radius: 28px;
      overflow: hidden;
      isolation: isolate;
      background:
        radial-gradient(circle at 18% 22%, rgba(43,212,191,0.16), transparent 24%),
        radial-gradient(circle at 84% 76%, rgba(214,158,46,0.14), transparent 26%),
        linear-gradient(145deg, rgba(255,251,245,0.88), rgba(240,247,245,0.74));
      border: 1px solid rgba(255,255,255,0.52);
    }}
    .phrase-cloud::before,
    .phrase-cloud::after {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
    }}
    .phrase-cloud::before {{
      background:
        linear-gradient(110deg, rgba(255,255,255,0.24), transparent 38%),
        linear-gradient(180deg, rgba(23,33,33,0.02), transparent 32%, rgba(23,33,33,0.03) 100%);
    }}
    .phrase-cloud::after {{
      inset: 18px;
      border-radius: 22px;
      border: 1px solid rgba(23,33,33,0.05);
      opacity: 0.7;
    }}
    .phrase-cloud__guides {{
      position: absolute;
      inset: 18px;
      display: grid;
      grid-template-rows: repeat(3, 1fr);
      pointer-events: none;
    }}
    .phrase-cloud__guides span {{
      align-self: center;
      border-top: 1px dashed var(--phrase-guide-color);
      opacity: 0.24;
      transition:
        border-color 180ms ease,
        opacity 180ms ease,
        filter 180ms ease,
        transform 180ms ease;
    }}
    .phrase-cloud__guides span:nth-child(2) {{
      width: 78%;
    }}
    .phrase-cloud__guides span:nth-child(3) {{
      width: 62%;
    }}
    .phrase-cloud__guides span:nth-child(even) {{
      justify-self: end;
    }}
    .phrase-cloud__paths {{
      position: absolute;
      inset: 12px;
      width: calc(100% - 24px);
      height: calc(100% - 24px);
      pointer-events: none;
    }}
    .phrase-cloud__paths path,
    .phrase-cloud__paths ellipse {{
      fill: none;
      stroke: var(--phrase-track-stroke);
      stroke-width: 1.2;
      stroke-linecap: round;
      stroke-dasharray: 4 7;
      opacity: 0.52;
      transition:
        stroke 180ms ease,
        stroke-width 180ms ease,
        opacity 180ms ease,
        filter 180ms ease;
    }}
    .phrase-cloud__paths ellipse {{
      stroke: var(--phrase-ellipse-stroke);
      stroke-width: 1.6;
      stroke-dasharray: none;
      opacity: 0.82;
    }}
    .phrase-cloud--tone-sea {{
      --phrase-active-line: rgba(15,118,110,0.62);
      --phrase-active-guide: rgba(15,118,110,0.34);
      --phrase-active-glow: rgba(43,212,191,0.16);
      --phrase-ellipse-stroke: rgba(15,118,110,0.22);
    }}
    .phrase-cloud--tone-ink {{
      --phrase-active-line: rgba(23,49,62,0.68);
      --phrase-active-guide: rgba(23,49,62,0.32);
      --phrase-active-glow: rgba(129,170,194,0.14);
      --phrase-ellipse-stroke: rgba(23,49,62,0.2);
    }}
    .phrase-cloud--tone-gold {{
      --phrase-active-line: rgba(183,121,31,0.7);
      --phrase-active-guide: rgba(183,121,31,0.34);
      --phrase-active-glow: rgba(245,181,70,0.18);
      --phrase-ellipse-stroke: rgba(183,121,31,0.22);
    }}
    .phrase-cloud--lane-top .phrase-cloud__paths path:nth-of-type(1),
    .phrase-cloud--lane-mid .phrase-cloud__paths path:nth-of-type(2),
    .phrase-cloud--lane-bottom .phrase-cloud__paths path:nth-of-type(3) {{
      stroke: var(--phrase-active-line);
      stroke-width: 2.6;
      opacity: 1;
      filter: drop-shadow(0 0 10px var(--phrase-active-glow));
    }}
    .phrase-cloud--lane-top .phrase-cloud__guides span:nth-child(1),
    .phrase-cloud--lane-mid .phrase-cloud__guides span:nth-child(2),
    .phrase-cloud--lane-bottom .phrase-cloud__guides span:nth-child(3) {{
      border-top-color: var(--phrase-active-guide);
      opacity: 0.92;
      filter: drop-shadow(0 0 8px var(--phrase-active-glow));
      transform: translateX(-4px);
    }}
    .phrase-cloud__core {{
      position: absolute;
      left: 50%;
      top: 48%;
      z-index: 1;
      width: min(36%, 240px);
      min-height: 140px;
      transform: translate(-50%, -50%);
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 8px;
      padding: 22px 24px;
      border-radius: 28px;
      text-align: center;
      color: #f5f0e7;
      background:
        radial-gradient(circle at 50% 18%, rgba(43,212,191,0.26), transparent 42%),
        linear-gradient(160deg, rgba(23,49,62,0.96), rgba(15,118,110,0.84));
      box-shadow:
        0 24px 60px rgba(16,24,40,0.18),
        inset 0 1px 0 rgba(255,255,255,0.12);
    }}
    .phrase-cloud__core--sea {{
      background:
        radial-gradient(circle at 50% 18%, rgba(43,212,191,0.26), transparent 42%),
        linear-gradient(160deg, rgba(23,49,62,0.96), rgba(15,118,110,0.84));
    }}
    .phrase-cloud__core--ink {{
      background:
        radial-gradient(circle at 50% 20%, rgba(129,170,194,0.24), transparent 44%),
        linear-gradient(160deg, rgba(18,31,39,0.98), rgba(34,61,76,0.88));
    }}
    .phrase-cloud__core--gold {{
      background:
        radial-gradient(circle at 50% 18%, rgba(245,181,70,0.28), transparent 42%),
        linear-gradient(160deg, rgba(89,51,10,0.96), rgba(183,121,31,0.88));
    }}
    .phrase-cloud__core span,
    .phrase-cloud__core small {{
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      opacity: 0.72;
    }}
    .phrase-cloud__core strong {{
      font-size: 28px;
      line-height: 0.96;
      letter-spacing: -0.05em;
      font-family: "Avenir Next", "IBM Plex Sans", sans-serif;
      text-wrap: balance;
    }}
    .phrase-cloud__core b {{
      font-size: 30px;
      line-height: 1;
      letter-spacing: -0.04em;
      color: #ffffff;
    }}
    .phrase-cloud__core small {{
      line-height: 1.45;
      text-transform: none;
      letter-spacing: 0.04em;
      opacity: 0.8;
    }}
    .phrase-chip {{
      --phrase-accent: #17313e;
      --phrase-surface: rgba(239,247,247,0.78);
      position: absolute;
      left: var(--x);
      top: var(--y);
      z-index: 1;
      width: var(--width);
      min-height: 118px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 18px;
      border-radius: 24px;
      background:
        linear-gradient(160deg, rgba(255,255,255,0.84), var(--phrase-surface)),
        linear-gradient(140deg, rgba(255,255,255,0.12), transparent 72%);
      border: 1px solid rgba(255,255,255,0.62);
      box-shadow:
        0 18px 42px rgba(16,24,40,0.08),
        inset 0 1px 0 rgba(255,255,255,0.6);
      color: var(--phrase-accent);
      transform: translate3d(var(--drift-x), var(--drift-y), 0) rotate(var(--rotate));
      animation: phrase-drift var(--duration) ease-in-out infinite alternate;
      animation-delay: var(--delay);
      backdrop-filter: blur(12px);
      transition: box-shadow 180ms ease, border-color 180ms ease, filter 180ms ease;
      outline: none;
    }}
    .phrase-chip::before {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background: linear-gradient(125deg, rgba(255,255,255,0.2), transparent 42%);
      pointer-events: none;
    }}
    .phrase-chip::after {{
      content: "";
      position: absolute;
      top: 14px;
      right: 14px;
      width: 11px;
      height: 11px;
      border-radius: 999px;
      background: var(--phrase-accent);
      opacity: 0.9;
    }}
    .phrase-chip--ink {{
      --phrase-accent: #17313e;
      --phrase-surface: rgba(239,247,247,0.78);
    }}
    .phrase-chip--ink::after {{
      box-shadow: 0 0 22px rgba(23,49,62,0.16);
    }}
    .phrase-chip--sea {{
      --phrase-accent: #0f766e;
      --phrase-surface: rgba(228,249,245,0.78);
    }}
    .phrase-chip--sea::after {{
      box-shadow: 0 0 24px rgba(43,212,191,0.24);
    }}
    .phrase-chip--gold {{
      --phrase-accent: #b7791f;
      --phrase-surface: rgba(255,244,218,0.82);
    }}
    .phrase-chip--gold::after {{
      box-shadow: 0 0 24px rgba(214,158,46,0.22);
    }}
    .phrase-chip--active {{
      z-index: 3;
      animation-play-state: paused;
      filter: saturate(1.05);
    }}
    .phrase-chip--ink.phrase-chip--active {{
      border-color: rgba(23,49,62,0.18);
      box-shadow:
        0 26px 56px rgba(16,24,40,0.14),
        inset 0 1px 0 rgba(255,255,255,0.66);
    }}
    .phrase-chip--sea.phrase-chip--active {{
      border-color: rgba(15,118,110,0.22);
      box-shadow:
        0 26px 56px rgba(16,24,40,0.14),
        0 0 0 1px rgba(43,212,191,0.08),
        inset 0 1px 0 rgba(255,255,255,0.66);
    }}
    .phrase-chip--gold.phrase-chip--active {{
      border-color: rgba(183,121,31,0.22);
      box-shadow:
        0 26px 56px rgba(16,24,40,0.14),
        0 0 0 1px rgba(245,181,70,0.08),
        inset 0 1px 0 rgba(255,255,255,0.66);
    }}
    .phrase-chip__label {{
      position: relative;
      z-index: 1;
      display: block;
      line-height: 0.94;
      letter-spacing: -0.05em;
      font-family: "Avenir Next", "IBM Plex Sans", sans-serif;
      overflow-wrap: anywhere;
    }}
    .phrase-chip__rail {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    .phrase-chip__rail i {{
      display: block;
      height: 2px;
      border-radius: 999px;
      background: linear-gradient(90deg, currentColor, transparent);
      opacity: 0.18;
    }}
    .phrase-chip__rail i:first-child {{
      width: 46%;
    }}
    .phrase-chip__rail i:last-child {{
      width: 22%;
    }}
    .phrase-chip__count {{
      font-style: normal;
      font-size: 0.72rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    @keyframes phrase-drift {{
      0% {{
        transform: translate3d(var(--drift-x), var(--drift-y), 0) rotate(var(--rotate));
      }}
      100% {{
        transform: translate3d(calc(var(--drift-x) * -0.55), calc(var(--drift-y) * -0.75 - 5px), 0) rotate(calc(var(--rotate) * -0.45));
      }}
    }}
    .relationship-map {{
      position: relative;
      min-height: 520px;
      border-radius: 30px;
      overflow: hidden;
      background:
        radial-gradient(circle at center, rgba(43,212,191,0.10), transparent 26%),
        linear-gradient(180deg, rgba(255,255,255,0.18), rgba(255,255,255,0.04));
      border: 1px solid rgba(23,33,33,0.05);
    }}
    .relationship-map__svg {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }}
    .relationship-map__line {{
      fill: none;
      stroke-linecap: round;
      opacity: 0.9;
    }}
    .relationship-map__line--group {{
      stroke: rgba(43,212,191,0.50);
    }}
    .relationship-map__line--contact {{
      stroke: rgba(214,158,46,0.44);
    }}
    .relationship-map__pulse {{
      fill: rgba(15,118,110,0.10);
      stroke: rgba(15,118,110,0.18);
      stroke-width: 1.5;
    }}
    .relationship-map__ring {{
      position: absolute;
      inset: 50% auto auto 50%;
      border-radius: 999px;
      border: 1px dashed rgba(23,49,62,0.10);
      transform: translate(-50%, -50%);
    }}
    .relationship-map__ring--inner {{
      width: 380px;
      height: 380px;
    }}
    .relationship-map__ring--outer {{
      width: 448px;
      height: 448px;
    }}
    .relationship-map__label {{
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .relationship-map__label--top {{
      top: 26px;
    }}
    .relationship-map__label--bottom {{
      bottom: 26px;
    }}
    .relationship-node {{
      position: absolute;
      padding: 12px 14px;
      border-radius: 20px;
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,0.42);
      box-shadow: 0 18px 32px rgba(16, 24, 40, 0.08);
      overflow: hidden;
      transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }}
    .relationship-node::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(140deg, rgba(255,255,255,0.16), transparent 46%);
      pointer-events: none;
    }}
    .relationship-node--group {{
      background: linear-gradient(145deg, rgba(15,118,110,0.86), rgba(23,49,62,0.76));
      color: #f8f4ec;
      animation: relationship-float 8s ease-in-out infinite;
    }}
    .relationship-node--contact {{
      background: linear-gradient(145deg, rgba(183,121,31,0.84), rgba(139,92,20,0.78));
      color: #fff9ef;
      animation: relationship-float 9.5s ease-in-out infinite;
    }}
    .relationship-node--center {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      border-radius: 28px;
      background: linear-gradient(155deg, #17313e, #0f766e);
      color: #f8f4ec;
      box-shadow: 0 24px 48px rgba(15, 23, 42, 0.22);
    }}
    .relationship-node__eyebrow {{
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      opacity: 0.72;
      margin-bottom: 8px;
    }}
    .relationship-node__self {{
      font-size: 42px;
      line-height: 0.94;
      letter-spacing: -0.06em;
      font-weight: 700;
    }}
    .relationship-node__title {{
      position: relative;
      z-index: 1;
      font-size: 15px;
      line-height: 1.3;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .relationship-node__meta {{
      position: relative;
      z-index: 1;
      margin-top: 8px;
      font-size: 12px;
      opacity: 0.86;
      line-height: 1.45;
    }}
    .relationship-node__summary {{
      position: relative;
      z-index: 1;
      margin-top: 10px;
      font-size: 12px;
      line-height: 1.45;
      opacity: 0.86;
    }}
    .relationship-node__badges {{
      position: relative;
      z-index: 1;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}
    .relationship-node__badge {{
      display: inline-flex;
      align-items: center;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 11px;
      line-height: 1;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.12);
    }}
    .relationship-node__badge--sea {{
      color: #d8fff8;
    }}
    .relationship-node__badge--gold {{
      color: #fff1cc;
    }}
    .relationship-node:hover,
    .relationship-node:focus-visible,
    .relationship-node.is-active {{
      transform: translateY(-6px) scale(1.02);
      box-shadow: 0 26px 40px rgba(16, 24, 40, 0.16);
      border-color: rgba(255,255,255,0.68);
      z-index: 4;
    }}
    .relationship-node--center:hover,
    .relationship-node--center:focus-visible,
    .relationship-node--center.is-active {{
      transform: translateY(-4px) scale(1.01);
    }}
    .relationship-inspector {{
      position: absolute;
      right: 18px;
      bottom: 18px;
      width: min(320px, calc(100% - 36px));
      padding: 18px;
      border-radius: 22px;
      background: rgba(255,250,244,0.82);
      border: 1px solid rgba(255,255,255,0.55);
      backdrop-filter: blur(16px);
      box-shadow: 0 18px 38px rgba(16, 24, 40, 0.12);
      z-index: 3;
      transition: background 180ms ease, transform 180ms ease, border-color 180ms ease;
    }}
    .relationship-inspector--group {{
      background: rgba(232, 255, 250, 0.82);
      border-color: rgba(43, 212, 191, 0.32);
    }}
    .relationship-inspector--contact {{
      background: rgba(255, 247, 231, 0.86);
      border-color: rgba(214, 158, 46, 0.34);
    }}
    .relationship-inspector--center {{
      background: rgba(255,250,244,0.82);
      border-color: rgba(255,255,255,0.55);
    }}
    .relationship-inspector__eyebrow {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--sea);
      font-weight: 700;
    }}
    .relationship-inspector__title {{
      margin: 10px 0 0;
      font-size: 24px;
      line-height: 1;
      letter-spacing: -0.04em;
    }}
    .relationship-inspector__subtitle {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .relationship-inspector__summary {{
      margin: 12px 0 0;
      color: var(--text);
      font-size: 14px;
      line-height: 1.6;
    }}
    .relationship-inspector__grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .relationship-inspector__metric {{
      padding: 12px 12px 10px;
      border-radius: 16px;
      background: rgba(23,49,62,0.05);
      border: 1px solid rgba(23,33,33,0.05);
    }}
    .relationship-inspector__metric span {{
      display: block;
      font-size: 11px;
      line-height: 1;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .relationship-inspector__metric strong {{
      display: block;
      font-size: 16px;
      line-height: 1.25;
      letter-spacing: -0.03em;
    }}
    .relationship-inspector__reset {{
      appearance: none;
      border: 0;
      margin-top: 14px;
      padding: 10px 12px;
      border-radius: 999px;
      cursor: pointer;
      background: rgba(23,49,62,0.08);
      color: var(--text);
      transition: transform 160ms ease, background 160ms ease;
    }}
    .relationship-inspector__reset:hover {{
      transform: translateY(-1px);
      background: rgba(23,49,62,0.12);
    }}
    .score-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 44px;
      padding: 5px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }}
    .score-badge--positive {{
      background: rgba(15,118,110,0.12);
      color: #0f766e;
    }}
    .score-badge--negative {{
      background: rgba(180,83,9,0.12);
      color: #b45309;
    }}
    .score-badge--neutral {{
      background: rgba(23,49,62,0.08);
      color: #17313e;
    }}
    .mode-card {{
      border-radius: 24px;
      padding: 20px;
      border: 1px solid rgba(255,255,255,0.26);
      box-shadow: var(--shadow);
    }}
    .mode-card__title {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      margin-bottom: 14px;
      opacity: 0.84;
      font-weight: 700;
    }}
    .mode-card--ink {{
      background: linear-gradient(155deg, #17313e, #264858);
      color: #f7f2e9;
    }}
    .mode-card--sea {{
      background: linear-gradient(155deg, #0f766e, #0d9488);
      color: #f7f2e9;
    }}
    .mode-card--gold {{
      background: linear-gradient(155deg, #b7791f, #d69e2e);
      color: #fff9ef;
    }}
    .mode-card--rose {{
      background: linear-gradient(155deg, #9f1d1d, #c2410c);
      color: #fff7f4;
    }}
    .mode-card .meta-list__item {{
      border-color: rgba(255,255,255,0.14);
    }}
    .mode-card .meta-list__item span {{
      color: rgba(255,255,255,0.78);
    }}
    .mode-card code {{
      background: rgba(255,255,255,0.12);
      color: inherit;
    }}
    .artifact-grid {{
      display: grid;
      grid-template-columns: minmax(0, 0.72fr) minmax(0, 1.28fr);
      gap: 18px;
    }}
    @keyframes relationship-float {{
      0%, 100% {{
        transform: translateY(0);
      }}
      50% {{
        transform: translateY(-5px);
      }}
    }}
    @keyframes drift {{
      0%, 100% {{
        transform: translate3d(0, 0, 0) scale(1);
      }}
      50% {{
        transform: translate3d(14px, -18px, 0) scale(1.06);
      }}
    }}
    @media (max-width: 980px) {{
      .hero__grid,
      .grid--story,
      .artifact-grid,
      .donut-layout {{
        grid-template-columns: 1fr;
      }}
      .grid--metrics,
      .grid--triple,
      .grid--two {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .trend-card__head,
      .section-kicker {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}
    @media (max-width: 640px) {{
      .page {{ width: min(100vw - 20px, 1180px); padding: 20px 0 40px; }}
      .hero {{ padding: 22px; border-radius: 28px; }}
      .grid--metrics,
      .grid--triple,
      .grid--two {{
        grid-template-columns: 1fr;
      }}
      .panel {{ padding: 18px; border-radius: 22px; }}
      .meta-list__item {{ grid-template-columns: 1fr; }}
      .hero-orbit__grid,
      .trend-card__stats {{
        grid-template-columns: 1fr;
      }}
      .relationship-map {{
        min-height: 940px;
      }}
      .relationship-map__ring--inner {{
        width: 320px;
        height: 320px;
      }}
      .relationship-map__ring--outer {{
        width: 400px;
        height: 400px;
      }}
      .relationship-inspector {{
        left: 18px;
        right: 18px;
        width: auto;
      }}
      .relationship-inspector__grid {{
        grid-template-columns: 1fr 1fr;
      }}
      .donut {{
        width: 170px;
        height: 170px;
      }}
      .phrase-cloud {{
        min-height: auto;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        padding: 14px;
      }}
      .phrase-cloud__paths,
      .phrase-cloud__core {{
        display: none;
      }}
      .phrase-cloud::after,
      .phrase-cloud__guides {{
        inset: 14px;
      }}
      .phrase-chip {{
        position: relative;
        left: auto;
        top: auto;
        width: auto;
        grid-column: span var(--span-mobile);
        min-height: 104px;
        padding: 14px 14px 12px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="hero__grid">
        <div>
          <div class="eyebrow">WeChat Insight</div>
          <span class="sr-only">微信洞察 Dashboard</span>
          <h1>微信洞察 <span class="gradient-text">Dashboard</span></h1>
          <p class="hero__lead">这不是简单的聊天统计，而是一份把对话密度、商业信号、社交节奏和人格倾向收束到同一张页面里的本地分析报告。</p>
          {hero_chips}
          <div class="hero__meta">生成时间：{escape_text(format_datetime(payload.get("generated_at", "")))}</div>
        </div>
        <aside class="hero-orbit">
          <div class="hero-orbit__eyebrow">Conversation Pulse</div>
          <div class="hero-orbit__value">{escape_text(format_number(overview.get("total_messages", 0)))}</div>
          <div class="hero-orbit__caption">在 {escape_text(str(format_number(date_span_days)) + " 天")} 观察窗口内，重点看消息密度、人格信号和待推进对象。</div>
          <div class="hero-orbit__spark">
            {highlight_rows}
          </div>
          <div class="hero-orbit__grid">
            <div class="orbit-chip">
              <span>主导情绪</span>
              <strong>{escape_text(emotion_label(overview.get("dominant_emotion", "unknown")))}</strong>
            </div>
            <div class="orbit-chip">
              <span>人格推测</span>
              <strong>{escape_text(overview.get("mbti_type", "unknown"))}</strong>
            </div>
            <div class="orbit-chip">
              <span>商机联系人</span>
              <strong>{escape_text(format_number(overview.get("business_contact_count", 0)))}</strong>
            </div>
            <div class="orbit-chip">
              <span>待跟进</span>
              <strong>{escape_text(format_number(overview.get("pending_followup_count", 0)))}</strong>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section class="grid grid--metrics">
      {metric_cards}
    </section>

    {render_kicker("Overview", "先看这段时间你最值得关注的聊天摘要")}
    <section class="panel">
      <h2>一句话摘要</h2>
      <p class="panel__intro">把当期最浓缩的会话结论放在前面，方便你快速判断今天发生了什么。</p>
      {render_summary_lines(daily.get("summary_lines", []))}
    </section>

    {render_kicker("Activity", "用趋势和活跃分布看清消息是怎么涌进来的")}
    <section id="activity-section" class="grid grid--story">
      <article class="panel">
        {render_line_chart(activity_rows, "消息走势与自发输出")}
      </article>
      <article class="panel">
        <h2>日级观察</h2>
        <p class="panel__intro">每一天的峰值时段、最活跃会话和活跃范围。</p>
        {render_day_story_cards(activity_rows)}
      </article>
    </section>

    <section class="grid grid--triple">
      <article class="panel">
        <h2>最活跃会话</h2>
        <p class="panel__intro">消息最密集的场域，基本决定了你这段时间的注意力走向。</p>
        {render_bars(daily.get("top_chats", []), suffix=" 条")}
      </article>
      <article class="panel">
        <h2>最活跃联系人</h2>
        <p class="panel__intro">一对一关系里，谁占用了最多沟通带宽。</p>
        {render_bars(daily.get("top_contacts", []), suffix=" 条")}
      </article>
      <article class="panel">
        <h2>活跃时段</h2>
        <p class="panel__intro">你最常进入高交流状态的时间窗口。</p>
        {render_bars([(f"{hour}时", count) for hour, count in daily.get("top_hours", [])], suffix=" 条")}
      </article>
    </section>

    {render_kicker("Relationship", "把高频群聊和高频私聊真正画成一张社交图谱")}
    <section id="relationship-section" class="grid grid--story">
      <article class="panel">
        <h2>社交关系图</h2>
        <p class="panel__intro">中心是你自己，上层是高频群聊，下层是高频私聊联系人，连线粗细代表互动密度。</p>
        {render_relationship_map(chat_leaderboard, contact_leaderboard, overview, social)}
      </article>
      <article class="panel">
        <h2>关系摘要</h2>
        <p class="panel__intro">用最少的字，把这张图想表达的重点读出来。</p>
        {render_key_value_list(relationship_rows, empty_text="暂无关系图摘要")}
      </article>
    </section>

    {render_kicker("Persona", "让情绪、MBTI、口癖和社交节奏落到可视化上")}
    <section id="persona-section" class="grid grid--two">
      <article class="panel">
        <h2>情绪分布</h2>
        <p class="panel__intro">看你自己的表达更偏积极、平稳，还是容易带出焦虑和攻击性。</p>
        {render_donut_chart(emotion_chart_rows)}
      </article>
      <article class="panel">
        <h2>MBTI 推测</h2>
        <p class="panel__intro">不是测试问卷，而是从真实聊天行为里逆推出的四维倾向。</p>
        {render_dimension_matrix(mbti.get("dimensions", {}), empty_text="暂无 MBTI 数据")}
      </article>
      <article class="panel">
        <h2>口癖统计</h2>
        <p class="panel__intro">高频短语、反复出现的说法，会比单次措辞更像你。</p>
        {render_phrase_cloud(speech.get("top_terms") or speech.get("repeated_phrases") or [], empty_text="暂无明显重复口癖")}
      </article>
      <article class="panel">
        <h2>社交节奏</h2>
        <p class="panel__intro">用响应速度、群私聊占比和消息长度去看你的沟通方式。</p>
        {render_key_value_list(social_rows, empty_text="暂无社交画像数据")}
      </article>
      <article class="panel">
        <h2>情绪热点会话</h2>
        <p class="panel__intro">不是最活跃，而是情绪浓度最高、最可能拉高心智负荷的会话。</p>
        {render_emotional_chat_list(emotion.get("top_emotional_chats", []), empty_text="暂无情绪热点会话")}
      </article>
      <article class="panel">
        <h2>角色分布</h2>
        <p class="panel__intro">从联系人类型看，你当前的沟通资源更偏业务还是偏日常。</p>
        {render_bars(role_rows, suffix=" 人")}
      </article>
      <article class="panel">
        <h2>社交高频会话</h2>
        <p class="panel__intro">长期高频并不一定高价值，但一定会改变你的注意力结构。</p>
        {render_bars(social.get("top_chats", []), suffix=" 条")}
      </article>
      <article class="panel">
        <h2>语言标点</h2>
        <p class="panel__intro">问号、感叹号和省略号，是你表达情绪和压力的细碎线索。</p>
        {render_key_value_list([
          ("问号", speech.get("punctuation_counts", {}).get("question")),
          ("感叹号", speech.get("punctuation_counts", {}).get("exclamation")),
          ("省略号", speech.get("punctuation_counts", {}).get("ellipsis")),
          ("特征目录", features.get("output_dir")),
        ], empty_text="暂无语言特征数据")}
      </article>
    </section>

    <section class="grid grid--two">
      {render_persona_mode_card("工作人格", work_mode, "暂无工作人格样本")}
      {render_persona_mode_card("日常人格", life_mode, "暂无日常人格样本")}
    </section>

    {render_kicker("Signals", "哪些人、哪些话，最值得你继续跟进")}
    <section class="grid grid--two">
      <article class="panel">
        <h2>待跟进信号</h2>
        <p class="panel__intro">别人已经把球抛过来，但你还没真正接住的聊天节点。</p>
        {render_daily_followups(daily.get("pending_followups", []))}
      </article>
      <article class="panel">
        <h2>高意向机会</h2>
        <p class="panel__intro">报价、合作、推进等信号最浓的联系人，适合优先跟。</p>
        {render_opportunity_list(customer.get("top_opportunities", []))}
      </article>
      <article class="panel">
        <h2>售后风险</h2>
        <p class="panel__intro">抱怨、异常、负面情绪偏多的对象，建议单独观察。</p>
        {render_risk_list(customer.get("top_support_risks", []))}
      </article>
      <article class="panel">
        <h2>待跟进客户</h2>
        <p class="panel__intro">从客户维度聚合出的待处理项，避免遗漏重要推进对象。</p>
        {render_customer_followups(customer.get("pending_followups", []))}
      </article>
    </section>

    {render_kicker("Artifacts", "最后把导出结果和中间产物交代清楚")}
    <section class="artifact-grid">
      <article class="panel">
        <h2>标签与特征</h2>
        <p class="panel__intro">这部分是后续 dashboard、画像增强和自动化动作的基础。</p>
        {render_key_value_list([
          ("标签联系人", labels.get("generated_contacts")),
          ("私聊联系人", labels.get("total_private_contacts")),
          ("自动建议", labels.get("applied_suggestions")),
          ("特征目录", features.get("output_dir")),
        ], empty_text="暂无标签与特征信息")}
      </article>
      <article class="panel">
        <h2>数据源文件</h2>
        <p class="panel__intro">导出链路中的关键产物路径，方便你继续追查或二次加工。</p>
        {render_key_value_list(source_rows, empty_text="暂无产物文件")}
      </article>
    </section>
  </main>
  <script id="report-payload" type="application/json">{serialize_payload_for_script(payload)}</script>
  <script>
    (() => {{
      const phraseClouds = document.querySelectorAll(".phrase-cloud");
      phraseClouds.forEach((cloud) => {{
        const core = cloud.querySelector(".phrase-cloud__core");
        if (!core) {{
          return;
        }}

        const coreEyebrow = core.querySelector(".phrase-cloud__core-eyebrow");
        const coreTitle = core.querySelector(".phrase-cloud__core-title");
        const coreValue = core.querySelector(".phrase-cloud__core-value");
        const coreSummary = core.querySelector(".phrase-cloud__core-summary");
        const chips = Array.from(cloud.querySelectorAll(".phrase-chip"));
        const defaultState = {{
          eyebrow: cloud.dataset.defaultEyebrow || "Top Phrase",
          title: cloud.dataset.defaultTitle || "",
          value: cloud.dataset.defaultValue || "",
          summary: cloud.dataset.defaultSummary || "",
          accent: cloud.dataset.defaultAccent || "sea",
          lane: cloud.dataset.defaultLane || "mid",
        }};

        const applyPhraseState = (state) => {{
          const accent = state.accent || "sea";
          const lane = state.lane || "mid";
          cloud.classList.remove(
            "phrase-cloud--tone-sea",
            "phrase-cloud--tone-ink",
            "phrase-cloud--tone-gold",
            "phrase-cloud--lane-top",
            "phrase-cloud--lane-mid",
            "phrase-cloud--lane-bottom"
          );
          cloud.classList.add(`phrase-cloud--tone-${{accent}}`, `phrase-cloud--lane-${{lane}}`);
          core.classList.remove("phrase-cloud__core--sea", "phrase-cloud__core--ink", "phrase-cloud__core--gold");
          core.classList.add(`phrase-cloud__core--${{accent}}`);
          if (coreEyebrow) coreEyebrow.textContent = state.eyebrow || "Top Phrase";
          if (coreTitle) coreTitle.textContent = state.title || "";
          if (coreValue) coreValue.textContent = state.value || "";
          if (coreSummary) coreSummary.textContent = state.summary || "";
        }};

        const phraseState = (chip) => {{
          if (!chip) {{
            return defaultState;
          }}
          return {{
            eyebrow: chip.dataset.eyebrow || "Phrase Focus",
            title: chip.dataset.title || "",
            value: chip.dataset.value || "",
            summary: chip.dataset.summary || "",
            accent: chip.dataset.accent || "sea",
            lane: chip.dataset.lane || "mid",
          }};
        }};

        const activatePhrase = (chip) => {{
          chips.forEach((item) => item.classList.toggle("phrase-chip--active", item === chip));
          applyPhraseState(phraseState(chip));
        }};

        chips.forEach((chip, index) => {{
          chip.addEventListener("mouseenter", () => activatePhrase(chip));
          chip.addEventListener("focus", () => activatePhrase(chip));
          chip.addEventListener("mouseleave", () => activatePhrase(chips[0] || null));
          chip.addEventListener("blur", () => activatePhrase(chips[0] || null));
          if (index === 0) {{
            chip.classList.add("phrase-chip--active");
          }}
        }});

        applyPhraseState(defaultState);
      }});

      const maps = document.querySelectorAll(".relationship-map");
      maps.forEach((map) => {{
        const inspector = map.querySelector(".relationship-inspector");
        if (!inspector) {{
          return;
        }}

        const title = inspector.querySelector(".relationship-inspector__title");
        const subtitle = inspector.querySelector(".relationship-inspector__subtitle");
        const summary = inspector.querySelector(".relationship-inspector__summary");
        const resetButton = inspector.querySelector(".relationship-inspector__reset");
        const fields = {{
          type: inspector.querySelector('[data-inspector-field="type"]'),
          messages: inspector.querySelector('[data-inspector-field="messages"]'),
          business: inspector.querySelector('[data-inspector-field="business"]'),
          support: inspector.querySelector('[data-inspector-field="support"]'),
          activeDays: inspector.querySelector('[data-inspector-field="active_days"]'),
          selfRatio: inspector.querySelector('[data-inspector-field="self_ratio"]'),
        }};

        const defaults = {{
          eyebrow: map.dataset.defaultEyebrow || "Inspector",
          title: map.dataset.defaultTitle || "将鼠标移到节点上",
          subtitle: map.dataset.defaultSubtitle || "",
          summary: map.dataset.defaultSummary || "",
          type: map.dataset.defaultType || "",
          messages: map.dataset.defaultMessages || "",
          business: map.dataset.defaultBusiness || "",
          support: map.dataset.defaultSupport || "",
          activeDays: map.dataset.defaultActiveDays || "",
          selfRatio: map.dataset.defaultSelfRatio || "",
          theme: map.dataset.defaultTheme || "center",
        }};

        let selectedNode = null;

        const applyState = (state) => {{
          inspector.classList.remove("relationship-inspector--group", "relationship-inspector--contact", "relationship-inspector--center");
          inspector.classList.add(`relationship-inspector--${{state.theme || "center"}}`);
          const eyebrowNode = inspector.querySelector(".relationship-inspector__eyebrow");
          if (eyebrowNode) eyebrowNode.textContent = state.eyebrow || "Inspector";
          if (title) title.textContent = state.title || "";
          if (subtitle) subtitle.textContent = state.subtitle || "";
          if (summary) summary.textContent = state.summary || "";
          if (fields.type) fields.type.textContent = state.type || "—";
          if (fields.messages) fields.messages.textContent = state.messages || "—";
          if (fields.business) fields.business.textContent = state.business || "—";
          if (fields.support) fields.support.textContent = state.support || "—";
          if (fields.activeDays) fields.activeDays.textContent = state.activeDays || "—";
          if (fields.selfRatio) fields.selfRatio.textContent = state.selfRatio || "—";
        }};

        const nodeState = (node) => {{
          if (!node) {{
            return defaults;
          }}
          return {{
            eyebrow: node.dataset.eyebrow || "Inspector",
            title: node.dataset.title || "",
            subtitle: node.dataset.subtitle || "",
            summary: node.dataset.summary || "",
            type: node.dataset.type || "",
            messages: node.dataset.messages || "",
            business: node.dataset.business || "",
            support: node.dataset.support || "",
            activeDays: node.dataset.activeDays || "",
            selfRatio: node.dataset.selfRatio || "",
            theme: node.dataset.theme || "center",
          }};
        }};

        const activateNode = (node, persist) => {{
          map.querySelectorAll(".relationship-node").forEach((item) => item.classList.toggle("is-active", item === node));
          applyState(nodeState(node));
          if (persist) {{
            selectedNode = node && node.dataset.resetInspector ? null : node;
          }}
        }};

        map.querySelectorAll(".relationship-node").forEach((node) => {{
          node.addEventListener("mouseenter", () => activateNode(node, false));
          node.addEventListener("focus", () => activateNode(node, false));
          node.addEventListener("mouseleave", () => activateNode(selectedNode, false));
          node.addEventListener("blur", () => activateNode(selectedNode, false));
          node.addEventListener("click", () => activateNode(node, true));
        }});

        if (resetButton) {{
          resetButton.addEventListener("click", () => {{
            selectedNode = null;
            map.querySelectorAll(".relationship-node").forEach((item) => item.classList.remove("is-active"));
            applyState(defaults);
          }});
        }}

        applyState(defaults);
      }});
    }})();
  </script>
</body>
</html>
"""


def generate_html_report(payload_path=None, input_path=None, output_file=None,
                         config_path=None, labels_path=None):
    resolved_payload_path = os.path.expanduser(payload_path) if payload_path else None
    if resolved_payload_path:
        payload = load_payload(resolved_payload_path)
    else:
        payload = REPORT_DATA_MODULE.build_report_data_payload(
            input_path=input_path,
            config_path=config_path,
            labels_path=labels_path,
        )
        resolved_payload_path = payload.get("artifacts", {}).get("payload_path")

    html_content = render_html(payload)
    report_path = os.path.expanduser(output_file) if output_file else build_default_output_path(
        payload,
        payload_path=resolved_payload_path,
        config_path=config_path,
    )
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "payload_path": resolved_payload_path,
        "report_path": report_path,
        "title": "WeChat Insight Dashboard",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成本地可打开的 HTML 报告")
    parser.add_argument("--payload", help="已存在的 report_payload.json 路径")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 HTML 路径")
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = generate_html_report(
        payload_path=args.payload,
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        labels_path=args.labels,
    )

    print("=" * 50)
    print("WeChat Insight HTML Report")
    print("=" * 50)
    print(f"Payload 路径: {result['payload_path']}")
    print(f"HTML 路径: {result['report_path']}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
