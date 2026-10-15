"""
==============================================================================
Mihomo-Party 客户端覆写合并链模拟与断言验证器 (merge_sim.py)
==============================================================================

【功能定位】
在完全不起本地内核的情况下，秒级模拟 Clash Party / Sparkle 的底层 app.asar
覆写合并算法（applyOverrides），对输出的 YAML 产物执行 8 项铁律断言检查。

【客户端合并核心机制 (app.asar 权威依据)】
1. ext: js -> runOverrideScript(profile, content):
   main(config) 函数执行，整对象替换。
2. ext: yaml -> deepMerge(profile, patch, isOverride=true):
   - key+: 数组追加到已有数组之后 (append)
   - +key: 数组前插到已有数组之前 (prepend)
   - key!: 对象整体覆盖
   - key: 默认整段替换
3. 顺序铁律:
   JS 覆写必须在 YAML 覆写之前执行！
   JS 负责将 config.rules 初始化为内网直连规则，YAML 随后通过 rules+: 追加全球分流规则。
   若顺序反转，YAML 追加的内容会被后执行的 JS 直接清空抹杀！
"""
import json
import os
import re
import sys

# 客户端配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
BASE = os.environ.get("MIHOMO_PARTY_BASE") or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "mihomo-party"
)



if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def load_override_yaml_list():
    """模拟订阅自带的原始规则（这里只需一个非空占位）。"""
    return ["GEOSITE,category-ads-all,广告拦截", "MATCH,DIRECT"]


def run_js(profile, js_text):
    """模拟 runOverrideScript：把 config 交给 main()，返回新对象。"""
    m = re.search(r"function\s+main\s*\(\s*config\s*\)", js_text)
    if not m:
        raise SystemExit("JS 里找不到 main(config)")
    # 提取 workRules 数组字面量
    wr = re.search(r"const\s+workRules\s*=\s*\[(.*?)\];", js_text, re.S)
    if not wr:
        raise SystemExit("JS 里找不到 workRules")
    rules = re.findall(r'"([^"]+)"', wr.group(1))
    return rules, js_text


def deep_merge_arrays(target_rules, patch_rules, key):
    if key.endswith("+"):
        return target_rules + patch_rules
    return patch_rules


def main():
    # 优先使用配置根下的覆写，若不存在则回退至本仓库产物 (优先 customSubBoost.full.yaml)
    repo_override = os.path.join(os.path.dirname(__file__), "..", "override")
    yml_candidates = [
        os.path.join(BASE, "override", "customSubBoost.full.yaml"),
        os.path.join(repo_override, "customSubBoost.full.yaml"),
        os.path.join(repo_override, "customSubBoost.standard.yaml"),
        os.path.join(repo_override, "customSubBoost.minimal.yaml"),
    ]
    yml_path = next((p for p in yml_candidates if os.path.exists(p)), None)
    if not yml_path:
        raise SystemExit("找不到 YAML 覆写文件 (customSubBoost.*.yaml)")
    yml = open(yml_path, encoding="utf-8").read()

    js_path = os.path.join(BASE, "override", "1a128f773c5.js")
    if os.path.exists(js_path):
        js = open(js_path, encoding="utf-8").read()
        work, _ = run_js(None, js)
    else:
        # 外部无前置私有 JS 时，优先使用本仓库新增的 1a_high_freq_direct.js 前置直连白名单
        local_direct_js = os.path.join(repo_override, "1a_high_freq_direct.js")
        if os.path.exists(local_direct_js):
            js_content = open(local_direct_js, encoding="utf-8").read()
            work = re.findall(r'"([^"]+)"', js_content)
            # 过滤出合法的规则项
            work = [r for r in work if r.startswith(("IP-CIDR,", "DOMAIN-SUFFIX,", "DOMAIN,"))]
            js = "const workRules = " + json.dumps(work) + "; config.rules = [...workRules];"
        else:
            work = [
                "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
                "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
                "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
                "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
            ]
            js = "const workRules = " + json.dumps(work) + "; config.rules = [...workRules];"


    # --- 阶段 0：订阅原始配置 ---
    rules = load_override_yaml_list()
    print(f"[0] 订阅原始规则        : {len(rules)} 条")

    # --- 阶段 1：JS 覆写（若存在前置 JS，注册表第 1 项）---
    if re.search(r"config\.rules\s*=\s*\[\.\.\.workRules\]", js):
        rules = list(work)
        print(f"[1] JS 覆写后           : {len(rules)} 条（仅 workRules）")
    else:
        raise SystemExit("JS 里的 config.rules 赋值形态与预期不符，需人工确认")

    # --- 阶段 2：YAML 覆写（customSubBoost / 1b0sb00st01, global, 注册表第 4 项）---
    m = re.search(r"^rules(\+?):\s*$", yml, re.M)
    if not m:
        raise SystemExit("YAML 里找不到 rules 或 rules+ 键")
    key = "rules" + m.group(1)
    body = yml[m.end():]
    patch = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("- "):
            patch.append(line[2:].strip())
        elif line.startswith("#") or not line:
            continue
        else:
            break
    rules = deep_merge_arrays(rules, patch, key)
    print(f"[2] YAML({key}) 合并后   : {len(rules)} 条")

    # --- 校验 ---
    ok = True

    def chk(cond, msg):
        nonlocal ok
        print(("  PASS  " if cond else "  FAIL  ") + msg)
        if not cond:
            ok = False

    print("\n--- 校验 ---")
    chk(len(rules) == len(work) + len(patch),
        f"规则总数 = JS({len(work)}) + YAML({len(patch)}) = {len(rules)}")
    chk(rules[:len(work)] == work, f"前 {len(work)} 条为前置直连规则（未被覆盖）")
    chk(rules[-1] == "MATCH,漏网之鱼", "最后一条是 MATCH 兜底")

    groups = set(re.findall(r"^  - name: \"(.+?)\"", yml, re.M))
    bad = []
    for r in rules[1:]:
        parts = r.split(",")
        tgt = parts[2] if len(parts) > 2 else ""
        if not tgt or tgt in ("no-resolve",):
            continue
        if tgt not in groups and tgt not in ("DIRECT", "REJECT", "COMPATIBLE"):
            bad.append((r, tgt))
    chk(not bad, f"所有规则的目标组都在 proxy-groups 中定义（异常 {len(bad)} 条）")
    for r, t in bad[:5]:
        print("        ", r, "->", t)

    prov = set(re.findall(r"^  ([A-Za-z0-9._@!+-]+):\s*$", yml[:yml.find("\nrules+:")], re.M))
    used = set()
    for r in rules:
        if r.startswith("RULE-SET,"):
            used.add(r.split(",")[1])
    miss = sorted(used - prov)
    chk(not miss, f"所有 RULE-SET 都已声明 rule-provider（缺失 {len(miss)}）")
    if miss:
        print("        ", miss)

    noproxy = []
    seg = yml[: yml.find("\nrules+:")]
    for p in sorted(used):
        i = seg.find(f"\n  {p}:")
        if i < 0:
            continue
        # 块范围：从该键到下一个「两个空格缩进的键」为止（缩进 4 空格的属性行不算）
        rest = seg[i + len(f"\n  {p}:") :]
        nxt = re.search(r"\n  \S", rest)
        blk = rest[: nxt.start()] if nxt else rest
        if "proxy:" not in blk:
            noproxy.append(p)
    chk(not noproxy, f"每个 provider 都带 proxy（缺失 {len(noproxy)}）")
    if noproxy:
        print("        ", noproxy)

    # Steam 商店必须早于 category-games-cn
    def idx(pred):
        for n, r in enumerate(rules):
            if pred(r):
                return n
        return -1

    i_store = idx(lambda r: r == "DOMAIN-SUFFIX,store.steampowered.com,Steam")
    i_cgcn = idx(lambda r: r == "RULE-SET,category-games-cn,国内服务")
    chk(0 <= i_store < i_cgcn,
        f"Steam 商店代理({i_store}) 早于 category-games-cn({i_cgcn})")
    i_steamcn = idx(lambda r: r == "RULE-SET,steam-cn,国内服务")
    i_steam = idx(lambda r: r == "RULE-SET,steam,Steam")
    chk(0 <= i_steamcn < i_steam,
        f"steam-cn 直连({i_steamcn}) 早于 steam 兜底({i_steam})")

    print("\n结果:", "全部通过" if ok else "存在失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
