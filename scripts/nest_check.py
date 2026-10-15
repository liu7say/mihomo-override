"""验证两处改动没有引入组套娃（循环引用 / 过深嵌套 / 解析变慢）。

背景：SubBoost v2.5.1 修过两个相关 bug ——
  1. 「新建自定义代理组时默认成员过宽，避免默认生成出节点选择和自定义组互相引用的循环配置」
  2. 「节点选择默认不再自动包含自定义代理组，减少代理组套娃导致配置异常或预览卡顿的风险」
所以「节点选择里包含地区组」这个改动必须实测，不能只看语法过不过。
"""

import json
import sys
import shutil
import subprocess
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from gen_override import REGION_GROUPS  # noqa: E402  完整地区组清单（6 国 + 其他国家）

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))
SB = ROOT / "test" / "_sb"
WORK = SB / "nest"
CORE = ROOT / "test" / "mihomo-test.exe"
API = "http://127.0.0.1:19102"

SUBS = {"19f26ab99a3": "奈云", "1a0377776c2": "TAGMeta", "19e91d0a1b7": "Glados"}


def api(path, timeout=40):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_cycles_and_depth(groups: dict) -> tuple[list, dict, int]:
    """返回 (循环引用列表, 各组最大嵌套深度, 全局最大深度)。"""
    edges = {name: [m for m in (g.get("all") or []) if m in groups] for name, g in groups.items()}

    cycles = []
    color = {}          # 0=未访问 1=在栈上 2=已完成
    depth = {}

    def dfs(n, stack):
        color[n] = 1
        stack.append(n)
        best = 0
        for m in edges.get(n, []):
            if color.get(m) == 1:
                idx = stack.index(m)
                cycles.append(stack[idx:] + [m])
            elif color.get(m) != 2:
                d = dfs(m, stack)
                best = max(best, d)
        stack.pop()
        color[n] = 2
        # +1 是 url-test 组不计层（它不再往下引用组）
        depth[n] = best + 1 if edges.get(n) else 0
        return depth[n]

    maxd = 0
    for n in list(edges):
        if color.get(n) != 2:
            maxd = max(maxd, dfs(n, []))

    return cycles, depth, maxd


def main() -> int:
    ov = yaml.safe_load((SB / "subboost-override.yaml").read_text(encoding="utf-8"))
    ok = True

    for pid, label in SUBS.items():
        raw = yaml.safe_load((ROOT / "profiles" / f"{pid}.yaml").read_text(encoding="utf-8"))
        merged = dict(raw)
        merged.update({
            "proxy-groups": ov["proxy-groups"],
            "rules": ov["rules"],
            "rule-providers": ov["rule-providers"],
            "mode": "rule",
            "mixed-port": 17902,
            "external-controller": "127.0.0.1:19102",
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

        t0 = time.time()
        proc = subprocess.Popen(
            [str(CORE), "-d", str(WORK), "-f", str(cfg)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        log = []
        init_ms = None
        try:
            # 读内核启动日志，抓 Initial configuration complete 耗时
            deadline = time.time() + 120
            while time.time() < deadline:
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    continue
                log.append(line.rstrip())
                if "Initial configuration complete" in line:
                    init_ms = time.time() - t0
                    break
            for _ in range(50):
                try:
                    api("/version", timeout=4)
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(0.4)
            time.sleep(2)

            proxies = api("/proxies").get("proxies") or {}
            groups = {k: v for k, v in proxies.items() if v.get("all") is not None}
            cycles, depth, maxd = check_cycles_and_depth(groups)

            # 节点选择实际成员
            sel = groups.get("节点选择", {})
            sel_members = sel.get("all") or []
            regions = [r["name"] for r in REGION_GROUPS]
            in_sel = [r for r in regions if r in sel_members]

            print(f"\n【{label} {pid}】{len(raw.get('proxies') or [])} 节点 / {len(groups)} 组")
            print(f"  内核初始化耗时     {init_ms:.2f}s" if init_ms else "  内核初始化耗时     (未捕获)")
            print(f"  循环引用           {len(cycles)} 处 {cycles[:2] if cycles else '✓'}")
            print(f"  最大嵌套深度       {maxd}")
            print(f"  节点选择成员数     {len(sel_members)}")
            print(f"  节点选择含地区组   {len(in_sel)}/{len(REGION_GROUPS)} {in_sel if in_sel else ''}")
            deepest = sorted(depth.items(), key=lambda x: -x[1])[:4]
            print(f"  最深的几个组       {[(n, d) for n, d in deepest]}")

            if cycles:
                ok = False
            if maxd > 3:
                print("  ⚠ 嵌套过深")
                ok = False
            if len(in_sel) != len(REGION_GROUPS):
                print("  ✗ 节点选择未完整包含全部地区组")
                ok = False
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            (SB / "nest.log").write_text("\n".join(log), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"无循环引用、嵌套深度正常、节点选择已含全部 {len(REGION_GROUPS)} 个地区组" if ok else "存在问题，见上")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
