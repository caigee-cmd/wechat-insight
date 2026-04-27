#!/usr/bin/env python3
"""Prepare and launch the local React dashboard."""

import argparse
import importlib.util
import os
import pathlib
import shlex
import shutil
import subprocess


CURRENT_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent
DEFAULT_PROJECT_DIR = ROOT_DIR / "dashboard"


def load_script_module(name, relative_path):
    path = ROOT_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REPORT_DATA_MODULE = load_script_module("report_data", "scripts/analyze/report_data.py")


def ensure_dashboard_project(project_dir):
    project_path = pathlib.Path(project_dir)
    package_json = project_path / "package.json"
    if not package_json.exists():
        raise FileNotFoundError(f"未找到 dashboard 项目: {package_json}")
    public_dir = project_path / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    return project_path


def prepare_dashboard_payload(project_dir=None, payload_path=None, input_path=None,
                              config_path=None, labels_path=None):
    resolved_project_dir = ensure_dashboard_project(project_dir or DEFAULT_PROJECT_DIR)

    if payload_path:
        source_payload_path = pathlib.Path(os.path.expanduser(payload_path))
    else:
        payload = REPORT_DATA_MODULE.build_report_data_payload(
            input_path=input_path,
            config_path=config_path,
            labels_path=labels_path,
        )
        source_payload_path = pathlib.Path(payload["artifacts"]["payload_path"])

    if not source_payload_path.exists():
        raise FileNotFoundError(f"未找到 payload 文件: {source_payload_path}")

    dashboard_payload_path = resolved_project_dir / "public" / "report_payload.json"
    shutil.copyfile(source_payload_path, dashboard_payload_path)
    return {
        "project_dir": str(resolved_project_dir),
        "source_payload_path": str(source_payload_path),
        "dashboard_payload_path": str(dashboard_payload_path),
    }


def build_dashboard_command(project_dir=None, host="127.0.0.1", port=4173):
    resolved_project_dir = pathlib.Path(project_dir or DEFAULT_PROJECT_DIR)
    shell = os.environ.get("SHELL") or "/bin/zsh"
    command = "npm run dev -- --host {host} --port {port}".format(
        host=shlex.quote(host),
        port=shlex.quote(str(port)),
    )
    return {
        "cwd": str(resolved_project_dir),
        "argv": [shell, "-lc", command],
    }


def ensure_dashboard_dependencies(project_dir):
    node_modules = pathlib.Path(project_dir) / "node_modules"
    if node_modules.exists():
        return
    subprocess.run(
        ["npm", "install"],
        cwd=project_dir,
        check=True,
    )


def run_dashboard(project_dir=None, payload_path=None, input_path=None,
                  config_path=None, labels_path=None, host="127.0.0.1",
                  port=4173, skip_install=False):
    payload_result = prepare_dashboard_payload(
        project_dir=project_dir,
        payload_path=payload_path,
        input_path=input_path,
        config_path=config_path,
        labels_path=labels_path,
    )
    command = build_dashboard_command(
        project_dir=payload_result["project_dir"],
        host=host,
        port=port,
    )

    if not skip_install:
        ensure_dashboard_dependencies(payload_result["project_dir"])

    result = subprocess.run(
        command["argv"],
        cwd=command["cwd"],
        check=False,
    )
    return {
        **payload_result,
        "host": host,
        "port": port,
        "exit_code": result.returncode,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="启动本地 React dashboard")
    parser.add_argument("--payload", help="已存在的 report_payload.json 路径")
    parser.add_argument("--input", "-i", help="输入 JSONL 文件路径或 glob，默认取最新导出文件")
    parser.add_argument("--labels", help="联系人标签文件路径")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--host", default="127.0.0.1", help="dashboard 监听地址")
    parser.add_argument("--port", type=int, default=4173, help="dashboard 端口")
    parser.add_argument("--project-dir", help="dashboard 项目目录")
    parser.add_argument("--skip-install", action="store_true", help="跳过 npm install")
    args = parser.parse_args(argv)

    print("=" * 50)
    print("WeChat Insight Dashboard")
    print("=" * 50)

    result = run_dashboard(
        project_dir=args.project_dir,
        payload_path=args.payload,
        input_path=args.input,
        config_path=args.config,
        labels_path=args.labels,
        host=args.host,
        port=args.port,
        skip_install=args.skip_install,
    )

    print(f"项目目录: {result['project_dir']}")
    print(f"Payload 来源: {result['source_payload_path']}")
    print(f"Dashboard Payload: {result['dashboard_payload_path']}")
    print(f"访问地址: http://{result['host']}:{result['port']}")
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
