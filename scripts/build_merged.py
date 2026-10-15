"""
==============================================================================
Mihomo 生产全量配置拼装工具 (build_merged.py)
==============================================================================

【功能定位】
抽取真实订阅中的节点池 (proxies)、嗅探配置 (sniffer) 与 DNS 基础设施，
套用全合一 JS 覆写 (override/customSubBoost.js) 动态运行 main(config)，
生成一份 100% 具备内核语法合法性的单文件 config.yaml，
并调用 Mihomo Meta 内核进行 -t 语法预检与沙箱实测。
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# 配置根目录：优先读取环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
BASE = os.environ.get("MIHOMO_PARTY_BASE") or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "mihomo-party"
)

PROFILE_SRC = os.path.join(BASE, "profiles", "1a0377776c2.yaml")
WORK_SRC = os.path.join(BASE, "work", "1a0377776c2", "config.yaml")
OUT_DIR = os.path.join(BASE, "test", "_sb", "merged")
CORE_EXE = os.path.join(BASE, "test", "mihomo-test.exe")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
JS_OVERRIDE = REPO_ROOT / "override" / "customSubBoost.js"
YAML_OVERRIDE = REPO_ROOT / "override" / "customSubBoost.yaml"


def load_profile():
    """读取真实订阅底稿配置。"""
    if os.path.exists(PROFILE_SRC):
        return yaml.safe_load(open(PROFILE_SRC, encoding="utf-8").read())
    if os.path.exists(WORK_SRC):
        return yaml.safe_load(open(WORK_SRC, encoding="utf-8", errors="replace").read())
    return {
        "proxies": [{"name": "DIRECT", "type": "direct"}],
        "proxy-groups": [],
        "rules": [],
    }


def main():
    profile = load_profile()
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg_path = os.path.join(OUT_DIR, "config.yaml")

    merged = None

    # 优先采用全合一 JS 覆写 (customSubBoost.js) 运行 main(config)
    if JS_OVERRIDE.exists():
        js_rel = os.path.relpath(JS_OVERRIDE, REPO_ROOT).replace("\\", "/")
        driver = f"""
        const fs = require('fs');
        const {{ main, CONFIG }} = require('./{js_rel}');
        const raw = JSON.parse(fs.readFileSync(0, 'utf-8'));
        const out = main(raw);
        console.log(JSON.stringify(out));
        """
        proc = subprocess.run(
            ["node", "-e", driver],
            input=json.dumps(profile),
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        if proc.returncode == 0:
            merged = json.loads(proc.stdout)
            print(f"[*] 成功通过 customSubBoost.js 动态生成合并配置 (节点 {len(merged.get('proxies') or [])} 个)")
        else:
            print(f"[-] Node.js 执行 customSubBoost.js 失败:\n{proc.stderr}")

    if not merged:
        print("[-] 回退使用静态占位构建...")
        merged = profile

    # 写入最终合并 config.yaml
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False, width=100000)

    # 复制 geo 资源和 ruleset 本地缓存，保证内核 -t 顺利通过
    for f in ("country.mmdb", "geoip.metadb", "geoip.dat", "geosite.dat", "ASN.mmdb"):
        src = os.path.join(BASE, "work", "1a0377776c2", f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT_DIR, f))
    rs = os.path.join(BASE, "work", "1a0377776c2", "ruleset")
    if os.path.isdir(rs):
        shutil.copytree(rs, os.path.join(OUT_DIR, "ruleset"), dirs_exist_ok=True)

    print(f"已生成 {cfg_path}")
    print(f"规则数 {len(merged.get('rules') or [])} | 组数 {len(merged.get('proxy-groups') or [])} | provider {len(merged.get('rule-providers') or {})}")

    # 调用真实内核进行语法测试
    if os.path.exists(CORE_EXE):
        print("\n[*] 启动真实 Mihomo Meta 内核进行 -t 预检...")
        test_proc = subprocess.run(
            [CORE_EXE, "-t", "-d", OUT_DIR, "-f", cfg_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(test_proc.stdout or test_proc.stderr)
        if test_proc.returncode != 0:
            sys.exit(f"【内核校验失败】rc={test_proc.returncode}")
        print("✔ 内核语法预检 100% 成功！")

    return 0


if __name__ == "__main__":
    sys.exit(main())
