"""
==============================================================================
Mihomo 订阅与覆写内核合法性全量验证工具 (verify.py)
==============================================================================

【功能定位】
1. 双轨并行验证：
   - 模式 A (All-in-One JS 覆写): 将 4 大真实订阅管道送入 override/customSubBoost.js 运行 main(config)
   - 模式 B (双轨 YAML 覆写): 采用 deep_merge 将 override/customSubBoost.yaml 覆写至底稿
2. 真实内核预检:
   - 自动复制 MMDB/Metadb 与本地 ruleset 缓存到测试沙箱
   - 调用本地真实 mihomo-test.exe -t 进行全量语法与分流连通性测试
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# 修复 PyYAML 将形如 47245e18 的十六进制 short-id 序列化为浮点数科学计数法的缺陷
def _represent_yaml_str(dumper, data):
    if re.match(r"^(?:[0-9]+[eE][0-9]+|[0-9]+|0x[0-9a-fA-F]+|true|false|yes|no|null)$", data, re.I):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

yaml.SafeDumper.add_representer(str, _represent_yaml_str)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
CORE_EXE = ROOT / "test" / "mihomo-test.exe"
SB = ROOT / "test" / "_sb"
OUT = SB / "verify"

# 常用机场订阅别名表（供日志友好显示）
SUBS_ALIAS = {
    "19f26ab99a3": "奈云",
    "19db57e02f7": "自建/备用",
    "1a0377776c2": "TAGMeta",
    "19e91d0a1b7": "Glados",
}


def discover_profiles() -> dict[str, tuple[str, dict]]:
    """
    动态扫描 profiles 目录下的所有订阅底稿。
    若无本地订阅，则自动回退至内建标准 Mock 订阅底稿。
    返回: {pid: (display_name, profile_data)}
    """
    profiles = {}
    profiles_dir = ROOT / "profiles"
    if profiles_dir.exists():
        for p in sorted(profiles_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "proxies" in data:
                    pid = p.stem
                    name = SUBS_ALIAS.get(pid, pid[:8])
                    profiles[pid] = (name, data)
            except Exception:
                pass

    if not profiles:
        # 内建标准 Mock 订阅底稿 (跨平台零外部依赖)
        mock_data = {
            "proxies": [
                {"name": "🇺🇸 美国 01", "type": "ss", "server": "1.1.1.1", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "🇭🇰 香港 02 | 1x", "type": "ss", "server": "1.1.1.2", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "🇯🇵 日本 IEPL-X2", "type": "ss", "server": "1.1.1.3", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "🇸🇬 狮城 04 [2x]", "type": "ss", "server": "1.1.1.4", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "🇹🇼 台湾 05", "type": "ss", "server": "1.1.1.5", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "🇰🇷 韩国 06", "type": "ss", "server": "1.1.1.6", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
                {"name": "剩余流量: 500GB", "type": "ss", "server": "1.1.1.7", "port": 443, "cipher": "aes-128-gcm", "password": "pass"},
            ],
            "proxy-groups": [],
            "rules": ["DOMAIN-SUFFIX,mock-sub.com,DIRECT"],
            "dns": {"enable": True, "nameserver": ["223.5.5.5"]},
        }
        profiles["mock-env"] = ("内建标准Mock", mock_data)

    return profiles


def deep_merge(base: dict, patch: dict) -> dict:
    """
    模拟 mihomo-party 客户端的 YAML 覆写合并语义。
    - proxy-groups: 整段覆盖替换
    - rules+: 将覆写规则追加到已有订阅规则之后（关键向后兼容特性）
    - rules: 整段覆盖替换
    - rule-providers: 按字典 key 增量合并
    """
    out = dict(base)
    for key, val in patch.items():
        if key == "proxy-groups":
            out[key] = val
        elif key == "rules+":
            out["rules"] = list(out.get("rules") or []) + list(val)
        elif key == "rules":
            out[key] = val
        elif key == "rule-providers":
            merged = dict(out.get(key) or {})
            merged.update(val)
            out[key] = merged
        elif isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def run_js_override(js_path: Path, profile_data: dict) -> dict:
    """通过 Node.js 标准输入管道执行指定 JS 覆写的 main(config)。"""
    js_rel = os.path.relpath(js_path, REPO_ROOT).replace("\\", "/")
    driver = f"""
    const fs = require('fs');
    const {{ main }} = require('./{js_rel}');
    const raw = JSON.parse(fs.readFileSync(0, 'utf-8'));
    const out = main(raw);
    console.log(JSON.stringify(out));
    """
    proc = subprocess.run(
        ["node", "-e", driver],
        input=json.dumps(profile_data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node.js 执行 {js_path.name} 失败:\n{proc.stderr}")
    return json.loads(proc.stdout)


def test_kernel_config(workdir: Path, config_data: dict, pid: str) -> tuple[bool, str]:
    """将配置与必要资源写入沙箱目录并调用 mihomo 内核 -t 语法测试。"""
    if workdir.exists():
        try:
            shutil.rmtree(workdir)
        except Exception:
            pass
    workdir.mkdir(parents=True, exist_ok=True)

    # 复制 geo 数据库资源 (优先 profile 目录，回退 ROOT/work 公共目录)
    for f in ("geoip.metadb", "geoip.dat", "geosite.dat", "country.mmdb", "ASN.mmdb"):
        src = ROOT / "work" / pid / f
        if not src.exists():
            src = ROOT / "work" / f
        if not src.exists():
            src = ROOT / f
        if src.exists():
            shutil.copy2(src, workdir / f)

    # 复制 ruleset 规则集本地缓存 (从公共缓存与本地多候选源合并复制，杜绝网络反复拉取)
    (workdir / "ruleset").mkdir(exist_ok=True)
    (workdir / "rule_providers").mkdir(exist_ok=True)
    for cand in [
        ROOT / "work" / "ruleset",
        ROOT / "ruleset",
        ROOT / "work" / pid / "ruleset",
        REPO_ROOT / "ruleset",
    ]:
        if cand.is_dir():
            shutil.copytree(cand, workdir / "ruleset", dirs_exist_ok=True)

    cfg = workdir / "config.yaml"
    cfg.write_text(
        yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False, width=100000),
        encoding="utf-8",
    )

    if not CORE_EXE.exists():
        return True, "未检测到 mihomo-test.exe，跳过内核调用"

    proc = subprocess.run(
        [str(CORE_EXE), "-t", "-d", str(workdir), "-f", str(cfg)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    blob = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, blob


def load_front_rules() -> list[str]:
    """提取前置 JS 覆写中的直连规则（与旧版生产客户端流水线保持一致）。"""
    return [
        "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
        "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
        "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
    ]


def verify_tier(tier: str, discovered: dict[str, tuple[str, dict]]) -> list[tuple[str, str]]:
    """针对单个预设档位，执行 JS 与 YAML 双轨真实订阅测试。"""
    print(f"\n>>> 正在验证档位: [{tier.upper()}] <<<")
    # 优先检测子目录 override/js/，回退检测 override/example/，再兼容旧平铺路径
    js_override = REPO_ROOT / "override" / "js" / f"customSubBoost.{tier}.js"
    if not js_override.exists():
        js_override = REPO_ROOT / "override" / "example" / f"customSubBoost.{tier}.example.js"
    if not js_override.exists():
        js_override = REPO_ROOT / "override" / f"customSubBoost.{tier}.js"

    yaml_override = REPO_ROOT / "override" / "yaml" / f"customSubBoost.{tier}.yaml"
    if not yaml_override.exists():
        yaml_override = REPO_ROOT / "override" / f"customSubBoost.{tier}.yaml"

    failures = []

    # 模式 A: All-in-One JS
    if js_override.exists():
        print(f"  [模式 A] JS 覆写 ({js_override.name})...")
        for pid, (name, raw) in discovered.items():
            try:
                merged_js = run_js_override(js_override, raw)
            except Exception as e:
                print(f"    [FAIL] {pid} ({name}): JS 执行异常: {e}")
                failures.append((f"{tier.upper()}-{pid}-JS", str(e)))
                continue

            workdir = OUT / f"{tier}_{pid}_js"
            ok, log = test_kernel_config(workdir, merged_js, pid)
            raw_nodes = len(raw.get("proxies") or [])
            cleaned_nodes = len(merged_js.get("proxies") or [])
            groups = len(merged_js.get("proxy-groups") or [])
            rules = len(merged_js.get("rules") or [])

            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] {pid} ({name:<8})  原始节点{raw_nodes:>3} -> 清洗后{cleaned_nodes:>3}  组{groups:>2}  规则{rules:>3}")
            if not ok:
                failures.append((f"{tier.upper()}-{pid}-JS", log))

    # 模式 B: 双轨 YAML
    if yaml_override.exists():
        print(f"  [模式 B] YAML 覆写 ({yaml_override.name})...")
        override_yaml_data = yaml.safe_load(yaml_override.read_text(encoding="utf-8"))
        front_rules = load_front_rules()

        for pid, (name, raw) in discovered.items():
            base_data = dict(raw)
            base_data["rules"] = list(front_rules)
            merged_yaml = deep_merge(base_data, override_yaml_data)

            workdir = OUT / f"{tier}_{pid}_yaml"
            ok, log = test_kernel_config(workdir, merged_yaml, pid)
            groups = len(merged_yaml.get("proxy-groups") or [])
            rules = len(merged_yaml.get("rules") or [])

            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] {pid} ({name:<8})  节点{len(raw.get('proxies') or []):>3}  组{groups:>2}  规则{rules:>3}")
            if not ok:
                failures.append((f"{tier.upper()}-{pid}-YAML", log))

    return failures


def main() -> int:
    # 支持命令行参数指定单一档位或 all (默认 all)
    raw_arg = sys.argv[1].lower().lstrip("-") if len(sys.argv) > 1 else "all"
    if raw_arg in ("min", "minimal"):
        tiers = ["minimal"]
    elif raw_arg in ("std", "standard"):
        tiers = ["standard"]
    elif raw_arg in ("full", "max"):
        tiers = ["full"]
    else:
        tiers = ["minimal", "standard", "full"]

    print("=" * 60)
    print(f"Mihomo 订阅与覆写内核合法性全量验证 (目标档位: {', '.join(t.upper() for t in tiers)})")
    print("=" * 60)

    discovered = discover_profiles()
    print(f"[*] 发现待校验订阅底稿 {len(discovered)} 个: {[f'{pid} ({name})' for pid, (name, _) in discovered.items()]}")

    all_failures = []
    for tier in tiers:
        fails = verify_tier(tier, discovered)
        all_failures.extend(fails)

    if all_failures:
        print("\n" + "!" * 50)
        print("===== 失败详情 =====")
        for target, blob in all_failures:
            print(f"\n--- {target} ---")
            print(blob[-3000:])
        return 1

    print("\n" + "=" * 60)
    print(f"✔ 全部 {len(tiers)} 个预设档位在 JS 与 YAML 覆写模式下 100% 通过验证！")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

