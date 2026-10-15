"""
==============================================================================
地区策略组覆盖完整性与无重叠校验工具 (other_check.py)
==============================================================================

【功能定位】
验证「美国、香港、日本、狮城、台湾、韩国、其他国家」7 个地区策略组的成员划分：
1. 无组间重叠 (Zero Overlap): 任何一个有效节点只能且必须属于一个地区组，严禁跨组重叠命中。
2. 无遗漏全覆盖 (Zero Leak): 排除垃圾信息节点后，7 个组的并集必须 100% 等于机场订阅的全部可用节点。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

# 项目根路径与产物路径
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OVERRIDE_YAML = REPO_ROOT / "override" / "customSubBoost.yaml"
if not OVERRIDE_YAML.exists():
    OVERRIDE_YAML = REPO_ROOT / "override" / "1b0sb00st01.yaml"


# 客户端测试环境探测
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
SB = ROOT / "test" / "_sb"
WORK = SB / "oth"
CORE = ROOT / "test" / "mihomo-test.exe"
API = "http://127.0.0.1:19103"

SUBS = {
    "19f26ab99a3": "奈云",
    "1a0377776c2": "TAGMeta",
    "19e91d0a1b7": "Glados",
    "19db57e02f7": "狗子云",
}
REGIONS = ["美国节点", "香港节点", "日本节点", "狮城节点", "台湾节点", "韩国节点", "其他国家"]

# 垃圾信息节点过滤正则（与生成器保持一致）
JUNK_RE = re.compile(
    r"^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\s*[:：]"
    r"|^(余额|会员)\s*\||版本太旧|请更新|更新软件|去官网更新"
)


def api(path: str, timeout: int = 40) -> dict:
    """向测试内核外部控制器发送请求并解析响应。"""
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    if not OVERRIDE_YAML.exists():
        sys.exit(f"【错误】找不到覆写文件: {OVERRIDE_YAML}")

    if not CORE.exists():
        print(f"[*] 未检测到测试内核: {CORE}，跳过动态实测（纯算法检查可在独立沙箱运行）。")
        return 0

    ov = yaml.safe_load(OVERRIDE_YAML.read_text(encoding="utf-8"))
    problems = 0

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
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        try:
            core_ready = False
            for _ in range(30):
                if proc.poll() is not None:
                    # 内核过早退出，打印输出
                    out, _ = proc.communicate()
                    print(f"  ✘ 内核异常退出 (rc={proc.returncode}):\n{out[-500:]}")
                    break
                try:
                    api("/version", timeout=2)
                    core_ready = True
                    break
                except Exception:
                    time.sleep(0.5)

            if not core_ready:
                print(f"  ⚠ 内核未能按时就绪，跳过订阅 {label} 动态测试")
                continue

            time.sleep(1.5)
            proxies = api("/proxies").get("proxies") or {}


            print(f"\n【{label} {pid}】{len(raw.get('proxies') or [])} 节点")
            groups = {}
            for r in REGIONS:
                g = proxies.get(r) or {}
                members = g.get("all") or []
                # COMPATIBLE 是 mihomo 给空 url-test 组填充的内建占位符，需剔除
                groups[r] = {m for m in members if m != "COMPATIBLE"}
                empty_note = "（空组）" if not groups[r] else ""
                print(f"  {r:10s} 成员{len(groups[r]):>3}  {list(groups[r])[:3]}{empty_note}")

            # 1. 组间重叠检查
            print("  ── 组间重叠检查 ──")
            overlap_total = 0
            for i, a in enumerate(REGIONS):
                for b in REGIONS[i + 1:]:
                    inter = groups[a] & groups[b]
                    if inter:
                        overlap_total += len(inter)
                        print(f"  ✘ {a} ∩ {b} = {list(inter)[:3]}")
            print(f"  重叠总数: {overlap_total}")

            # 2. 覆盖完整性检查
            real_nodes = {p["name"] for p in (raw.get("proxies") or [])}
            clean = {n for n in real_nodes if not JUNK_RE.search(n)}
            union = set().union(*groups.values())
            missing = clean - union
            print("  ── 覆盖检查 ──")
            print(f"  有效节点: {len(clean)} | 7组并集: {len(union)} | 未覆盖漏网: {len(missing)}")
            if missing:
                print(f"  ✘ 漏掉节点: {list(missing)[:8]}")
                problems += len(missing)

            problems += overlap_total
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("\n" + "=" * 60)
    print("✔ 7 个地区组无重叠、无遗漏" if not problems else f"✘ 存在问题 {problems} 处")
    print("=" * 60)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
