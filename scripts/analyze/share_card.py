#!/usr/bin/env python3
"""生成一张适合分享的竖版"关系画像卡"。

和完整 dashboard 不同，分享卡只挑最有"晒点"的几个数字压进一张竖图里
（适配朋友圈 / 小红书截图），底部带项目水印，形成传播闭环。

纯 Python 模板渲染，零新依赖、零联网，产物是自包含的单文件 HTML——
用浏览器打开后直接截图即可。

用法：
    ./wechat-insight share --input ~/.wechat-insight/data/messages_*.jsonl
    ./wechat-insight share --payload ~/.wechat-insight/reports/report_payload_xxx.json
    ./wechat-insight share --input docs/sample/messages_sample.jsonl -o /tmp/card.html
"""

import argparse
import html
import importlib.util
import json
import os
import pathlib


CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_REPORT_DIR = os.path.expanduser("~/.wechat-insight/reports")
CURRENT_DIR = pathlib.Path(__file__).resolve().parent

EMOTION_LABELS = {
    "positive": "积极",
    "negative": "消极",
    "neutral": "平稳",
    "anxious": "焦虑",
    "angry": "愤怒",
}
EMOTION_COLORS = {
    "positive": "#4ade80",
    "negative": "#fb7185",
    "neutral": "#94a3b8",
    "anxious": "#fbbf24",
    "angry": "#f87171",
}


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


def load_payload(payload_path):
    with open(os.path.expanduser(payload_path), encoding="utf-8") as f:
        return json.load(f)


def resolve_payload(payload_path=None, input_path=None, config_path=None, labels_path=None):
    if payload_path:
        resolved = os.path.expanduser(payload_path)
        return load_payload(resolved), resolved
    payload = REPORT_DATA_MODULE.build_report_data_payload(
        input_path=input_path,
        config_path=config_path,
        labels_path=labels_path,
    )
    return payload, payload.get("artifacts", {}).get("payload_path")


def esc(value):
    return html.escape(str(value if value is not None else ""))


def build_default_output_path(payload, payload_path=None, config_path=None):
    resolved = payload_path or payload.get("artifacts", {}).get("payload_path")
    if resolved:
        f = pathlib.Path(os.path.expanduser(resolved))
        name = f.stem
        if name.startswith("report_payload_"):
            filename = f"share_card_{name[len('report_payload_'):]}.html"
        else:
            filename = f"{name}_share.html"
        return str(f.with_name(filename))
    config = load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, "share_card.html")


def _stat(label, value, accent="#e8eaf0"):
    return (
        '<div class="stat">'
        f'<div class="stat__num" style="color:{accent}">{esc(value)}</div>'
        f'<div class="stat__label">{esc(label)}</div>'
        "</div>"
    )


def build_share_card_html(payload):
    overview = payload.get("overview", {}) or {}
    sections = payload.get("sections", {}) or {}
    mbti = sections.get("mbti", {}) or {}
    emotion = sections.get("emotion", {}) or {}
    speech = sections.get("speech", {}) or {}
    daily = sections.get("daily", {}) or {}

    total_messages = overview.get("total_messages", 0)
    active_chats = overview.get("active_chat_count", 0)
    span_days = overview.get("date_span_days", 0)
    business_count = overview.get("business_contact_count", 0)
    pending_count = overview.get("pending_followup_count", 0)
    latency = overview.get("median_response_latency_minutes")

    # MBTI 四维
    mbti_type = overview.get("mbti_type") or mbti.get("mbti_type") or "----"
    dims = mbti.get("dimensions", {}) or {}
    dim_chips = ""
    for key in ("EI", "SN", "TF", "JP"):
        dim = dims.get(key)
        if not dim:
            continue
        dim_chips += (
            '<div class="dim">'
            f'<div class="dim__letter">{esc(dim.get("letter", "-"))}</div>'
            f'<div class="dim__label">{esc(dim.get("label", ""))}</div>'
            "</div>"
        )

    # 情绪
    dominant = overview.get("dominant_emotion") or emotion.get("dominant_emotion") or "neutral"
    emo_label = EMOTION_LABELS.get(dominant, dominant)
    emo_color = EMOTION_COLORS.get(dominant, "#94a3b8")

    # 口头禅 top 3
    top_terms = [t.get("text", "") for t in (speech.get("top_terms") or [])[:3] if t.get("text")]
    terms_html = "".join(f'<span class="term">{esc(t)}</span>' for t in top_terms) or \
        '<span class="term">—</span>'

    # 最活跃时段
    top_hours = daily.get("top_hours") or []
    peak_hour = f"{int(top_hours[0][0]):02d}:00" if top_hours else "—"

    latency_text = f"{latency} 分钟" if latency is not None else "—"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>我的微信关系画像 · WeChat Insight</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #05070c; min-height: 100vh; display: flex; justify-content: center; align-items: flex-start;
    padding: 40px 16px; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .card {{
    width: 540px; max-width: 100%; border-radius: 28px; overflow: hidden;
    background: radial-gradient(700px 360px at 50% -8%, #1c2740 0%, #0b0f1a 55%, #090c14 100%);
    border: 1px solid #1e2533; color: #e8eaf0; padding: 44px 40px 28px;
    box-shadow: 0 40px 120px rgba(0,0,0,.6);
  }}
  .kicker {{ font-size: 13px; letter-spacing: 3px; color: #6b7689; text-transform: uppercase; }}
  .title {{ font-size: 30px; font-weight: 800; letter-spacing: -.5px; margin: 8px 0 4px; }}
  .subtitle {{ font-size: 13px; color: #8a93a6; margin-bottom: 28px; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 28px; }}
  .stat {{ flex: 1; background: rgba(255,255,255,.03); border: 1px solid #1e2533; border-radius: 16px; padding: 16px 10px; text-align: center; }}
  .stat__num {{ font-size: 30px; font-weight: 800; line-height: 1; }}
  .stat__label {{ font-size: 12px; color: #8a93a6; margin-top: 7px; }}
  .block {{ background: rgba(255,255,255,.03); border: 1px solid #1e2533; border-radius: 18px; padding: 20px; margin-bottom: 16px; }}
  .block__head {{ display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }}
  .block__name {{ font-size: 13px; color: #8a93a6; letter-spacing: .5px; }}
  .mbti-type {{ font-size: 34px; font-weight: 900; letter-spacing: 4px; color: #60a5fa; }}
  .dims {{ display: flex; gap: 10px; }}
  .dim {{ flex: 1; text-align: center; }}
  .dim__letter {{ font-size: 22px; font-weight: 800; color: #cfe0ff; }}
  .dim__label {{ font-size: 11px; color: #8a93a6; margin-top: 4px; }}
  .row {{ display: flex; gap: 16px; }}
  .row .block {{ flex: 1; }}
  .big {{ font-size: 26px; font-weight: 800; }}
  .muted {{ font-size: 12px; color: #8a93a6; }}
  .terms {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .term {{ font-size: 14px; padding: 6px 12px; border-radius: 999px; background: rgba(96,165,250,.12); color: #9ec5ff; border: 1px solid rgba(96,165,250,.25); }}
  .footer {{ display: flex; align-items: center; justify-content: space-between; margin-top: 22px; padding-top: 18px; border-top: 1px solid #1a212e; }}
  .brand {{ font-size: 13px; font-weight: 700; color: #cdd5e3; }}
  .brand span {{ color: #4ade80; }}
  .link {{ font-size: 11px; color: #6b7689; }}
  .disclaimer {{ font-size: 10.5px; color: #5c6577; margin-top: 10px; line-height: 1.5; }}
</style>
</head>
<body>
  <div class="card">
    <div class="kicker">WeChat Insight</div>
    <div class="title">我的微信关系画像</div>
    <div class="subtitle">基于近 {esc(span_days)} 天聊天记录 · 全本地分析</div>

    <div class="stats">
      {_stat("条消息", f"{total_messages:,}" if isinstance(total_messages, int) else total_messages)}
      {_stat("个活跃会话", active_chats, "#60a5fa")}
      {_stat("天跨度", span_days, "#4ade80")}
    </div>

    <div class="block">
      <div class="block__head">
        <span class="block__name">人格推测（启发式）</span>
        <span class="mbti-type">{esc(mbti_type)}</span>
      </div>
      <div class="dims">{dim_chips or '<div class="muted">数据不足</div>'}</div>
    </div>

    <div class="row">
      <div class="block">
        <div class="block__name">情绪底色</div>
        <div class="big" style="color:{emo_color}; margin-top:8px">{esc(emo_label)}</div>
      </div>
      <div class="block">
        <div class="block__name">最活跃时段</div>
        <div class="big" style="margin-top:8px">{esc(peak_hour)}</div>
      </div>
    </div>

    <div class="block">
      <div class="block__name" style="margin-bottom:12px">我的口头禅</div>
      <div class="terms">{terms_html}</div>
    </div>

    <div class="row">
      <div class="block">
        <div class="block__name">商机联系人</div>
        <div class="big" style="color:#4ade80; margin-top:8px">{esc(business_count)}</div>
      </div>
      <div class="block">
        <div class="block__name">待跟进</div>
        <div class="big" style="color:#fbbf24; margin-top:8px">{esc(pending_count)}</div>
      </div>
      <div class="block">
        <div class="block__name">中位回复</div>
        <div class="big" style="margin-top:8px">{esc(latency_text)}</div>
      </div>
    </div>

    <div class="footer">
      <div class="brand">WeChat <span>Insight</span></div>
      <div class="link">github.com/caigee-cmd/wechat-insight</div>
    </div>
    <div class="disclaimer">
      数据全程在本机分析，聊天内容未上传。MBTI / 情绪 / 口头禅均为启发式推测，仅供娱乐参考。
    </div>
  </div>
</body>
</html>
"""


def generate_share_card(payload_path=None, input_path=None, output_file=None,
                        config_path=None, labels_path=None):
    payload, resolved_payload_path = resolve_payload(
        payload_path=payload_path,
        input_path=input_path,
        config_path=config_path,
        labels_path=labels_path,
    )
    output_path = output_file or build_default_output_path(
        payload, payload_path=resolved_payload_path, config_path=config_path
    )
    output_path = os.path.expanduser(output_path)
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(build_share_card_html(payload))

    return {"payload_path": resolved_payload_path, "card_path": output_path}


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成可分享的关系画像卡（竖版 HTML，截图即用）")
    parser.add_argument("--payload", help="已存在的 report_payload.json 路径")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--output", "-o", help="输出 HTML 路径")
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    args = parser.parse_args(argv)

    result = generate_share_card(
        payload_path=args.payload,
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        labels_path=args.labels,
    )

    print("=" * 50)
    print("WeChat Insight 分享卡")
    print("=" * 50)
    print(f"Payload 路径: {result['payload_path']}")
    print(f"分享卡路径: {result['card_path']}")
    print("用浏览器打开后截图即可分享。")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
