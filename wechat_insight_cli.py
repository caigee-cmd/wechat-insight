#!/usr/bin/env python3
"""Unified CLI for WeChat Insight."""

import argparse
import importlib.util
import json
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/wechat-insight.json")
DEFAULT_KEYS_PATH = os.path.expanduser("~/.config/wechat-keys.json")


def load_script_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_parser(config_path=DEFAULT_CONFIG_PATH, keys_path=DEFAULT_KEYS_PATH):
    parser = argparse.ArgumentParser(
        prog="wechat-insight",
        description="微信聊天记录提取与导出 CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("setup", help="首次提取数据库密钥并生成配置")

    list_parser = subparsers.add_parser("list", help="列出群聊和联系人")
    list_parser.add_argument("args", nargs=argparse.REMAINDER)

    export_parser = subparsers.add_parser("export", help="导出聊天记录")
    export_parser.add_argument("args", nargs=argparse.REMAINDER)

    features_parser = subparsers.add_parser("features", help="从导出数据生成 feature 层")
    features_parser.add_argument("args", nargs=argparse.REMAINDER)

    daily_parser = subparsers.add_parser("daily", help="基于已导出数据生成日报")
    daily_parser.add_argument("args", nargs=argparse.REMAINDER)

    digest_parser = subparsers.add_parser("digest", help="一键导出并生成自动化日报")
    digest_parser.add_argument("args", nargs=argparse.REMAINDER)

    customer_parser = subparsers.add_parser("customer", help="基于已导出数据生成客户/商业分析")
    customer_parser.add_argument("args", nargs=argparse.REMAINDER)

    labels_parser = subparsers.add_parser("labels", help="生成联系人标签引导文件")
    labels_parser.add_argument("args", nargs=argparse.REMAINDER)

    report_data_parser = subparsers.add_parser("report-data", help="生成统一 report payload 数据")
    report_data_parser.add_argument("args", nargs=argparse.REMAINDER)

    html_parser = subparsers.add_parser("html", help="生成本地可打开的静态 HTML 报告")
    html_parser.add_argument("args", nargs=argparse.REMAINDER)

    dashboard_parser = subparsers.add_parser("dashboard", help="启动本地交互式 dashboard")
    dashboard_parser.add_argument("args", nargs=argparse.REMAINDER)

    emotion_parser = subparsers.add_parser("emotion", help="生成情绪周期分析")
    emotion_parser.add_argument("args", nargs=argparse.REMAINDER)

    mbti_parser = subparsers.add_parser("mbti", help="生成 MBTI 推测报告")
    mbti_parser.add_argument("args", nargs=argparse.REMAINDER)

    speech_parser = subparsers.add_parser("speech", help="生成口癖与语言风格分析")
    speech_parser.add_argument("args", nargs=argparse.REMAINDER)

    social_parser = subparsers.add_parser("social", help="生成社交图谱与时间画像")
    social_parser.add_argument("args", nargs=argparse.REMAINDER)

    doctor_parser = subparsers.add_parser("doctor", help="检查当前配置状态")
    doctor_parser.add_argument(
        "--config-path",
        default=config_path,
        help="配置文件路径",
    )
    doctor_parser.add_argument(
        "--keys-path",
        default=keys_path,
        help="密钥文件路径",
    )

    return parser


def run_doctor(config_path=DEFAULT_CONFIG_PATH, keys_path=DEFAULT_KEYS_PATH):
    config_exists = os.path.exists(config_path)
    keys_exists = os.path.exists(keys_path)

    print("WeChat Insight Doctor")
    print("=" * 24)
    print(f"配置文件: {'已存在' if config_exists else '缺失'}")
    print(f"密钥文件: {'已存在' if keys_exists else '缺失'}")
    print(f"配置路径: {config_path}")
    print(f"密钥路径: {keys_path}")

    config = {}
    if config_exists:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    wxid = config.get("wxid")
    db_base_path = config.get("db_base_path")
    data_dir = config.get("data_dir")

    print(f"wxid: {wxid or '未配置'}")
    print(f"db_base_path: {db_base_path or '未配置'}")
    print(f"data_dir: {data_dir or '未配置'}")

    complete = config_exists and keys_exists and wxid and db_base_path
    if complete:
        print("状态: 可直接使用 `./wechat-insight list` 或 `./wechat-insight export ...`")
        return 0

    print("状态: 需要先执行 `./wechat-insight setup`")
    return 1


def main(argv=None, extract_module=None, export_module=None, features_module=None,
         daily_module=None, digest_module=None, customer_module=None, labels_module=None,
         report_data_module=None, html_module=None, dashboard_module=None,
         emotion_module=None, mbti_module=None, speech_module=None, social_module=None,
         config_path=DEFAULT_CONFIG_PATH, keys_path=DEFAULT_KEYS_PATH):
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] in {
        "list", "export", "features", "daily", "customer", "labels",
        "digest", "report-data", "html", "dashboard", "emotion", "mbti", "speech", "social",
    }:
        if argv[0] == "list":
            export_module = export_module or load_script_module(
                "export_messages", "scripts/export_messages.py"
            )
            return export_module.main(argv[1:] + ["--list-chats"])
        if argv[0] == "export":
            export_module = export_module or load_script_module(
                "export_messages", "scripts/export_messages.py"
            )
            return export_module.main(argv[1:])
        if argv[0] == "features":
            features_module = features_module or load_script_module(
                "build_features", "scripts/features/build_features.py"
            )
            return features_module.main(argv[1:])
        if argv[0] == "daily":
            daily_module = daily_module or load_script_module(
                "daily", "scripts/analyze/daily.py"
            )
            return daily_module.main(argv[1:])
        if argv[0] == "digest":
            digest_module = digest_module or load_script_module(
                "digest", "scripts/analyze/digest.py"
            )
            return digest_module.main(argv[1:])
        if argv[0] == "customer":
            customer_module = customer_module or load_script_module(
                "customer", "scripts/analyze/customer.py"
            )
            return customer_module.main(argv[1:])
        if argv[0] == "report-data":
            report_data_module = report_data_module or load_script_module(
                "report_data", "scripts/analyze/report_data.py"
            )
            return report_data_module.main(argv[1:])
        if argv[0] == "html":
            html_module = html_module or load_script_module(
                "html_report", "scripts/analyze/html_report.py"
            )
            return html_module.main(argv[1:])
        if argv[0] == "dashboard":
            dashboard_module = dashboard_module or load_script_module(
                "dashboard", "scripts/analyze/dashboard.py"
            )
            return dashboard_module.main(argv[1:])
        if argv[0] == "emotion":
            emotion_module = emotion_module or load_script_module(
                "emotion", "scripts/analyze/emotion.py"
            )
            return emotion_module.main(argv[1:])
        if argv[0] == "mbti":
            mbti_module = mbti_module or load_script_module(
                "mbti", "scripts/analyze/mbti.py"
            )
            return mbti_module.main(argv[1:])
        if argv[0] == "speech":
            speech_module = speech_module or load_script_module(
                "speech_patterns", "scripts/analyze/speech_patterns.py"
            )
            return speech_module.main(argv[1:])
        if argv[0] == "social":
            social_module = social_module or load_script_module(
                "social_graph", "scripts/analyze/social_graph.py"
            )
            return social_module.main(argv[1:])
        labels_module = labels_module or load_script_module(
            "contact_labels", "scripts/analyze/contact_labels.py"
        )
        return labels_module.main(argv[1:])

    parser = build_parser(config_path=config_path, keys_path=keys_path)
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    extract_module = extract_module or load_script_module(
        "extract_keys", "scripts/extract_keys.py"
    )
    if args.command == "setup":
        extract_module = extract_module or load_script_module(
            "extract_keys", "scripts/extract_keys.py"
        )
        return extract_module.main([])

    if args.command == "doctor":
        return run_doctor(
            config_path=args.config_path,
            keys_path=args.keys_path,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
