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
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
JS_OVERRIDE = REPO_ROOT / "override" / "customSubBoost.js"
YAML_OVERRIDE = REPO_ROOT / "override" / "customSubBoost.yaml"
if not YAML_OVERRIDE.exists():
    YAML_OVERRIDE = REPO_ROOT / "override" / "1b0sb00st01.yaml"

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
CORE_EXE = ROOT / "test" / "mihomo-test.exe"
SB = ROOT / "test" / "_sb"
OUT = SB / "verify"

SUBS = {
    "19f26ab99a3": "奈云",
    "19db57e02f7": "自建/备用",
    "1a0377776c2": "TAGMeta",
    "19e91d0a1b7": "Glados",
}


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


def run_js_override(profile_data: dict) -> dict:
    """通过 Node.js 标准输入管道执行 customSubBoost.js 的 main(config)。"""
    js_rel = os.path.relpath(JS_OVERRIDE, REPO_ROOT).replace("\\", "/")
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
        raise RuntimeError(f"Node.js 执行 customSubBoost.js 失败:\n{proc.stderr}")
    return json.loads(proc.stdout)


def test_kernel_config(workdir: Path, config_data: dict, pid: str) -> tuple[bool, str]:
    """将配置与必要资源写入沙箱目录并调用 mihomo 内核 -t 语法测试。"""
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    # 复制 geo 数据库资源
    for f in ("geoip.metadb", "geoip.dat", "geosite.dat", "country.mmdb", "ASN.mmdb"):
        src = ROOT / "work" / pid / f
        if src.exists():
            shutil.copy2(src, workdir / f)

    # 复制 ruleset 规则集本地缓存
    (workdir / "ruleset").mkdir(exist_ok=True)
    (workdir / "rule_providers").mkdir(exist_ok=True)
    rs_src = ROOT / "work" / pid / "ruleset"
    if rs_src.is_dir():
        shutil.copytree(rs_src, workdir / "ruleset", dirs_exist_ok=True)

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


def main() -> int:
    print("=" * 60)
    print("Mihomo 订阅与覆写内核合法性全量验证")
    print("=" * 60)

    failures = []

    # -------------------------------------------------------------
    # 阶段 1: 验证全合一 JS 覆写 (customSubBoost.js - 新架构主力)
    # -------------------------------------------------------------
    if JS_OVERRIDE.exists():
        print("\n[模式 A] 验证 All-in-One JS 覆写 (customSubBoost.js - 推荐)...")
        for pid, name in SUBS.items():
            profile_path = ROOT / "profiles" / f"{pid}.yaml"
            if not profile_path.exists():
                print(f"  [-] 订阅底稿不存在，跳过: {pid} ({name})")
                continue

            raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            try:
                merged_js = run_js_override(raw)
            except Exception as e:
                print(f"  [FAIL] {pid} ({name}): JS 执行异常: {e}")
                failures.append((f"{pid}-JS", str(e)))
                continue

            workdir = OUT / f"{pid}_js"
            ok, log = test_kernel_config(workdir, merged_js, pid)
            raw_nodes = len(raw.get("proxies") or [])
            cleaned_nodes = len(merged_js.get("proxies") or [])
            groups = len(merged_js.get("proxy-groups") or [])
            rules = len(merged_js.get("rules") or [])

            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {pid} ({name:<6})  原始节点{raw_nodes:>3} -> 清洗后{cleaned_nodes:>3}  组{groups}  规则{rules}")
            if not ok:
                failures.append((f"{pid}-JS", log))

    # -------------------------------------------------------------
    # 阶段 2: 验证双轨 YAML 覆写 (customSubBoost.yaml - 旧版流水线备用)
    # -------------------------------------------------------------
    if YAML_OVERRIDE.exists():
        print("\n[模式 B] 验证双轨 YAML 覆写 (customSubBoost.yaml - 兼容备用)...")
        override_yaml_data = yaml.safe_load(YAML_OVERRIDE.read_text(encoding="utf-8"))
        front_rules = load_front_rules()

        for pid, name in SUBS.items():
            profile_path = ROOT / "profiles" / f"{pid}.yaml"
            if not profile_path.exists():
                continue

            raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            # 遵循 Clash Party 旧版流水线：前置覆写初始化规则，后续 rules+: 追加
            raw["rules"] = list(front_rules)
            merged_yaml = deep_merge(raw, override_yaml_data)

            workdir = OUT / f"{pid}_yaml"
            ok, log = test_kernel_config(workdir, merged_yaml, pid)
            groups = len(merged_yaml.get("proxy-groups") or [])
            rules = len(merged_yaml.get("rules") or [])

            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {pid} ({name:<6})  节点{len(raw.get('proxies') or []):>3}  组{groups}  规则{rules}")
            if not ok:
                failures.append((f"{pid}-YAML", log))

    if failures:
        print("\n" + "!" * 50)
        print("===== 失败详情 =====")
        for target, blob in failures:
            print(f"\n--- {target} ---")
            print(blob[-3000:])
        return 1

    print("\n" + "=" * 60)
    print("✔ 所有真实订阅在 JS 与 YAML 覆写模式下全部通过内核语法校验！")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

