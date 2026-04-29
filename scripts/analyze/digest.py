#!/usr/bin/env python3
"""One-command daily digest entrypoint for automation hosts."""

import argparse
import importlib.util
import os
import pathlib
from datetime import datetime


CURRENT_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent


def load_script_module(name, relative_path):
    path = ROOT_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


DAILY_MODULE = load_script_module("daily", "scripts/analyze/daily.py")
EXPORT_MODULE = load_script_module("export_messages", "scripts/export_messages.py")


def build_export_args(days=1, today=False, config_path=None, output_dir=None):
    args = []
    if today:
        today_label = datetime.now().strftime("%Y-%m-%d")
        args.extend(["--start", today_label, "--end", today_label])
    else:
        args.extend(["--days", str(days or 1)])

    if config_path:
        args.extend(["--config", config_path])
    if output_dir:
        args.extend(["--output", os.path.expanduser(output_dir)])
    return args


def resolve_latest_input(config_path=None):
    config = DAILY_MODULE.load_config(config_path)
    latest = DAILY_MODULE.find_latest_export_file(
        config.get("data_dir", DAILY_MODULE.DEFAULT_DATA_DIR)
    )
    if not latest:
        raise FileNotFoundError("未找到可分析的消息文件，请检查 export 是否成功")
    return latest


def build_empty_report_path(output_file=None, config_path=None):
    if output_file:
        return os.path.expanduser(output_file)
    config = DAILY_MODULE.load_config(config_path)
    report_dir = os.path.expanduser(config.get("report_dir", DAILY_MODULE.DEFAULT_REPORT_DIR))
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, f"daily_{datetime.now().strftime('%Y%m%d')}.md")


def write_empty_digest(input_files, output_file=None, config_path=None):
    report_path = build_empty_report_path(output_file=output_file, config_path=config_path)
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    report_markdown = "\n".join([
        "# 微信聊天日报",
        "",
        "- 暂无可分析消息",
        "",
        "## 今日摘要",
        "- 当前输入文件为空，未发现可统计的聊天记录。",
        "",
    ])
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    return {
        "input_files": input_files,
        "report_path": report_path,
        "report_markdown": report_markdown,
        "total_messages": 0,
        "pending_followups": [],
    }


def run_digest(input_path=None, output_file=None, config_path=None, days=1,
               today=False, export_main=None, output_dir=None):
    if input_path:
        resolved_input = input_path
    else:
        runner = export_main or EXPORT_MODULE.main
        exit_code = runner(build_export_args(
            days=days,
            today=today,
            config_path=config_path,
            output_dir=output_dir,
        ))
        if exit_code:
            raise RuntimeError(f"export 失败，退出码: {exit_code}")
        resolved_input = resolve_latest_input(config_path=config_path)

    input_files = DAILY_MODULE.resolve_input_files(
        input_path=resolved_input,
        config_path=config_path,
    )
    if not DAILY_MODULE.load_messages(input_files):
        return write_empty_digest(
            input_files=input_files,
            output_file=output_file,
            config_path=config_path,
        )

    return DAILY_MODULE.analyze_daily(
        input_path=resolved_input,
        output_file=output_file,
        config_path=config_path,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="一键生成微信聊天日报 digest")
    parser.add_argument("--input", "-i", help="已存在的 JSONL 输入；提供后跳过 export")
    parser.add_argument("--output", "-o", help="输出 Markdown 路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--days", "-d", type=int, default=1, help="未指定 input 时导出最近 N 天")
    parser.add_argument("--today", action="store_true", help="未指定 input 时导出当天自然日")
    parser.add_argument("--export-output", help="export 输出目录")
    parser.add_argument("--stdout", action="store_true", help="同时把 Markdown 正文打印到 stdout")
    args = parser.parse_args(argv)

    result = run_digest(
        input_path=args.input,
        output_file=args.output,
        config_path=args.config,
        days=args.days,
        today=args.today,
        output_dir=args.export_output,
    )

    print("WECHAT_INSIGHT_DIGEST")
    print(f"DIGEST_INPUT_FILES={','.join(result['input_files'])}")
    print(f"DIGEST_REPORT_PATH={result['report_path']}")
    print(f"DIGEST_TOTAL_MESSAGES={result['total_messages']}")
    print(f"DIGEST_PENDING_FOLLOWUPS={len(result['pending_followups'])}")
    if args.stdout:
        print()
        print(result["report_markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
