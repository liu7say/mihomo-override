<div align="center">

# mihomo-override

**工业级全合一分流覆写体系与多预设档位解决方案**

适用于 **Clash Party**、**Flclash**、**bettbox** 及 **Sparkle** 等基于 **Mihomo (Clash.Meta)** 内核的全平台客户端

[![Release](https://img.shields.io/github/v/release/liu7say/mihomo-override?style=flat-square&color=blue)](https://github.com/liu7say/mihomo-override/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Kernel](https://img.shields.io/badge/Kernel-Mihomo%20Meta-orange?style=flat-square)](https://github.com/MetaCubeX/mihomo)
[![CI Build](https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square)](https://github.com/liu7say/mihomo-override/actions)

[English](README_EN.md) | [简体中文](README.md)

</div>

---

## 项目简介

**mihomo-override** 是一套专为 Mihomo (Clash.Meta) 生态量身定制的高性能、全闭环规则覆写工程方案。

针对传统规则覆写“多文件编排脆弱易清空、规则集冷启动死锁引发 TLS EOF 报错、并发健康检查拖垮路由器连接表、移动端海量策略组滑动卡顿”等工业级网络痛点，本项目通过现代化代码生成器与运行时防御架构，为不同硬件终端提供从极简省电到桌面极客的全域分流能力。

---

## 核心优势与技术调优

| 核心调优特性 | 传统覆写痛点 | 本项目解决方案 | 实际收益 |
|---|---|---|---|
| **零冷启动死锁 (No Deadlock)** | 规则集走代理通道拉取，冷启动时因节点未建连频繁触发 `SSL EOF` 或假死 | 规则集默认解耦为 `DIRECT` 直连通道，并采用全球高可用 CDN 镜像 | 客户端启动毫秒级解析通过，彻底告别 429 限流与 EOF |
| **根除测速风暴 (No Ping Storm)** | 数十个自动组高频并发 Ping 测速，导致路由器连接表被打满、游戏乒乓断流 | 全面落地 `lazy: true`（惰性测速）、`tolerance: 50ms` 与 `interval: 600s` | 消除后台无谓带宽损耗与并发风暴，网络延迟抖动更平滑 |
| **All-in-One 单脚本闭环** | 分散维护 3 个覆写，严格依赖执行顺序；顺序一旦颠倒直接清空分流规则 | 熔铸为唯一 JS 脚本：DNS 统一接管 + 垃圾节点清洗 + 策略组拓扑装配一气呵成 | 跨平台直接复制即用，零外部依赖，杜绝级联死链异常 |
| **三档独立预设矩阵** | 单一全量配置导致手机与轻量终端滑动 40+ 组卡顿发热 | 提供 `Minimal`、`Standard`、`Full` 三套独立编译产物与双轨纯 YAML 备份 | 移动端轻量省电，桌面端保留 94 个规则集的极致细粒度控制 |
| **物理级隐私安全隔离** | 工作内网域名、专有 DNS 和内网 IP 容易意外随 Git 提交泄露 | 本地私有配置存入独立文件，构建产物物理分流至 `override/js/` 整目录隔离 | 仓库仅追踪脱敏公开模板，杜绝敏感企业内网信息外泄 |

---

## 三大预设档位决策矩阵

根据您的终端设备性能与实际分流需求，选择最适配的预设档位：

| 预设档位 | 策略组数量 | 规则集数量 | 展开规则条数 | 内存开销 | 推荐适用设备与场景 |
|---|:---:|:---:|:---:|:---:|---|
| **Minimal (极简版)** | 16 个 | 12 个 | 55 条 | 约 25 MB | **移动端 / 电视盒子**：Android、iOS、Bettbox、智能电视，极致省电、轻量流畅 |
| **Standard (标准版)** | 23 个 | 24 个 | 67 条 | 约 45 MB | **日常黄金主流推荐**：主流流媒体（YouTube/Netflix/Disney+）、Google、微软、AI服务 |
| **Full (全量版)** | 41 个 | 94 个 | 137 条 | 约 75 MB | **桌面极客 / 软路由**：Windows、macOS、Linux，全域流媒体、多地区细粒度分流与游戏加速 |

---

## 快速上手与开箱即用

您可以直接从最新发布的 **[GitHub Releases](https://github.com/liu7say/mihomo-override/releases)** 下载已打包好的脱敏覆写脚本，或克隆本仓库使用。

### 方案 A：Flclash / bettbox (跨平台最简推荐)

1. 打开客户端设置 -> **配置覆写 (Script / Override)** 或进入脚本编辑区；
2. 打开本仓库对应档位的脱敏模板（如 [override/example/customSubBoost.standard.example.js](override/example/customSubBoost.standard.example.js)）；
3. **全选复制代码**，粘贴到客户端脚本输入框中；
4. （可选）在脚本开头的 `CONFIG` 对象中按需调整参数（如最大节点倍率）；
5. 保存并更新配置，立即生效！

### 方案 B：Clash Party / Sparkle (桌面端推荐)

1. 将所选档位的脚本复制到客户端本地覆写目录：
   - 复制源文件：`override/example/customSubBoost.standard.example.js`
   - 建议重命名为：%APPDATA%\mihomo-party\override\customSubBoost.standard.js
2. 打开客户端「覆写」管理面板，新建覆写项：
   - **名称**：`SubBoost 标准版覆写`
   - **类型**：`JavaScript` (扩展名: `js`)
   - **ID**：`customSubBoost.standard`
   - **全局生效 (Global)**：勾选
3. 单一脚本闭环接管 DNS、节点清洗与分流装配。

### 方案 C：仅支持 YAML 的客户端 (双轨备用)

如果客户端环境不支持 JavaScript 执行，可直接挂载对应档位的纯 YAML 覆写：
- 极简版：`override/yaml/customSubBoost.minimal.yaml`
- 标准版：`override/yaml/customSubBoost.standard.yaml`
- 全量版：`override/yaml/customSubBoost.full.yaml`

---

## 运行时配置参数说明 (CONFIG)

所有 All-in-One JS 覆写文件顶部均提供了清晰明了的声明式配置字典，无需重新编译，在客户端直接微调即刻生效：

```javascript
const CONFIG = {
  // ── 1. 基础功能开关 ──
  enableDnsOverride: true,          // 是否接管并覆盖系统/订阅自带 DNS (构建 Fake-IP + 国内双 DoH)
  enableLanDirect: true,            // 是否注入局域网直连规则 (10/8, 172.16/12, 192.168/16 等)
  enableFakeIpFilterSteam: true,    // Steam 握手与下载是否直解国内 IP (保持 IPCountry=CN 满速)

  // ── 2. 规则集与图标拉取策略 (解决冷启动 TLS EOF 与代理死锁) ──
  ruleProviderProxy: "DIRECT",       // 规则集拉取通道："DIRECT"（推荐，规避死锁）或 "节点选择"
  ruleProviderCdn: "fastly",         // 规则集与图标 CDN 源："fastly" | "gcore" | "cdn" | "testingcf"

  // ── 3. 节点清洗引擎 (运行时动态执行) ──
  cleanTrashNodes: true,            // 是否过滤公告/流量到期/官网等垃圾信息节点
  cleanHighMultiplier: true,        // 是否过滤高倍率吸血节点
  maxMultiplier: 1.0,               // 允许保留的最高节点倍率阈值 (超过则自动清洗剔除)

  // ── 4. 工作内网与私有白名单 (零延迟直连，不走代理) ──
  enableWorkRules: true,            // 是否启用工作内网直连与专属分流
  workDomains: [                    // 内网专属域名通配白名单
    // "+.corp.example.com", "+.internal.cn"
  ],
  workIpCidrs: [                    // 内网 IP 网段白名单
    // "10.0.0.0/8", "172.16.0.0/12"
  ],
  workNameserverPolicy: {           // 工作内网专属解析 DNS (精准防解析污染)
    // "+.corp.example.com": "10.0.0.1"
  }
};
```

---

## 项目目录结构

```
├── .github/workflows/                 GitHub Actions 自动化 CI/CD 与 Release 流水线
├── pyproject.toml                     现代 Python 工程打包元信息
├── requirements.txt                   运行依赖（极简轻量，仅需 pyyaml）
├── config/
│   ├── rules_profile.json             SubBoost 36 个业务规则模块清单与测速调优参数
│   ├── private_work.example.json      [公开模板] 脱敏个人内网配置范例
│   └── private_work.json              [本地私有] 个人工作内网真实配置 (受 .gitignore 严密隔离)
├── docs/
│   ├── PROJECT.md                     项目权威技术架构、合并语义与跨端适配指南
│   └── PERFORMANCE.md                 深度网络性能调优与冷启动基准测试报告
├── override/
│   ├── js/                            [本地私有产物] 已注入真实内网配置 (整目录 gitignore 保护)
│   │   ├── customSubBoost.minimal.js
│   │   ├── customSubBoost.standard.js
│   │   └── customSubBoost.full.js
│   ├── example/                       [公开脱敏模板] 纯净脱敏样例 (Git 追踪，供开源分享)
│   │   ├── customSubBoost.minimal.example.js
│   │   ├── customSubBoost.standard.example.js
│   │   └── customSubBoost.full.example.js
│   └── yaml/                          [双轨纯 YAML] 传统规则追加备用 (Git 追踪)
│       ├── customSubBoost.minimal.yaml
│       ├── customSubBoost.standard.yaml
│       └── customSubBoost.full.yaml
└── scripts/
    ├── gen_override.py                核心生成器：读取配置并并行渲染 3 大档位 JS 与 YAML
    ├── test_js_override.py            自动化测试：Node.js 运行时 10 项核心断言沙箱套件
    ├── nest_check.py                  策略组拓扑有向图无环检测与最大深度核查
    ├── verify.py                      内核实测：基于本地真实机场订阅底稿进行语法与分流测试
    ├── check_icons.py                 Qure Color 图标集存在性与语义替代校验
    └── check_urls.py                  规则集 CDN 资源连通性与体积探测
```

---

## 本地开发与编译指南

本项目使用纯 Python 3.9+ 编写，依赖极轻：

```bash
# 1. 克隆仓库并安装依赖
git clone https://github.com/liu7say/mihomo-override.git
cd mihomo-override
pip install -r requirements.txt

# 2. 一键编译全量 3 大预设档位 (自动产出 js/, example/, yaml/)
python scripts/gen_override.py

# 3. 运行全套质量门禁断言测试
python scripts/test_js_override.py    # Node.js 运行时 10 项功能与引用完整性测试
python scripts/nest_check.py          # 策略组 DAG 拓扑无环检测 (0 闭环, 深度 <= 1)
```

---

## 常见问题排查 (FAQ)

<details>
<summary><b>Q1: 为什么客户端更新配置时提示规则集下载失败或 SSL/TLS EOF？</b></summary>

> **原因**：部分第三方规则集走代理拉取时，在客户端启动瞬间代理节点尚未完成握手建连，引发死锁；或者部分 CDN 镜像（如 Cloudflare 测试节点）触发了 TLS 重协商导致 Go 语言标准库阻断。  
> **解决**：本项目的 All-in-One 脚本已默认将规则集通道解耦为 `DIRECT` 直连，并将 CDN 设为高可用的 Fastly 节点。如需切换，直接在脚本顶部修改 `ruleProviderProxy: "DIRECT"` 与 `ruleProviderCdn: "fastly"` 即可。
</details>

<details>
<summary><b>Q2: 为什么我的某些高倍率节点不见了？</b></summary>

> **原因**：本项目内置了节点清洗引擎，默认会自动剔除吸血的高倍率节点（倍率 > 1.0x），防止意外跑飞流量。  
> **解决**：在脚本头部将 `cleanHighMultiplier` 设为 `false`（完全关闭倍率过滤），或调大 `maxMultiplier: 2.0`（允许 2 倍率及以下节点保留）。
</details>

<details>
<summary><b>Q3: 手机端使用全量版感觉策略组长列表滑动略有掉帧，如何解决？</b></summary>

> **解决**：移动端推荐使用 **`Standard (标准版)`**（23 组）或 **`Minimal (极简版)`**（16 组）。这两个档位精简了桌面端繁复的细粒度流媒体分类，聚焦核心网络直连与主流社交/视频分流，内存占用削减 50% 以上，滑动顺畅自然。
</details>

---

## 致谢与开源基石 (Acknowledgments)

本项目深度借鉴、整合并受益于以下优秀的开源项目与社区生态，特此致以诚挚敬意：

| 开源项目 / 资源 | 角色与贡献定位 | 官方链接 | 开源协议 |
|---|---|---|:---:|
| **SubBoost** | 完整版规则体系架构、策略组拓扑设计与业务模块蓝本 | [SubBoost/subboost](https://github.com/SubBoost/subboost) | GPL-3.0 |
| **ACL4SSR** | 中文互联网分流规则长期沉淀与场景划分范式基石 | [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) | GPL-3.0 |
| **Qure IconSet** | 高清、规范且全彩色的策略组与地区节点视觉图标库 | [Koolson/Qure](https://github.com/Koolson/Qure) | MIT |
| **MetaCubeX (meta-rules-dat)** | 高性能紧凑型二进制 `.mrs` 规则集与高可用 CDN 数据源 | [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | GPL-3.0 |

特别感谢所有在 Mihomo (Clash.Meta) 规则体系与网络性能领域默默贡献的开源维护者们！

---

## 开源许可证

本项目基于 [MIT License](LICENSE) 协议开源。
