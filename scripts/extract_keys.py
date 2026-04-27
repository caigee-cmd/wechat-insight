#!/usr/bin/env python3
"""
微信 Mac 4.x 数据库密钥提取工具
使用 frida hook CCKeyDerivationPBKDF 捕获所有数据库的加密密钥
"""

import os
import sys
import json
import glob
import subprocess
import time
import shutil

KEYS_FILE = os.path.expanduser("~/.config/wechat-keys.json")
CONFIG_FILE = os.path.expanduser("~/.config/wechat-insight.json")
WECHAT_APP = "/Applications/WeChat.app"
WECHAT_COPY = os.path.expanduser("~/Desktop/WeChat.app")
FRIDA_LOG = "/tmp/wechat_frida_keys.log"
WECHAT_BASE = os.path.expanduser(
    "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files"
)

HOOK_TARGETS = [
    {"name": "CCKeyDerivationPBKDF", "kind": "commoncrypto"},
    {"name": "PKCS5_PBKDF2_HMAC", "kind": "openssl"},
]


def build_frida_script():
    targets_json = json.dumps(HOOK_TARGETS, ensure_ascii=True)
    return f"""
'use strict';

var HOOK_TARGETS = {targets_json};

function findExport(name) {{
    var modules = Process.enumerateModules();
    for (var i = 0; i < modules.length; i++) {{
        try {{
            var exp = modules[i].enumerateExports();
            for (var j = 0; j < exp.length; j++) {{
                if (exp[j].name === name) {{
                    return exp[j].address;
                }}
            }}
        }} catch (e) {{}}
    }}
    return null;
}}

function toHex(ptrValue, length) {{
    if (!ptrValue || length <= 0) {{
        return '';
    }}
    var nativePtr;
    try {{
        nativePtr = ptr(ptrValue);
    }} catch (e) {{
        return '';
    }}
    if (nativePtr.isNull()) {{
        return '';
    }}
    var out = '';
    for (var i = 0; i < length; i++) {{
        var value = nativePtr.add(i).readU8();
        out += ('0' + value.toString(16)).slice(-2);
    }}
    return out;
}}

HOOK_TARGETS.forEach(function(target) {{
    var address = findExport(target.name);
    if (!address) {{
        send({{type: 'status', msg: target.name + ' not found'}});
        return;
    }}

    send({{type: 'status', msg: 'Hooked ' + target.name + ' at ' + address}});

    Interceptor.attach(address, {{
        onEnter: function(args) {{
            this.targetName = target.name;

            if (target.kind === 'commoncrypto') {{
                this.passwordLen = args[2].toInt32();
                this.salt = args[3];
                this.saltLen = args[4].toInt32();
                this.rounds = args[6].toInt32();
                this.derivedKey = args[7];
                this.derivedKeyLen = args[8].toInt32();
            }} else if (target.kind === 'openssl') {{
                this.passwordLen = args[1].toInt32();
                this.salt = args[2];
                this.saltLen = args[3].toInt32();
                this.rounds = args[4].toInt32();
                this.derivedKeyLen = args[6].toInt32();
                this.derivedKey = args[7];
            }}
        }},
        onLeave: function(retval) {{
            try {{
                var entry = {{
                    symbol: this.targetName,
                    rounds: this.rounds,
                    salt: toHex(this.salt, Math.min(this.saltLen, 32)),
                    dk: toHex(this.derivedKey, Math.min(this.derivedKeyLen, 64)),
                    dkLen: this.derivedKeyLen,
                    saltLen: this.saltLen,
                    passwordLen: this.passwordLen
                }};
                send({{type: 'key', data: entry}});
            }} catch (e) {{
                var detail = e && e.stack ? e.stack : e;
                send({{type: 'error', msg: this.targetName + ' read failed: ' + detail}});
            }}
        }}
    }});
}});
"""


FRIDA_JS = build_frida_script()


def run_cmd(cmd, check=True):
    """Run a shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  [ERROR] {cmd}")
        print(f"  {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def check_env():
    """Step 1: Check prerequisites"""
    print("\n[1/5] 检查环境...")

    if sys.platform != "darwin":
        print("  [ERROR] 仅支持 macOS")
        sys.exit(1)

    if not os.path.exists(WECHAT_APP):
        print(f"  [ERROR] 未找到微信: {WECHAT_APP}")
        print("  请确认已安装微信 Mac 版")
        sys.exit(1)
    print("  ✓ 微信已安装")

    # Check Python version
    if sys.version_info < (3, 9):
        print(f"  [ERROR] Python 版本过低: {sys.version}，需要 3.9+")
        sys.exit(1)
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")

    return True


def prepare_wechat():
    """Step 2: Copy and codesign WeChat"""
    print("\n[2/5] 准备微信签名副本...")

    if os.path.exists(WECHAT_COPY):
        existing_sig = run_cmd(f"codesign -dv {WECHAT_COPY} 2>&1 | grep 'Signature'", check=False)
        print("  ✓ 签名副本已存在")
    else:
        print(f"  复制微信到 {WECHAT_COPY}...")
        shutil.copytree(WECHAT_APP, WECHAT_COPY, symlinks=True)

    print("  重新签名（去掉 Hardened Runtime）...")
    run_cmd(f"codesign --force --deep --sign - {WECHAT_COPY}")
    print("  ✓ 签名完成")


def install_frida():
    """Step 3: Check/install frida"""
    print("\n[3/5] 检查 frida...")

    try:
        import frida
        print(f"  ✓ frida 已安装 (版本: {frida.__version__})")
        return True
    except ImportError:
        pass

    print("  正在安装 frida...")
    run_cmd(f"{sys.executable} -m pip install frida frida-tools")
    print("  ✓ frida 安装完成")
    return True


def extract_keys():
    """Step 4: Run frida to extract keys"""
    print("\n[4/5] 提取密钥...")

    import frida

    # Kill existing WeChat
    run_cmd("killall WeChat 2>/dev/null", check=False)
    time.sleep(2)

    # Clear previous log
    if os.path.exists(FRIDA_LOG):
        os.remove(FRIDA_LOG)

    wechat_binary = os.path.join(WECHAT_COPY, "Contents", "MacOS", "WeChat")

    keys = []

    def on_message(message, data):
        if message['type'] == 'send':
            payload = message['payload']
            if payload.get('type') == 'key':
                keys.append(payload['data'])
                with open(FRIDA_LOG, 'a') as f:
                    f.write(json.dumps(payload['data']) + '\n')
                print(f"  [KEY] rounds={payload['data']['rounds']} salt={payload['data']['salt'][:16]}... dk={payload['data']['dk'][:16]}...")
            elif payload.get('type') == 'status':
                print(f"  {payload['msg']}")
            elif payload.get('type') == 'error':
                print(f"  [ERROR] {payload['msg']}")
        elif message['type'] == 'error':
            print(f"  [FRIDA ERROR] {message.get('description', message)}")

    print("  启动 frida hook...")
    print("  " + "=" * 50)

    try:
        print("  正在启动微信...")
        device = frida.get_local_device()
        pid = device.spawn([wechat_binary])
        session = device.attach(pid)
        script = session.create_script(FRIDA_JS)
        script.on('message', on_message)
        script.load()
        device.resume(pid)

        print("  微信已启动，请登录微信。")
        print("  密钥会在微信打开数据库时自动捕获...")
        print("  你有最多 5 分钟时间完成登录。")
        print(f"  密钥日志: {FRIDA_LOG}")

        for i in range(300, 0, -1):
            time.sleep(1)
            if i % 30 == 0:
                print(f"  剩余 {i} 秒... (已捕获 {len(keys)} 个密钥)")
            # 一旦捕获到至少3个密钥，多等10秒确保没有遗漏，然后提前结束
            if len(keys) >= 3 and i <= 290:
                print(f"  已捕获 {len(keys)} 个密钥，等待10秒确保无遗漏...")
                time.sleep(10)
                break

        print(f"\n  共捕获 {len(keys)} 个密钥")
        session.detach()

    except KeyboardInterrupt:
        print("\n  用户中断")

    print("  " + "=" * 50)

    if not keys:
        print("  [ERROR] 未捕获到任何密钥。请确认已登录微信。")
        sys.exit(1)

    print(f"  ✓ 共捕获 {len(keys)} 个密钥")
    return keys


def pick_db_base(db_dirs):
    """Pick the most recently active WeChat account directory."""
    if not db_dirs:
        return None

    def sort_key(path):
        message_db = os.path.join(path, "message", "message_0.db")
        candidate = message_db if os.path.exists(message_db) else path
        try:
            return os.path.getmtime(candidate)
        except OSError:
            return 0

    return max(db_dirs, key=sort_key)


def get_db_salt(db_path):
    with open(db_path, "rb") as f:
        return f.read(16).hex()


def find_db_key(db_path, keys):
    """Match a database to its key using the file salt."""
    db_salt = get_db_salt(db_path)

    for key_entry in keys:
        dk = key_entry.get("dk", "")
        if (
            key_entry.get("rounds") == 256000
            and key_entry.get("salt") == db_salt
            and len(dk) >= 64
        ):
            return dk[:64]

    return None


def detect_databases():
    """Auto-detect WeChat database paths and wxid"""
    print("\n[5/5] 匹配密钥到数据库...")

    # Find wxid directories
    pattern = os.path.join(WECHAT_BASE, "*/db_storage")
    db_dirs = glob.glob(pattern)

    if not db_dirs:
        print(f"  [ERROR] 未找到微信数据库目录")
        print(f"  搜索路径: {pattern}")
        sys.exit(1)

    db_base = pick_db_base(db_dirs)
    wxid = db_base.split("/xwechat_files/")[1].split("/")[0]
    print(f"  ✓ 检测到 wxid: {wxid}")
    print(f"  ✓ 数据库路径: {db_base}")

    # Load captured keys
    keys = []
    with open(FRIDA_LOG) as f:
        for line in f:
            try:
                keys.append(json.loads(line.strip()))
            except:
                continue

    # Match keys to databases by trying each key
    db_files = {
        "message_0": os.path.join(db_base, "message", "message_0.db"),
        "contact": os.path.join(db_base, "contact", "contact.db"),
        "session": os.path.join(db_base, "session", "session.db"),
    }

    result = {}
    for db_name, db_path in db_files.items():
        if not os.path.exists(db_path):
            print(f"  [WARN] 数据库不存在: {db_path}")
            continue

        matched_key = find_db_key(db_path, keys)
        if matched_key:
            result[db_name] = matched_key
            print(f"  ✓ {db_name}.db → 密钥已匹配")
        else:
            print(f"  [WARN] {db_name}.db 未匹配到密钥")

    if not result:
        print("\n  [ERROR] 未能匹配任何密钥到数据库")
        print("  请确认：")
        print("  1. 已正常登录微信")
        print("  2. 微信版本为 Mac 4.x")
        sys.exit(1)

    # Save keys
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    with open(KEYS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  ✓ 密钥已保存到 {KEYS_FILE}")

    # Also create/update config with detected paths
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    config["wxid"] = wxid
    config["db_base_path"] = db_base
    config.setdefault("data_dir", os.path.expanduser("~/.wechat-insight/data"))
    config.setdefault("report_dir", os.path.expanduser("~/.wechat-insight/reports"))

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 配置已更新 {CONFIG_FILE}")

    # Create data directories
    os.makedirs(config["data_dir"], exist_ok=True)
    os.makedirs(config["report_dir"], exist_ok=True)
    print(f"  ✓ 数据目录已创建: {config['data_dir']}")

    return result


def main(argv=None):
    print("=" * 50)
    print("微信 Mac 4.x 数据库密钥提取工具")
    print("=" * 50)

    check_env()
    prepare_wechat()
    install_frida()
    extract_keys()
    detect_databases()

    print("\n" + "=" * 50)
    print("密钥提取完成！")
    print(f"  密钥文件: {KEYS_FILE}")
    print(f"  配置文件: {CONFIG_FILE}")
    print("\n接下来请在 Claude Code 中说 '微信分析' 来选择分析类型。")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
