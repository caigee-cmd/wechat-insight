"""隐私护栏：断言分析链路里没有任何出网能力。

这条测试是项目对用户的可验证承诺——"你的聊天内容不出本机"。
它会扫描所有数据处理脚本（导出、特征、分析、报告、分享卡），确认没有
任何模块 import 了具备联网能力的库。一旦有人不小心引入 requests / urllib /
socket 等依赖，这条测试会立刻失败，提醒"隐私承诺被破坏了"。

说明：工具安装（pip / npm）和 setup 阶段注入 Frida 会联网，但那只是下载
公共依赖包，发生在数据处理之外，且不经过这里扫描的模块，因此不影响"聊天
内容零上传"的承诺。
"""

import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]

# 具备出网能力的模块前缀，分析链路里出现任意一个都视为破坏隐私承诺。
FORBIDDEN_TOP_LEVEL = {
    "socket",
    "ssl",
    "urllib",
    "http",
    "requests",
    "httpx",
    "aiohttp",
    "websocket",
    "websockets",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "xmlrpc",
    "asyncio",  # 拉进来通常是为了网络 IO，分析链路不需要
}

# 只扫描"数据处理链路"。setup/密钥提取（extract_keys）允许联网装 Frida，
# 不在隐私承诺覆盖范围内，因此排除。
SCANNED_DIRS = [
    ROOT / "scripts" / "analyze",
    ROOT / "scripts" / "features",
]
SCANNED_FILES = [
    ROOT / "scripts" / "export_messages.py",
    ROOT / "wechat_insight_cli.py",
]


def iter_source_files():
    for directory in SCANNED_DIRS:
        yield from sorted(directory.rglob("*.py"))
    for file in SCANNED_FILES:
        yield file


def imported_top_level_modules(source_path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules


class NoNetworkGuardTests(unittest.TestCase):
    def test_analysis_pipeline_imports_no_network_libraries(self):
        offenders = {}
        for source_path in iter_source_files():
            forbidden = imported_top_level_modules(source_path) & FORBIDDEN_TOP_LEVEL
            if forbidden:
                rel = source_path.relative_to(ROOT)
                offenders[str(rel)] = sorted(forbidden)

        self.assertEqual(
            offenders,
            {},
            msg=(
                "隐私护栏失败：分析链路里出现了具备联网能力的 import，"
                f"可能导致聊天内容外泄 -> {offenders}"
            ),
        )

    def test_guard_actually_scans_source_files(self):
        # 防止扫描列表被改空导致测试"假通过"。
        files = list(iter_source_files())
        self.assertGreater(len(files), 5, "扫描到的源文件过少，护栏可能失效")


if __name__ == "__main__":
    unittest.main()
