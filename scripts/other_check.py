"""验证「其他国家」组的实际成员构成。

这个组是对官方 other 预设的反向实现（exclude 掉全部已知地区），
必须实测：既不能漏（该进去的没进去），也不能串（不该进去的混进来）。
"""

import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import yaml

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
SB = ROOT / "test" / "_sb"
WORK = SB / "oth"
CORE = ROOT / "test" / "mihomo-test.exe"
API = "http://127.0.0.1:19103"

SUBS = {"19f26ab99a3": "奈云", "1a0377776c2": "TAGMeta", "19e91d0a1b7": "Glados",
        "19db57e02f7": "狗子云"}
REGIONS = ["美国节点", "香港节点", "日本节点", "狮城节点", "台湾节点", "韩国节点", "其他国家"]


def api(path, timeout=40):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    ov = yaml.safe_load((SB / "subboost-override.yaml").read_text(encoding="utf-8"))
    problems = 0

    for pid, label in SUBS.items():
        raw = yaml.safe_load((ROOT / "profiles" / f"{pid}.yaml").read_text(encoding="utf-8"))
        merged = dict(raw)
        merged.update({
            "proxy-groups": ov["proxy-groups"],
            "rules": ov["rules"],
            "rule-providers": ov["rule-providers"],
            "mode": "rule",
            "mixed-port": 17903,
            "external-controller": "127.0.0.1:19103",
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
                    time.sleep(0.4)
            time.sleep(3)
            proxies = api("/proxies").get("proxies") or {}

            print(f"\n【{label} {pid}】{len(raw.get('proxies') or [])} 节点")
            groups = {}
            for r in REGIONS:
                g = proxies.get(r) or {}
                members = g.get("all") or []
                # COMPATIBLE 是 mihomo 给空 url-test 组填充的内建占位符，
                # 不是真实节点，必须在重叠检查前就剔除。
                groups[r] = {m for m in members if m != "COMPATIBLE"}
                empty_note = "（空组）" if not groups[r] else ""
                print(f"  {r:10s} 成员{len(groups[r]):>3}  {list(groups[r])[:3]}{empty_note}")

            # 1. 地区组之间不应重叠
            print("  ── 组间重叠检查 ──")
            overlap_total = 0
            for i, a in enumerate(REGIONS):
                for b in REGIONS[i + 1:]:
                    inter = groups[a] & groups[b]
                    if inter:
                        overlap_total += len(inter)
                        print(f"  ✗ {a} ∩ {b} = {list(inter)[:3]}")
            print(f"  重叠总数 {overlap_total}")

            # 2. 覆盖完整性：7 个组的并集应等于全部真实节点
            real_nodes = {p["name"] for p in (raw.get("proxies") or [])}
            import re
            JUNK = re.compile(
                r"^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\s*[:：]"
                r"|^(余额|会员)\s*\||版本太旧|请更新|更新软件|去官网更新"
            )
            clean = {n for n in real_nodes if not JUNK.search(n)}
            union = set().union(*groups.values())
            missing = clean - union
            print(f"  ── 覆盖检查 ──")
            print(f"  真实节点(去信息节点) {len(clean)} | 7组并集 {len(union)} | 未被任何组覆盖 {len(missing)}")
            if missing:
                print(f"  ✗ 漏掉: {list(missing)[:8]}")
                problems += len(missing)

            problems += overlap_total
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("\n" + "=" * 60)
    print("7 个地区组无重叠、无遗漏" if not problems else f"存在问题 {problems} 处")
    print("=" * 60)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
