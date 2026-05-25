#!/usr/bin/env bash
# 重建在线 Demo：脱敏样例数据 -> 单文件 HTML 报告 -> docs/demo/index.html
#
# 用法（在仓库根目录执行）：
#   ./scripts/build_demo.sh
#
# 产物：
#   docs/sample/messages_sample.jsonl   脱敏虚构聊天数据（已提交）
#   docs/demo/index.html                可直接打开/挂 GitHub Pages 的示例报告
#   docs/index.html                     落地页（手写，不在此脚本生成）

set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
SAMPLE="docs/sample/messages_sample.jsonl"
PAYLOAD="$(mktemp -t wechat-insight-demo-payload.XXXXXX.json)"
trap 'rm -f "$PAYLOAD"' EXIT

echo "[1/3] 生成脱敏样例数据"
"$PY" scripts/make_sample_data.py -o "$SAMPLE"

echo "[2/3] 生成统一 report payload"
"$PY" wechat_insight_cli.py report-data --input "$SAMPLE" --output "$PAYLOAD"

echo "[3/4] build 单文件 HTML 报告 -> docs/demo/index.html"
mkdir -p docs/demo
"$PY" wechat_insight_cli.py html --payload "$PAYLOAD" --output docs/demo/index.html

echo "[4/4] build 分享卡 -> docs/demo/share.html"
"$PY" wechat_insight_cli.py share --payload "$PAYLOAD" --output docs/demo/share.html

echo "✅ Demo 已更新：docs/demo/index.html、docs/demo/share.html"
echo "   本地预览：open docs/index.html"
