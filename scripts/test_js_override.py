"""
==============================================================================
全合一 JS 覆写运行时自动化测试套件 (test_js_override.py)
==============================================================================

【功能定位】
利用 Node.js 真实运行环境，对 override/ 目录下的三大预设档位
(minimal / standard / full) 执行全方位运行时行为仿真：
1. 节点清洗引擎：验证垃圾节点过滤与高倍率识别（排除 -X2 线路误伤）；
2. 策略组级联清洗：验证策略组中的已剔除节点是否被彻底移除（零死链引用）；
3. 全局 DNS 与 Fake-IP：验证 Fake-IP 绕过规则与工作内网专有 DNS 策略合并；
4. 规则链拓扑保序：验证局域网直连、工作内网直连、游戏直连/代理与 MATCH 兜底；
5. 空安全防御：验证在空配置或异常字段输入时稳定运行、永不抛出未捕获异常；
6. 规则集拉取通道与动态 CDN 声明：验证默认 DIRECT 与运行时动态切换。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# 确保在 Windows 控制台环境下输出 UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# 导入生成器中定义的连通性探测常量 (Single Source of Truth)
sys.path.insert(0, str(REPO_ROOT))
from scripts.gen_override import CAPTIVE_PORTAL_DOMAINS, CAPTIVE_PORTAL_RULES


def run_node_test(test_script: str) -> dict:
    """在 Node.js 中执行测试脚本并返回 JSON 解析结果。"""
    proc = subprocess.run(
        ["node", "-e", test_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print("[-] Node.js 执行报错:\n", proc.stderr)
        raise RuntimeError(f"Node.js 测试执行失败，退出码: {proc.returncode}")
    return json.loads(proc.stdout)


def test_tier(tier: str, exp_groups: int, exp_providers: int) -> None:
    # 优先检测带有本地私有配置的自用脚本，若不存在则回退检测公开脱敏示例模板
    js_path = REPO_ROOT / "override" / "js" / f"customSubBoost.{tier}.js"
    if not js_path.exists():
        js_path = REPO_ROOT / "override" / "example" / f"customSubBoost.{tier}.example.js"
    if not js_path.exists():
        # 兼容旧平铺路径
        js_path = REPO_ROOT / "override" / f"customSubBoost.{tier}.js"
    if not js_path.exists():
        sys.exit(f"【致命错误】找不到 JS 覆写文件: {js_path}")

    js_rel = os.path.relpath(js_path, REPO_ROOT).replace("\\", "/")

    test_driver = f"""
    const {{ main, CONFIG }} = require('./{js_rel}');

    // 1. 构建模拟订阅输入
    const mockInput = {{
      proxies: [
        {{ name: "🇺🇸 美国 01", type: "ss", server: "1.1.1.1", port: 443 }},
        {{ name: "🇭🇰 香港 02 | 1x", type: "ss", server: "1.1.1.2", port: 443 }},
        {{ name: "🇯🇵 日本 IEPL-X2", type: "ss", server: "1.1.1.3", port: 443 }}, // 线路代号，必须保留
        {{ name: "🇯🇵 日本 IEPL X2", type: "ss", server: "1.1.1.7", port: 443 }},  // 空格线路代号，严禁误杀
        {{ name: "🇺🇸 美国 Server X1", type: "ss", server: "1.1.1.8", port: 443 }}, // 服务器代号，严禁误杀
        {{ name: "🇭🇰 香港 01 - 流量: 50G", type: "ss", server: "1.1.1.9", port: 443 }}, // 流量额度非倍率，严禁误杀
        {{ name: "🇸🇬 狮城 04 [2x]", type: "ss", server: "1.1.1.4", port: 443 }},  // 2倍率，必须剔除
        {{ name: "🇭🇰 香港 03 [x2]", type: "ss", server: "1.1.1.10", port: 443 }}, // 前置x倍率，必须剔除
        {{ name: "到期时间: 2026-12-31", type: "ss", server: "1.1.1.5", port: 443 }}, // 垃圾节点，必须剔除
        {{ name: "剩余流量: 500G", type: "ss", server: "1.1.1.6", port: 443 }},       // 垃圾节点，必须剔除
        {{ name: "🇭🇰 香港 [官网专线]", type: "ss", server: "1.1.1.11", port: 443 }}, // 包含官网字样但为正常节点，严禁误杀
        {{ name: "🇸🇬 优质套餐专线", type: "ss", server: "1.1.1.12", port: 443 }}, // 包含套餐字样但为正常节点，严禁误杀
        {{ name: "🇯🇵 备用线路", type: "ss", server: "1.1.1.13", port: 443 }},     // 正常节点，严禁误杀
        {{ name: "官网: https://sub.com", type: "ss", server: "1.1.1.14", port: 443 }}, // 纯信息节点，必须剔除
        {{ name: "剩余流量: 50G", type: "ss", server: "1.1.1.15", port: 443 }},       // 纯信息节点，必须剔除
        {{ name: "到期: 2026-12-31", type: "ss", server: "1.1.1.16", port: 443 }},   // 纯信息节点，必须剔除
        {{ name: "到期：2026-12-31", type: "ss", server: "1.1.1.17", port: 443 }},   // 中文冒号信息节点，必须剔除
        {{ name: "套餐: 500G", type: "ss", server: "1.1.1.18", port: 443 }},         // 套餐信息节点，必须剔除
        {{ name: "套餐：年付VIP", type: "ss", server: "1.1.1.19", port: 443 }},      // 套餐中文冒号节点，必须剔除
        {{ name: "过期: 2026-12-31", type: "ss", server: "1.1.1.20", port: 443 }},   // 过期信息节点，必须剔除
      ],
      "proxy-groups": [
        {{
          name: "自定义测试组",
          type: "select",
          proxies: ["🇺🇸 美国 01", "🇸🇬 狮城 04 [2x]", "剩余流量: 500G"]
        }}
      ],
      rules: [
        "DOMAIN-SUFFIX,raw-subscription.com,DIRECT"
      ],
      dns: {{
        enable: true,
        nameserver: ["1.1.1.1"]
      }}
    }};

    // 2. 模拟配置个性化工作地址 (含 IPv4 与 IPv6 私有网段)
    CONFIG.cleanTrashNodes = true;
    CONFIG.cleanHighMultiplier = true;
    CONFIG.maxMultiplier = 1.0;
    CONFIG.enableWorkRules = true;
    CONFIG.workDomains = ["oa.corp.com", "+.corp.internal"];
    CONFIG.workIpCidrs = ["10.20.0.0/16", "fd00::/8"];
    CONFIG.workProcesses = ["corp-vpn.exe"];
    CONFIG.workNameserverPolicy = {{
      "+.corp.internal": "10.0.0.53"
    }};

    // 3. 执行覆写
    const output = main(JSON.parse(JSON.stringify(mockInput)));

    // 4. 空安全测试
    const emptyOutput = main({{}});
    const nullOutput = main(null);

    // 5. 组装测试报告数据
    const remainingProxies = output.proxies.map(p => p.name);
    const groupsCount = output["proxy-groups"].length;
    const testGroup = output["proxy-groups"].find(g => g.name === "自定义测试组");
    const testGroupProxies = testGroup ? testGroup.proxies : [];
    const providersCount = Object.keys(output["rule-providers"]).length;
    const sampleProvider = output["rule-providers"]["cn"] || {{}};

    // 动态切换 proxy 验证
    CONFIG.ruleProviderProxy = "节点选择";
    const switchedProxyOutput = main(JSON.parse(JSON.stringify(mockInput)));
    const switchedSampleProxy = switchedProxyOutput["rule-providers"]["cn"] ? switchedProxyOutput["rule-providers"]["cn"].proxy : "";

    // 动态切换 CDN 验证
    CONFIG.ruleProviderCdn = "gcore";
    const switchedCdnOutput = main(JSON.parse(JSON.stringify(mockInput)));
    const switchedSampleUrl = switchedCdnOutput["rule-providers"]["cn"] ? switchedCdnOutput["rule-providers"]["cn"].url : "";
    const switchedSampleIcon = switchedCdnOutput["proxy-groups"][0] ? switchedCdnOutput["proxy-groups"][0].icon : "";

    console.log(JSON.stringify({{
      remainingProxies: remainingProxies,
      groupsCount: groupsCount,
      testGroupProxies: testGroupProxies,
      providersCount: providersCount,
      defaultProviderProxy: sampleProvider.proxy,
      defaultProviderUrl: sampleProvider.url,
      switchedSampleProxy: switchedSampleProxy,
      switchedSampleUrl: switchedSampleUrl,
      switchedSampleIcon: switchedSampleIcon,
      hasDns: !!output.dns,
      dnsFakeIpFilters: output.dns ? output.dns["fake-ip-filter"] : [],
      dnsPolicy: output.dns ? output.dns["nameserver-policy"] : {{}},
      proxyServerNameserver: output.dns ? output.dns["proxy-server-nameserver"] : [],
      rulesCount: output.rules.length,
      rulesTop: output.rules.slice(0, 20),
      rulesBottom: output.rules.slice(-3),
      emptySafe: Array.isArray(emptyOutput["proxy-groups"]) && Array.isArray(nullOutput.rules),
      groupNames: output["proxy-groups"].map(g => g.name),
      providerKeys: Object.keys(output["rule-providers"]),
      allRules: output.rules,
    }}));
    """

    res = run_node_test(test_driver)
    remaining = res["remainingProxies"]

    # 断言 1: 垃圾与信息节点过滤（冒号/到期/流量）
    assert "到期时间: 2026-12-31" not in remaining, f"✘ [{tier}] 垃圾公告节点未被过滤！"
    assert "剩余流量: 500G" not in remaining, f"✘ [{tier}] 剩余流量信息节点未被过滤！"
    assert "官网: https://sub.com" not in remaining, f"✘ [{tier}] 官网信息节点未被过滤！"
    assert "剩余流量: 50G" not in remaining, f"✘ [{tier}] 剩余流量信息节点未被过滤！"
    assert "到期: 2026-12-31" not in remaining, f"✘ [{tier}] '到期: 2026-12-31' 信息节点未被过滤！"
    assert "到期：2026-12-31" not in remaining, f"✘ [{tier}] '到期：2026-12-31' 信息节点未被过滤！"
    assert "套餐: 500G" not in remaining, f"✘ [{tier}] '套餐: 500G' 信息节点未被过滤！"
    assert "套餐：年付VIP" not in remaining, f"✘ [{tier}] '套餐：年付VIP' 信息节点未被过滤！"
    assert "过期: 2026-12-31" not in remaining, f"✘ [{tier}] '过期: 2026-12-31' 信息节点未被过滤！"

    # 断言 2: 倍率过滤与精准不误杀
    assert "🇸🇬 狮城 04 [2x]" not in remaining, f"✘ [{tier}] 2x 高倍率节点未被过滤！"
    assert "🇭🇰 香港 03 [x2]" not in remaining, f"✘ [{tier}] [x2] 高倍率节点未被过滤！"
    assert "🇺🇸 美国 01" in remaining, f"✘ [{tier}] 普通节点误伤！"
    assert "🇯🇵 日本 IEPL-X2" in remaining, f"✘ [{tier}] IEPL-X2 线路代号被误伤过滤！"
    assert "🇯🇵 日本 IEPL X2" in remaining, f"✘ [{tier}] IEPL X2 空格线路代号被误杀！"
    assert "🇺🇸 美国 Server X1" in remaining, f"✘ [{tier}] Server X1 服务器代号被误杀！"
    assert "🇭🇰 香港 01 - 流量: 50G" in remaining, f"✘ [{tier}] '流量: 50G' 流量额度被误杀为50倍率！"
    assert "🇭🇰 香港 [官网专线]" in remaining, f"✘ [{tier}] '[官网专线]' 正常节点被误杀！"
    assert "🇸🇬 优质套餐专线" in remaining, f"✘ [{tier}] '优质套餐专线' 正常节点被误杀！"
    assert "🇯🇵 备用线路" in remaining, f"✘ [{tier}] '备用线路' 正常节点被误杀！"

    # 断言 3: 策略组数量核验
    assert res["groupsCount"] == exp_groups, f"✘ [{tier}] 策略组数量预期 {exp_groups}，实测 {res['groupsCount']}"

    # 断言 4: 规则集数量核验
    assert res["providersCount"] == exp_providers, f"✘ [{tier}] 规则集数量预期 {exp_providers}，实测 {res['providersCount']}"

    # 断言 5: 级联清理无死链与节点池清洗纯净度
    test_group_proxies = res["testGroupProxies"]
    assert "🇸🇬 狮城 04 [2x]" not in test_group_proxies, f"✘ [{tier}] 策略组中残留已剔除的高倍率节点！"
    assert "剩余流量: 500G" not in test_group_proxies, f"✘ [{tier}] 策略组中残留已剔除的垃圾节点！"
    assert "到期: 2026-12-31" not in remaining
    assert "到期时间: 2026-12-31" not in remaining
    assert "剩余流量: 500G" not in remaining
    assert "官网: https://sub.com" not in remaining
    assert "剩余流量: 50G" not in remaining
    assert "🇸🇬 狮城 04 [2x]" not in remaining

    # 断言 6: DNS 与 Fake-IP 白名单（含连通性探测放行与 Google 排除）
    fake_filters = res["dnsFakeIpFilters"]
    assert "+.corp.internal" in fake_filters, f"✘ [{tier}] 工作域名未自动并入 Fake-IP 放行列表！"
    assert res["dnsPolicy"].get("+.corp.internal") == "10.0.0.53", f"✘ [{tier}] 工作内网专有 DNS 策略未正确注入！"
    for pd in CAPTIVE_PORTAL_DOMAINS:
        assert pd in fake_filters, f"✘ [{tier}] 连通性探测域名 {pd} 未在 Fake-IP 放行列表中！"
    assert not any("connectivitycheck.gstatic.com" in f for f in fake_filters), f"✘ [{tier}] Google gstatic 域名未被排除在 Fake-IP 绕过列表外！"
    assert not any("connectivitycheck.gstatic.com" in k for k in res["dnsPolicy"].keys()), f"✘ [{tier}] Google gstatic 域名未被排除在 nameserver-policy 外！"
    assert "https://223.5.5.5/dns-query" in res["proxyServerNameserver"], f"✘ [{tier}] proxy-server-nameserver 缺少 DoH https://223.5.5.5/dns-query！"

    # 断言 7: 规则链保序与连通性探测直连 (First-Match-Win)
    rules_top = res["rulesTop"]
    rules_bottom = res["rulesBottom"]
    for r in CAPTIVE_PORTAL_RULES:
        assert r in rules_top, f"✘ [{tier}] 缺少连通性直连规则: {r}！"
    assert not any("connectivitycheck.gstatic.com" in r for r in res["allRules"]), f"✘ [{tier}] Google gstatic 连通性探测域名未被排除在直连规则外！"
    assert any("10.0.0.0/8" in r and "no-resolve" in r for r in rules_top), f"✘ [{tier}] 规则链最前端缺少带 no-resolve 的局域网私网直连！"
    assert any("IP-CIDR,10.20.0.0/16,DIRECT,no-resolve" == r for r in rules_top), f"✘ [{tier}] IPv4 工作内网网段缺少 no-resolve 或格式错误！"
    assert any("IP-CIDR6,fd00::/8,DIRECT,no-resolve" == r for r in rules_top), f"✘ [{tier}] IPv6 工作内网网段缺少 IP-CIDR6 识别或 no-resolve！"
    assert any("corp.internal" in r for r in rules_top), f"✘ [{tier}] 规则链缺少前置工作域名直连！"
    assert any("corp-vpn.exe" in r for r in rules_top), f"✘ [{tier}] 规则链缺少前置工作进程直连！"
    assert rules_bottom[-1].startswith("MATCH,"), f"✘ [{tier}] 规则链末尾不是 MATCH 兜底！"

    # 断言 8: 空安全检查
    assert res["emptySafe"] is True, f"✘ [{tier}] 空配置防御失败！"

    # 断言 9: 规则集拉取通道与动态 CDN
    assert res["defaultProviderProxy"] == "DIRECT", f"✘ [{tier}] 默认规则集拉取通道应为 DIRECT，实测 {res['defaultProviderProxy']}"
    assert "fastly.jsdelivr.net" in res["defaultProviderUrl"], f"✘ [{tier}] 默认规则集 CDN 应为 fastly.jsdelivr.net，实测 {res['defaultProviderUrl']}"
    assert res["switchedSampleProxy"] == "节点选择", f"✘ [{tier}] 动态切换 ruleProviderProxy 为 '节点选择' 失败！实测 {res['switchedSampleProxy']}"
    assert "gcore.jsdelivr.net" in res["switchedSampleUrl"], f"✘ [{tier}] 动态切换 ruleProviderCdn 为 'gcore' 失败！实测 {res['switchedSampleUrl']}"
    assert "gcore.jsdelivr.net" in res["switchedSampleIcon"], f"✘ [{tier}] 动态切换 CDN 后策略组图标 URL 未同步更新！实测 {res['switchedSampleIcon']}"

    # 断言 10: 规则链引用完整性 (Referential Integrity Check)
    group_names = set(res["groupNames"]) | {"DIRECT", "REJECT", "COMPATIBLE", "PASS"}
    provider_keys = set(res["providerKeys"])
    for r in res["allRules"]:
        parts = r.split(",")
        if parts[0] == "RULE-SET":
            assert parts[1] in provider_keys, f"✘ [{tier}] 规则引用的 RULE-SET '{parts[1]}' 未在 rule-providers 中声明！"
        if len(parts) >= 3 and parts[2] not in ("no-resolve",):
            tgt = parts[2]
            assert tgt in group_names, f"✘ [{tier}] 规则 '{r}' 的目标策略组 '{tgt}' 未在 proxy-groups 中声明！"

    print(f"  [✔] {tier.upper()} 档位 10 项断言全部通过 (策略组 {res['groupsCount']} 组, 规则集 {res['providersCount']} 个, 规则链 {res['rulesCount']} 条)")


def main() -> int:
    print("[*] 正在启动 Node.js 进行全部 3 个档位运行时全量断言核查...")
    tiers = [
        ("minimal", 16, 12),
        ("standard", 23, 24),
        ("full", 41, 94),
    ]
    for tier, exp_g, exp_p in tiers:
        test_tier(tier, exp_g, exp_p)

    print("\n============================================================")
    print("✔ 全部 3 个预设档位 (minimal / standard / full) 运行时测试全部 100% 通过！")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
