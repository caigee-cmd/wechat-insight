#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$ROOT_DIR/wechat-insight"
DEFAULT_CONFIG_PATH="${WECHAT_INSIGHT_CONFIG_PATH:-$HOME/.config/wechat-insight.json}"
DEFAULT_DATA_DIR="$HOME/.wechat-insight/data"

usage() {
  cat <<'EOF'
本机 smoke 验收脚本

用法:
  ./scripts/local_smoke.sh doctor
  ./scripts/local_smoke.sh setup
  ./scripts/local_smoke.sh list
  ./scripts/local_smoke.sh quick [--days N]

说明:
  - 本项目以真机链路为准，不依赖 GitHub CI
  - quick 会依次执行: doctor -> list -> export -> report-data -> html
  - setup 仍然需要手动登录微信
EOF
}

ensure_cli() {
  if [[ ! -x "$CLI" ]]; then
    echo "[ERROR] 未找到可执行 CLI: $CLI"
    exit 1
  fi
}

resolve_data_dir() {
  python3 - "$DEFAULT_CONFIG_PATH" "$DEFAULT_DATA_DIR" <<'PY'
import json
import os
import sys

config_path = os.path.expanduser(sys.argv[1])
default_data_dir = os.path.expanduser(sys.argv[2])

if os.path.exists(config_path):
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    print(os.path.expanduser(config.get("data_dir", default_data_dir)))
else:
    print(default_data_dir)
PY
}

find_latest_export() {
  local data_dir
  data_dir="$(resolve_data_dir)"

  python3 - "$data_dir" <<'PY'
import glob
import os
import sys

data_dir = os.path.expanduser(sys.argv[1])
paths = glob.glob(os.path.join(data_dir, "messages_*.jsonl"))
if not paths:
    raise SystemExit(1)
print(max(paths, key=lambda path: (os.path.getmtime(path), path)))
PY
}

run_quick() {
  local days="${1:-7}"
  local latest_export

  "$CLI" doctor
  "$CLI" list
  "$CLI" export --days "$days"

  if ! latest_export="$(find_latest_export)"; then
    echo "[ERROR] 未找到最新导出文件，请先检查 export 是否成功"
    exit 1
  fi

  "$CLI" report-data --input "$latest_export"
  "$CLI" html --input "$latest_export"

  echo
  echo "Smoke 验收完成"
  echo "最近导出: $latest_export"
}

main() {
  ensure_cli

  case "${1:-}" in
    doctor)
      "$CLI" doctor
      ;;
    setup)
      "$CLI" setup
      ;;
    list)
      "$CLI" list
      ;;
    quick)
      shift || true
      if [[ "${1:-}" == "--days" ]]; then
        run_quick "${2:-7}"
      else
        run_quick "7"
      fi
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      echo "[ERROR] 未知命令: $1"
      echo
      usage
      exit 1
      ;;
  esac
}

main "$@"
