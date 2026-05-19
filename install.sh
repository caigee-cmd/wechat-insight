#!/usr/bin/env bash
# wechat-insight installer (macOS only)
#
# 一行安装：
#   curl -sL https://raw.githubusercontent.com/caigee-cmd/wechat-insight/main/install.sh | bash
#
# 自定义路径：
#   WECHAT_INSIGHT_HOME=/path/to/dir bash install.sh

set -euo pipefail

REPO_URL="${WECHAT_INSIGHT_REPO_URL:-https://github.com/caigee-cmd/wechat-insight.git}"
INSTALL_DIR="${WECHAT_INSIGHT_HOME:-$HOME/.local/share/wechat-insight}"

log() { printf "\033[1;34m[wechat-insight]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[wechat-insight]\033[0m %s\n" "$*" >&2; }

[[ "$(uname -s)" == "Darwin" ]] \
    || { err "目前只支持 macOS（依赖微信 Mac 4.x + Frida）"; exit 1; }

command -v python3 >/dev/null 2>&1 \
    || { err "未找到 python3（需要 3.9+）"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || { err "Python 版本太低，需要 3.9+"; exit 1; }
command -v git >/dev/null 2>&1 \
    || { err "未找到 git"; exit 1; }

if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "更新已有 checkout: $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
else
    log "clone 到: $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

VENV_DIR="$INSTALL_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    log "创建 venv: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

log "安装 Python 依赖"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

cat <<EOF

✅ 装好了。Checkout: $INSTALL_DIR

下一步（首次配置，会引导登录微信 + Frida 注入提取密钥）：
  cd "$INSTALL_DIR"
  ./wechat-insight doctor
  ./wechat-insight setup

之后日常使用（./wechat-insight 会自动用项目自带的 .venv，不需要手动 activate）：
  cd "$INSTALL_DIR"
  ./wechat-insight export --days 7
  ./wechat-insight daily
  ./wechat-insight html

HTML 报告所需的前端依赖会在首次跑 html 时自动 npm install。
EOF
