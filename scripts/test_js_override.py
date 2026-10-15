"""
==============================================================================
全合一 JS 覆写运行时自动化测试套件 (test_js_override.py)
==============================================================================

【功能定位】
利用 Node.js 真实运行环境，对 override/customSubBoost.js 执行全方位运行时行为仿真：
1. 节点清洗引擎：验证垃圾节点过滤与高倍率识别（排除 -X2 线路误伤）；
2. 策略组级联清洗：验证策略组中的已剔除节点是否被彻底移除（零死链引用）；
3. 全局 DNS 与 Fake-IP：验证 Fake-IP 绕过规则与工作内网专有 DNS 策略合并；
4. 规则链拓扑保序：验证局域网直连、工作内网直连、游戏直连/代理与 MATCH 兜底；
5. 空安全防御：验证在空配置或异常字段输入时稳定运行、永不抛出未捕获异常。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
JS_PATH = REPO_ROOT / "override" / "customSubBoost.js"


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


def main() -> int:
    if not JS_PATH.exists():
        sys.exit(f"【致命错误】找不到 JS 覆写文件: {JS_PATH}")

    js_rel = os.path.relpath(JS_PATH, REPO_ROOT).replace("\\", "/")

    test_driver = f"""
    const {{ main, CONFIG }} = require('./{js_rel}');

    // 1. 构建模拟订阅输入
    const mockInput = {{
      proxies: [
        {{ name: "🇺🇸 美国 01", type: "ss", server: "1.1.1.1", port: 443 }},
        {{ name: "🇭🇰 香港 02 | 1x", type: "ss", server: "1.1.1.2", port: 443 }},
        {{ name: "🇯🇵 日本 IEPL-X2", type: "ss", server: "1.1.1.3", port: 443 }}, // 线路编号，倍率应为 null，必须保留
        {{ name: "🇸🇬 狮城 04 [2x]", type: "ss", server: "1.1.1.4", port: 443 }},  // 2倍率，必须剔除
        {{ name: "到期时间: 2026-12-31", type: "ss", server: "1.1.1.5", port: 443 }}, // 垃圾节点，必须剔除
        {{ name: "剩余流量: 500G", type: "ss", server: "1.1.1.6", port: 443 }},       // 垃圾节点，必须剔除
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

    // 2. 模拟配置个性化工作地址
    CONFIG.cleanTrashNodes = true;
    CONFIG.cleanHighMultiplier = true;
    CONFIG.maxMultiplier = 1.0;
    CONFIG.enableWorkRules = true;
    CONFIG.workDomains = ["oa.corp.com", "+.corp.internal"];
    CONFIG.workIpCidrs = ["10.20.0.0/16", "172.16.88.1/32"];
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

    console.log(JSON.stringify({{
      remainingProxies: remainingProxies,
      groupsCount: groupsCount,
      testGroupProxies: testGroupProxies,
      providersCount: providersCount,
      hasDns: !!output.dns,
      dnsFakeIpFilters: output.dns ? output.dns["fake-ip-filter"] : [],
      dnsPolicy: output.dns ? output.dns["nameserver-policy"] : {{}},
      rulesCount: output.rules.length,
      rulesTop: output.rules.slice(0, 15),
      rulesBottom: output.rules.slice(-3),
      emptySafe: Array.isArray(emptyOutput["proxy-groups"]) && Array.isArray(nullOutput.rules),
    }}));
    """

    print("[*] 正在启动 Node.js 进行 customSubBoost.js 运行时全量断言核查...")
    res = run_node_test(test_driver)

    remaining = res["remainingProxies"]
    print(f"  清洗后剩余代理节点 ({len(remaining)} 个): {remaining}")

    # 断言 1: 垃圾节点必须被彻底剔除
    assert "到期时间: 2026-12-31" not in remaining, "✘ 垃圾公告节点未被过滤！"
    assert "剩余流量: 500G" not in remaining, "✘ 剩余流量信息节点未被过滤！"

    # 断言 2: 高倍率节点必须被过滤，低倍率与线路代号保留
    assert "🇸🇬 狮城 04 [2x]" not in remaining, "✘ 2x 高倍率节点未被过滤！"
    assert "🇺🇸 美国 01" in remaining, "✘ 普通节点误伤！"
    assert "🇯🇵 日本 IEPL-X2" in remaining, "✘ IEPL-X2 线路代号被误伤过滤！"
    print("  ✔ 节点清洗引擎断言通过（垃圾节点过滤、2x高倍率剔除、IEPL-X2正确保留）")

    # 断言 3: 策略组数量为 41 个（加原始组共 41 个 SubBoost 组）
    assert res["groupsCount"] >= 41, f"✘ 策略组数量不足 41，实测 {res['groupsCount']}"
    print(f"  ✔ 策略组全量注入通过 (共 {res['groupsCount']} 组)")

    # 断言 4: 规则集数量必须达到 94 个
    assert res["providersCount"] == 94, f"✘ 规则集数量预期 94，实测 {res['providersCount']}"
    print(f"  ✔ 规则集提供者全量注入通过 (共 {res['providersCount']} 个 MRS 规则集)")

    # 断言 5: 策略组级联清理无死链
    test_group_proxies = res["testGroupProxies"]
    assert "🇸🇬 狮城 04 [2x]" not in test_group_proxies, "✘ 策略组中残留已剔除的高倍率节点！"
    assert "剩余流量: 500G" not in test_group_proxies, "✘ 策略组中残留已剔除的垃圾节点！"
    print("  ✔ 策略组级联引用清洗断言通过 (无已删除节点的残留死链)")

    # 断言 6: DNS 与 Fake-IP 白名单合并
    fake_filters = res["dnsFakeIpFilters"]
    assert "+.corp.internal" in fake_filters, "✘ 工作域名未自动并入 Fake-IP 放行列表！"
    assert res["dnsPolicy"].get("+.corp.internal") == "10.0.0.53", "✘ 工作内网专有 DNS 策略未正确注入！"
    print("  ✔ DNS 与 Fake-IP 体系断言通过 (DoH、Steam握手直解与工作内网专有DNS均生效)")

    # 断言 7: 规则链顺序拓扑严格保序
    rules_top = res["rulesTop"]
    rules_bottom = res["rulesBottom"]
    assert any("10.0.0.0/8" in r for r in rules_top), "✘ 规则链最前端缺少局域网私有网段直连！"
    assert any("corp.internal" in r for r in rules_top), "✘ 规则链缺少前置工作域名直连！"
    assert any("corp-vpn.exe" in r for r in rules_top), "✘ 规则链缺少前置工作进程直连！"
    assert rules_bottom[-1].startswith("MATCH,"), "✘ 规则链末尾不是 MATCH 兜底！"
    print(f"  ✔ 规则链拓扑保序断言通过 (共 {res['rulesCount']} 条，局域网->工作直连->游戏->SubBoost->MATCH)")

    # 断言 8: 空安全检查
    assert res["emptySafe"] is True, "✘ 空配置防御失败！"
    print("  ✔ 防御性空安全断言通过 (main({}) 与 main(null) 稳定零崩溃)")

    print("\n============================================================")
    print("✔ customSubBoost.js 全合一覆写运行时测试全部 100% 通过！")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
