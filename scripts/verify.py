"""把 SubBoost 覆写套到真实订阅上，生成一份完整配置供 mihomo 内核校验。"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
SB = ROOT / "test" / "_sb"
OUT = SB / "verify"

SUBS = ["19f26ab99a3", "19db57e02f7", "1a0377776c2", "19e91d0a1b7"]


def deep_merge(base: dict, patch: dict) -> dict:
    """模拟 mihomo-party 的 YAML 覆写合并：proxy-groups / rules 整段替换，
    rule-providers 按 key 合并，其余递归合并。"""
    out = dict(base)
    for key, val in patch.items():
        if key in ("proxy-groups", "rules"):
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


def main() -> int:
    override = yaml.safe_load((SB / "subboost-override.yaml").read_text(encoding="utf-8"))

    failures = []
    for pid in SUBS:
        raw = yaml.safe_load((ROOT / "profiles" / f"{pid}.yaml").read_text(encoding="utf-8"))
        merged = deep_merge(raw, override)

        # 去掉订阅自带的 dns（本覆写不涉及 dns，保留原样即可）
        workdir = OUT / pid
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        for f in ("geoip.dat", "geosite.dat", "country.mmdb", "ASN.mmdb"):
            src = ROOT / "work" / pid / f
            if src.exists():
                shutil.copy2(src, workdir / f)
        (workdir / "ruleset").mkdir(exist_ok=True)
        (workdir / "rule_providers").mkdir(exist_ok=True)

        cfg = workdir / "config.yaml"
        cfg.write_text(
            yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=100000),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [str(ROOT / "test" / "mihomo-test.exe"), "-t", "-d", str(workdir), "-f", str(cfg)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        blob = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
        groups = len(merged.get("proxy-groups") or [])
        rules = len(merged.get("rules") or [])
        print(f"[{'PASS' if ok else 'FAIL'}] {pid}  节点{len(raw.get('proxies') or []):>3}  组{groups}  规则{rules}  rc={proc.returncode}")
        if not ok:
            failures.append((pid, blob))

    if failures:
        print("\n===== 失败详情 =====")
        for pid, blob in failures:
            print(f"\n--- {pid} ---")
            print(blob[-3000:])
        return 1

    print("\n全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
