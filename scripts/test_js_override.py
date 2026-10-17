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
        {{ name: "🇸🇬 狮城 01 优质专线", type: "ss", server: "1.1.1.21", port: 443 }}, // 狮城正常节点
        {{ name: "🇹🇼 台湾 01 优质专线", type: "ss", server: "1.1.1.22", port: 443 }}, // 台湾正常节点
        {{ name: "🇰🇷 韩国 01 优质专线", type: "ss", server: "1.1.1.23", port: 443 }}, // 韩国正常节点
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
    const allGroupProxies = output["proxy-groups"].flatMap(g => Array.isArray(g.proxies) ? g.proxies : []);
    const leakedProxiesInGroups = allGroupProxies.filter(name => [
      "🇸🇬 狮城 04 [2x]",
      "🇭🇰 香港 03 [x2]",
      "剩余流量: 500G",
      "到期时间: 2026-12-31",
      "官网: https://sub.com"
    ].includes(name));
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

    // 零节点地区物理剔除仿真测试（模拟缺失韩国节点的订阅输入）
    const noKrInput = JSON.parse(JSON.stringify(mockInput));
    noKrInput.proxies = noKrInput.proxies.filter(p => !p.name.includes("韩国"));
    const noKrOutput = main(noKrInput);
    const noKrGroupNames = noKrOutput["proxy-groups"].map(g => g.name);
    const noKrSelectGroup = noKrOutput["proxy-groups"].find(g => g.name === "节点选择");
    const noKrSelectProxies = noKrSelectGroup ? noKrSelectGroup.proxies : [];
    const noKrAllGroupProxies = noKrOutput["proxy-groups"].flatMap(g => Array.isArray(g.proxies) ? g.proxies : []);

    console.log(JSON.stringify({{
      remainingProxies: remainingProxies,
      groupsCount: groupsCount,
      leakedProxiesInGroups: leakedProxiesInGroups,
      providersCount: providersCount,
      defaultProviderProxy: sampleProvider.proxy,
      defaultProviderUrl: sampleProvider.url,
      switchedSampleProxy: switchedSampleProxy,
      switchedSampleUrl: switchedSampleUrl,
      switchedSampleIcon: switchedSampleIcon,
      hasDns: !!output.dns,
      dnsFakeIpFilters: output.dns ? output.dns["fake-ip-filter"] : [],
      dnsPolicy: output.dns ? output.dns["nameserver-policy"] : {{}},
      nameserver: output.dns ? output.dns.nameserver : [],
      proxyServerNameserver: output.dns ? output.dns["proxy-server-nameserver"] : [],
      directNameserver: output.dns ? output.dns["direct-nameserver"] : [],
      ipv6: output.ipv6,
      emptyIpv6: emptyOutput.ipv6,
      regionGroupProxies: output["proxy-groups"].filter(g => g.type === "url-test" && g.filter).map(g => ({{ name: g.name, proxies: g.proxies }})),
      groupsExcludeFilters: output["proxy-groups"].map(g => ({{ name: g.name, excludeFilter: g["exclude-filter"] }})),
      testUrls: output["proxy-groups"].filter(g => g.url).map(g => ({{ name: g.name, url: g.url }})),
      rulesCount: output.rules.length,
      rulesTop: output.rules.slice(0, 20),
      rulesBottom: output.rules.slice(-3),
      emptySafe: Array.isArray(emptyOutput["proxy-groups"]) && Array.isArray(nullOutput.rules),
      groupNames: output["proxy-groups"].map(g => g.name),
      providerKeys: Object.keys(output["rule-providers"]),
      allRules: output.rules,
      noKrHasKoreaGroup: noKrGroupNames.includes("韩国节点"),
      noKrSelectHasKorea: noKrSelectProxies.includes("韩国节点"),
      noKrAnyGroupHasKorea: noKrAllGroupProxies.includes("韩国节点"),
      noKrGroupsCount: noKrOutput["proxy-groups"].length,
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

    # 断言 5: 级联清理无死链（验证全量策略组内绝无已被剔除节点的残留引用）
    leaked_in_groups = res["leakedProxiesInGroups"]
    assert len(leaked_in_groups) == 0, f"✘ [{tier}] 策略组中残留已被移除的节点死链引用: {leaked_in_groups}"

    # 断言 5.1: 零节点地区组物理剔除与上游引用自动净化 (Linus: 好品味消除视觉噪音与死锁)
    assert not res["noKrHasKoreaGroup"], f"✘ [{tier}] 无韩国节点输入时，'韩国节点' 策略组未被物理剔除！"
    assert not res["noKrSelectHasKorea"], f"✘ [{tier}] 无韩国节点输入时，'节点选择' 策略组仍残留 '韩国节点' 死链！"
    assert not res["noKrAnyGroupHasKorea"], f"✘ [{tier}] 无韩国节点输入时，策略组中仍残留 '韩国节点' 引用！"
    assert res["noKrGroupsCount"] == exp_groups - 1, f"✘ [{tier}] 物理剔除韩国节点后策略组数量应为 {exp_groups - 1}，实测 {res['noKrGroupsCount']}"

    # 断言 6: DNS 与 Fake-IP 白名单（含连通性探测放行与 Google 排除）
    fake_filters = res["dnsFakeIpFilters"]
    assert "+.corp.internal" in fake_filters, f"✘ [{tier}] 工作域名未自动并入 Fake-IP 放行列表！"
    assert res["dnsPolicy"].get("+.corp.internal") == "10.0.0.53", f"✘ [{tier}] 工作内网专有 DNS 策略未正确注入！"
    for pd in CAPTIVE_PORTAL_DOMAINS:
        assert pd in fake_filters, f"✘ [{tier}] 连通性探测域名 {pd} 未在 Fake-IP 放行列表中！"
    assert not any("connectivitycheck.gstatic.com" in f for f in fake_filters), f"✘ [{tier}] Google gstatic 域名未被排除在 Fake-IP 绕过列表外！"
    assert res["proxyServerNameserver"] == [
        "223.5.5.5",
        "119.29.29.29",
        "https://223.5.5.5/dns-query",
        "https://doh.pub/dns-query",
    ], f"✘ [{tier}] proxy-server-nameserver 顺序或内容未优化为双 UDP 优先 + 双 DoH 兜底: {res['proxyServerNameserver']}"
    assert res["directNameserver"] == [
        "223.5.5.5",
        "119.29.29.29",
        "system",
    ], f"✘ [{tier}] direct-nameserver 未加固为双 UDP + system 兜底: {res['directNameserver']}"
    assert res["ipv6"] is False, f"✘ [{tier}] 顶层 config.ipv6 未显式设置为 false: {res['ipv6']}"
    assert res["emptyIpv6"] is False, f"✘ [{tier}] 空输入时顶层 config.ipv6 未显式设置为 false: {res['emptyIpv6']}"
    assert res["nameserver"] == [
        "223.5.5.5",
        "119.29.29.29",
        "https://223.5.5.5/dns-query",
        "https://doh.pub/dns-query",
    ], f"✘ [{tier}] nameserver 未配置为双 UDP 优先 + 双 DoH 兜底: {res['nameserver']}"

    # 地区策略组属地纯净性检查 (严禁将全局「自动选择」等动态组或直连「DIRECT」注入地区组，消除 33ms 延迟劫持与直连断网)
    for rg in res.get("regionGroupProxies", []):
        assert "自动选择" not in (rg.get("proxies") or []), f"✘ [{tier}] 地区组 '{rg['name']}' 违规残留全局动态组 '自动选择': {rg.get('proxies')}"
        assert "DIRECT" not in (rg.get("proxies") or []), f"✘ [{tier}] 地区组 '{rg['name']}' 违规残留直连 'DIRECT': {rg.get('proxies')}"
        assert not rg.get("proxies"), f"✘ [{tier}] 地区组 '{rg['name']}' proxies 应为空或未定义，实测为: {rg.get('proxies')}"

    # 核验工业级标准 204 HTTPS 测速 URL 与策略组冗余正则精简
    for tu in res.get("testUrls", []):
        assert tu["url"] == "https://www.gstatic.com/generate_204", f"✘ [{tier}] 策略组 '{tu['name']}' 测速地址未更新为 https://... : {tu['url']}"

    groups_ef_map = {g["name"]: g.get("excludeFilter") for g in res.get("groupsExcludeFilters", [])}

    # 1. 验证已在 JS 内存层完成垃圾清洗的策略组，已彻底剥离 exclude-filter
    clean_groups = ["自动选择", "手动切换", "香港节点", "日本节点", "狮城节点", "韩国节点"]
    for cg_name in clean_groups:
        if cg_name in groups_ef_map:
            assert groups_ef_map[cg_name] is None, f"✘ [{tier}] 策略组 '{cg_name}' 未彻底移除冗余 exclude-filter: {groups_ef_map[cg_name]}"

    # 2. 验证特定地区与排他排除规则完整保留且未被破坏
    assert groups_ef_map.get("美国节点") == "(?i)Australia|俄罗斯|Russia|Belarus|巴西|Brazil", f"✘ [{tier}] 美国节点特定排除规则丢失或损坏: {groups_ef_map.get('美国节点')}"
    assert groups_ef_map.get("台湾节点") == "(?i)Network|Software|Westward", f"✘ [{tier}] 台湾节点特定排除规则丢失或损坏: {groups_ef_map.get('台湾节点')}"
    other_ef = groups_ef_map.get("其他国家")
    assert other_ef and other_ef.startswith("(?i)美国"), f"✘ [{tier}] 其他国家排他排除规则丢失或损坏: {other_ef}"

    # 3. 任何策略组的 exclude-filter 中均严禁残留通用垃圾信息特征正则
    for name, ef in groups_ef_map.items():
        if ef:
            assert "剩余流量" not in ef and "到期时间" not in ef and "非代理节点" not in ef, f"✘ [{tier}] 策略组 '{name}' 残留冗余垃圾节点特征正则: {ef}"

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
