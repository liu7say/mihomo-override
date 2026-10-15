"""启动内核，用真实订阅验证 6 个地区组的实际成员构成。

这是最终确认：filter / exclude-filter 在 mihomo 里真的按预期工作，
而不是只在 Python 正则层面看起来对。
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OVERRIDE_YAML = REPO_ROOT / "override" / "customSubBoost.yaml"
if not OVERRIDE_YAML.exists():
    OVERRIDE_YAML = REPO_ROOT / "override" / "1b0sb00st01.yaml"


# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
SB = ROOT / "test" / "_sb"
WORK = SB / "rgn"
CORE = ROOT / "test" / "mihomo-test.exe"
API = "http://127.0.0.1:19101"

SUBS = {
    "19f26ab99a3": "奈云",
    "1a0377776c2": "TAGMeta",
    "19e91d0a1b7": "Glados",
    "19db57e02f7": "狗子云",
}
REGIONS = ["美国节点", "香港节点", "日本节点", "狮城节点", "台湾节点", "韩国节点"]
# 明确属于其他地区的名字段，出现即判定为误伤
OTHER = (
    "Australia", "Russia", "Belarus", "Brazil", "United Kingdom", "London",
    "Germany", "France", "Canada", "Amsterdam", "Mumbai", "Thailand",
    "Malaysia", "Vietnam", "Indonesia", "Argentina", "Mexico", "Santiago",
)


def api(path, timeout=30):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    if not OVERRIDE_YAML.exists():
        sys.exit(f"【错误】找不到覆写文件: {OVERRIDE_YAML}")

    if not CORE.exists():
        print(f"[*] 未检测到测试内核: {CORE}，跳过动态实测。")
        return 0

    ov = yaml.safe_load(OVERRIDE_YAML.read_text(encoding="utf-8"))
    total_bad = 0
    total_empty = 0

    for pid, label in SUBS.items():
        profile_path = ROOT / "profiles" / f"{pid}.yaml"
        if not profile_path.exists():
            continue

        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        merged = dict(raw)
        merged.update({
            "proxy-groups": ov["proxy-groups"],
            "rules": ov.get("rules+") or ov.get("rules") or [],
            "rule-providers": ov["rule-providers"],
            "mode": "rule",

            "mixed-port": 17901,
            "external-controller": "127.0.0.1:19101",
            "log-level": "warning",
            "dns": {"enable": True, "nameserver": ["223.5.5.5", "119.29.29.29"]},
        })

        if WORK.exists():
            shutil.rmtree(WORK)
        WORK.mkdir(parents=True)
        for f in ("geoip.dat", "geosite.dat", "country.mmdb"):
            src = ROOT / "work" / pid / f
            if src.exists():
                shutil.copy2(src, WORK / f)

        cfg = WORK / "config.yaml"
        cfg.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=100000), encoding="utf-8")

        proc = subprocess.Popen(
            [str(CORE), "-d", str(WORK), "-f", str(cfg)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(50):
                try:
                    api("/version", timeout=4)
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(0.5)
            time.sleep(3)
            proxies = api("/proxies").get("proxies") or {}

            print(f"\n【{label} {pid}】{len(raw.get('proxies') or [])} 节点")
            for rn in REGIONS:
                g = proxies.get(rn)
                if not g:
                    print(f"  {rn:10s} !! 内核未识别")
                    total_empty += 1
                    continue
                members = g.get("all") or []
                bad = [m for m in members if any(o.lower() in m.lower() for o in OTHER)]
                if not members:
                    total_empty += 1
                if bad:
                    total_bad += len(bad)
                flag = ""
                if bad:
                    flag = f"  ✗ 误伤: {bad[:3]}"
                elif not members:
                    flag = "  （空组，该订阅无此地区节点）"
                print(f"  {rn:10s} type={g.get('type'):8s} 成员{len(members):>3}{flag}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("\n" + "=" * 60)
    print(f"误伤总数 {total_bad} | 空组 {total_empty}")
    print("=" * 60)
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
