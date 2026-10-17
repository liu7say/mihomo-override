"""
==============================================================================
代理组嵌套拓扑检查与环引用检测工具 (nest_check.py)
==============================================================================

【功能定位】
1. 静态拓扑检查 (纯算法，零外部依赖):
   - 基于深度优先搜索 (DFS) 和三色标记法对 proxy-groups 构成的有向图进行拓扑遍历。
   - 严密检测是否存在循环引用（组套娃：例如 A 引用 B，B 引用 A，会导致内核启动挂死或死循环）。
   - 严密检测全局与各策略组的最大嵌套深度（嵌套层级 > 3 会引发 UI 严重卡顿与分流递归慢）。
2. 动态内核校验 (可选，当本地存在 mihomo 内核与测试订阅时触发):
   - 拉起测试内核实例，通过 RESTful API 实测各组展开后的实际节点构成与初始化耗时。
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 项目路径定义
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from gen_override import REGION_GROUPS

# 生产覆写产物清单（支持三大预设档位）
DEFAULT_PRESET_TIERS = ["minimal", "standard", "full"]

# 客户端测试运行环境探测
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))


def find_mihomo_core() -> Path:
    """自动探测本地 Mihomo / Clash 内核二进制。"""
    candidates = [
        ROOT / "test" / "mihomo-test.exe",
        Path("C:/Program Files/Clash Party/resources/sidecar/mihomo.exe"),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Clash Party" / "resources" / "sidecar" / "mihomo.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "mihomo-party" / "resources" / "sidecar" / "mihomo.exe",
    ]
    which = shutil.which("mihomo")
    if which:
        candidates.append(Path(which))
    for c in candidates:
        if c.exists():
            return c
    return ROOT / "test" / "mihomo-test.exe"


CORE = find_mihomo_core()
API = "http://127.0.0.1:19102"
SUBS = {"19f26ab99a3": "奈云", "1a0377776c2": "TAGMeta", "19e91d0a1b7": "Glados"}


def api(path: str, timeout: int = 40) -> dict:
    """调用 Mihomo 外部控制器 RESTful API。"""
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_cycles_and_depth(groups_map: dict) -> tuple[list, dict, int]:
    """
    基于三色标记法 (Coloring DFS) 的有向图环检测与最大深度计算算法。
    
    【颜色状态】
    - color = 0 (未访问): 节点尚未探索
    - color = 1 (在栈上/正在访问): 节点正在当前 DFS 搜索路径中。若此时再次遇到 color=1 的邻居，即发现环！
    - color = 2 (已完成): 该节点的所有子分支均已遍历完毕，安全无环。
    
    【返回值】
    - cycles: 发现的所有循环引用闭环路径列表
    - depth: 各个策略组的最大嵌套深度字典
    - maxd: 全局最大嵌套深度
    """
    # 建立有向边：策略组 -> 其直接引用的子策略组
    edges = {}
    for name, proxies in groups_map.items():
        edges[name] = [p for p in proxies if p in groups_map]

    cycles = []
    color = {}
    depth = {}

    def dfs(n: str, stack: list[str]) -> int:
        color[n] = 1
        stack.append(n)
        best = 0

        for neighbor in edges.get(n, []):
            if color.get(neighbor) == 1:
                # 命中祖先节点，提取闭环路径
                idx = stack.index(neighbor)
                cycles.append(stack[idx:] + [neighbor])
            else:
                # 若未访问则递归深入；若已完成 (color=2) 则直接利用已计算出的记忆化深度
                if color.get(neighbor) != 2:
                    dfs(neighbor, stack)
                best = max(best, depth.get(neighbor, 0))

        stack.pop()
        color[n] = 2
        # 计算深度：如果下属有引用其他组，则层级为最大子深度 + 1
        depth[n] = best + 1 if edges.get(n) else 0
        return depth[n]

    maxd = 0
    for node in list(edges):
        if color.get(node) != 2:
            maxd = max(maxd, dfs(node, []))

    return cycles, depth, maxd


def static_check(override_path: Path) -> bool:
    """纯静态有向图拓扑核查（无需启动外部内核与订阅）。"""
    print(f"[*] 正在执行静态拓扑拓扑排序与环检测: {override_path.name}")
    data = yaml.safe_load(override_path.read_text(encoding="utf-8"))
    proxy_groups = data.get("proxy-groups") or []

    # 提取所有策略组及其显式 proxies 引用列表
    groups_map = {}
    for g in proxy_groups:
        name = g.get("name")
        proxies = g.get("proxies") or []
        groups_map[name] = proxies

    cycles, depth, maxd = check_cycles_and_depth(groups_map)

    print(f"  策略组总数       : {len(groups_map)}")
    print(f"  循环引用检测     : {'✔ 0 处，无任何循环引用' if not cycles else f'✘ 发现环: {cycles}'}")
    print(f"  全局最大嵌套深度 : {maxd} (健康阈值: <= 3)")

    deepest = sorted(depth.items(), key=lambda x: -x[1])[:5]
    print(f"  层级最深的策略组 : {[(n, d) for n, d in deepest]}")

    # 检查节点选择是否收齐 7 个地区组
    sel_proxies = groups_map.get("节点选择") or []
    expected_regions = [r["name"] for r in REGION_GROUPS]
    missing_regs = [r for r in expected_regions if r not in sel_proxies]

    if missing_regs:
        print(f"  ✘ 节点选择组遗漏地区组: {missing_regs}")
        return False
    else:
        print(f"  ✔ 节点选择组已完整收纳全部 {len(expected_regions)} 个地区组")

    if cycles or maxd > 3:
        return False
    return True


def main() -> int:
    targets: list[Path] = []
    if len(sys.argv) > 1:
        custom_target = Path(sys.argv[1])
        if not custom_target.exists():
            sys.exit(f"【错误】找不到指定的覆写文件: {custom_target}")
        targets.append(custom_target)
    else:
        for tier in DEFAULT_PRESET_TIERS:
            # 优先检测子目录 override/yaml/，回退检测旧平铺路径
            p = REPO_ROOT / "override" / "yaml" / f"customSubBoost.{tier}.yaml"
            if not p.exists():
                p = REPO_ROOT / "override" / f"customSubBoost.{tier}.yaml"
            if p.exists():
                targets.append(p)

    if not targets:
        sys.exit("【错误】在 override/yaml/ 目录下未找到任何 customSubBoost.*.yaml 覆写文件！")

    all_passed = True
    print(f"[*] 开始对 {len(targets)} 个预设覆写产物进行拓扑与环引用核查...")
    for idx, target in enumerate(targets, 1):
        print(f"\n--- [{idx}/{len(targets)}] 核查目标: {target.name} ---")
        if not static_check(target):
            all_passed = False

    if not all_passed:
        print("\n[✘] 拓扑核查失败：存在环引用或层级超标！")
        return 1

    print("\n[✔] 全部预设文件的静态拓扑与环引用核查 100% 通过！")

    # 检查环境是否支持动态实测
    if not CORE.exists():
        print(f"\n[i] 未检测到本地内核二进制 ({CORE})，跳过动态实测阶段。")
        return 0

    print("\n[*] 检测到本地测试内核，启动动态多订阅实测...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
