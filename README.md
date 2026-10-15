# self-mihomo-override

适用于 **Clash Party**、**Flclash**、**bettbox**（Flclash fork）及 **Sparkle** 等基于 Mihomo (Clash.Meta) 内核客户端的**全合一 (All-in-One) 规则覆写生成器与生产级配置体系**。

基于 [SubBoost](https://github.com/SubBoost/subboost) 完整版模板规则体系、[Qure](https://github.com/Koolson/Qure) 高清彩色图标集，并结合工业级网络性能调优与节点清洗策略开发。

---

## 核心设计哲学 (Linus Torvalds Good Taste)

1. **单文件彻底解耦 (All-in-One 单脚本交付)**：
   - **过去痛点**：需要分散维护 `全局DNS统一覆写.js`、`节点清理.js`、`customSubBoost.yaml` 三个覆写，且严格依赖客户端特定的全局执行顺序（一旦次序颠倒，规则直接被清空）。
   - **新架构**：熔铸为唯一的单文件脚本 `override/customSubBoost.js`。在标准 ECMAScript 沙箱内流水线式完成 **“Fake-IP 与专有 DNS 注入 → 垃圾与高倍率节点清洗 → 41 策略组与 94 规则集装配 → 132 条拓扑保序规则链生成”**。
2. **跨客户端与跨平台原生支持**：
   - 纯 Vanilla ES6 语法，零外部 Node.js / DOM 依赖，带有严密的防御性空安全机制。
   - 完美适配：**Clash Party**、**Flclash**、**bettbox**，全平台（Windows / macOS / Linux / Android / iOS）直接**复制粘贴即用**。
3. **企业私有内网安全隔离 (Zero Leak Git)**：
   - 真实工作内网域名、专有 DNS 与私有 IP 彻底剥离至本地未追踪文件 `config/private_work.json`（已加入 `.gitignore`）。
   - 仓库仅追踪脱敏公开模板 `config/private_work.example.json`，杜绝任何敏感隐私泄露风险。
4. **运行时纯声明式开关**：
   - 生成的 `customSubBoost.js` 头部暴露了清晰明了的 `CONFIG` 对象，所有功能（如垃圾节点过滤、倍率上限阈值、专有内网直连等）均在客户端运行时动态生效，无需重新运行 Python 生成器。

---

## 目录结构

```
├── pyproject.toml                     现代 Python 工程元信息与打包配置
├── requirements.txt                   运行依赖（极简轻量，仅需 pyyaml）
├── config/
│   ├── rules_profile.json             SubBoost 36 个业务规则模块清单与测速调优预设
│   ├── private_work.json              [本地私有] 个人工作内网直连与专有 DNS 配置 (git 忽略)
│   └── private_work.example.json      [公开模板] 脱敏内网配置范例
├── docs/
│   ├── PROJECT.md                     ★ 项目权威技术文档（架构设计/合并机制/跨端适配/踩坑）
│   └── PERFORMANCE.md                 ★ 规则与网络性能分析报告（冷启动/测速风暴/DNS链路）
├── override/
│   ├── customSubBoost.js              ★【本地自用】全合一单文件 JS 覆写 (自动打包内网配置，已被 gitignore 隔离)
│   ├── customSubBoost.example.js      ★【公开模板】纯净脱敏版 JS 覆写 (供 Git 追踪与他人参考)
│   └── customSubBoost.yaml            【备用双轨】纯 YAML 覆写 (适用于仅支持 YAML 的客户端)
└── scripts/
    ├── gen_override.py                ★ 核心生成器：读取配置，自动化渲染 JS 与 YAML 双轨产物
    ├── test_js_override.py            ★ 自动化测试：Node.js 运行时 8 项核心断言沙箱套件
    ├── verify.py                      ★ 内核实测：基于真实四大订阅与本地 mihomo-test.exe -t 验证
    ├── nest_check.py                  策略组拓扑 DFS 检查与环引用检测 (0环，深度<=1)
    ├── merge_sim.py                   旧版客户端合并链模拟器
    └── build_merged.py                一键拼装完整 config.yaml 并触发内核语法预检
```

---

## 客户端一键部署指南

### 方案 A：Flclash / bettbox (最简推荐)

1. 打开客户端设置 → **配置覆写 (Script / Override)** 或进入配置脚本编辑区。
2. 打开本仓库的 `override/customSubBoost.js`，**全选复制**并粘贴到客户端脚本输入框中。
3. （可选）在脚本开头的 `CONFIG` 对象中按需调整参数（如 `cleanHighMultiplier` 开关或 `maxMultiplier` 上限）。
4. 保存并更新配置，立即生效！

### 方案 B：Clash Party / Sparkle

1. 将 `override/customSubBoost.js` 复制到客户端的覆写目录：
   - 路径通常为：`%APPDATA%\mihomo-party\override\customSubBoost.js`
2. 打开客户端「覆写」管理面板，新建或注册覆写项：
   - **名称**：`SubBoost 全合一覆写`
   - **类型**：`JavaScript` (ext: `js`)
   - **ID**：`customSubBoost`
   - **全局生效 (Global)**：勾选
3. 此时无需再挂载多个前置 JS，单一脚本即包含全套能力。

### 方案 C：仅支持 YAML 的客户端 (双轨备用)

如果客户端不支持 JavaScript 脚本运行，可直接挂载 `override/customSubBoost.yaml` 作为 YAML 覆写。

---

## 运行时配置参数说明 (CONFIG)

在 `override/customSubBoost.js` 顶部，提供了简明易懂的声明式配置字典：

```javascript
const CONFIG = {
  // === 节点清洗引擎 ===
  cleanTrashNodes: true,        // 是否过滤订阅自带的官网/广告/流量提示等垃圾节点
  cleanHighMultiplier: true,    // 是否剔除高倍率吸血节点 (如 2x, 3x, 5x, 10x 等)
  maxMultiplier: 1.5,           // 允许保留的最高倍率阈值 (超过则自动清洗剔除)

  // === 工作与内网私有白名单 (不走代理，保持零延迟直连) ===
  workDomains: [                // 内网域名后缀白名单
    // "internal.company.com", "corp.example.cn"
  ],
  workIpCidrs: [                // 内网 IP 网段白名单
    // "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
  ],
  workProcesses: [              // 内网专有进程名白名单 (桌面端生效)
    // "vpnclient.exe", "wework.exe"
  ],
  workNameserverPolicy: {       // 工作内网独立解析 DNS (精准防解析污染)
    // "company.com": "10.0.0.1",
  },
};
```

---

## 开发者与生成器指南

### 1. 安装依赖

本项目仅需 Python 3.10+ 与 `pyyaml`：

```bash
pip install -r requirements.txt
```

### 2. 本地私有内网配置 (可选)

如需在本地使用生成器直接烧录个人工作内网信息：
1. 复制模板：`cp config/private_work.example.json config/private_work.json`
2. 编辑 `config/private_work.json` 填入您的内网域名、IP 和 Nameserver；
3. `config/private_work.json` 已被 Git 严密忽略，绝不会被意外提交。

### 3. 一键编译生成覆写产物

运行核心编译命令：

```bash
python scripts/gen_override.py
```

生成器将完成：
- 读取 `config/rules_profile.json` 与规则分类；
- 编译生成 `override/customSubBoost.js` (All-in-One 脚本)；
- 编译生成 `override/customSubBoost.yaml` (双轨 YAML 备份)；
- 自动触发 Node.js 语法树静态自检。

### 4. 运行全套质量门禁与断言测试

```bash
# 1. 运行 Node.js 运行时测试套件 (8项核心功能与容错断言)
python scripts/test_js_override.py

# 2. 运行代理组拓扑有向图无环检测与最大深度核查
python scripts/nest_check.py

# 3. 运行四大真实订阅全量内核预检 (调用本地 mihomo 内核 -t)
python scripts/verify.py
```

---

## 性能调优亮点 (相比原版 SubBoost)

1. **消除健康检查风暴**：
   - 自动选择组全面引入 `lazy: true`、`tolerance: 50` 与 `interval: 600`，彻底消除了后台并发测速对路由器连接表的侵蚀与频繁乒乓断流。
2. **规则集下载可靠性保障**：
   - 94 个 `rule-providers` 统一加上 `proxy: 节点选择`，彻底根绝国内直连 jsdelivr 时遭遇的 `SSL EOF` 与 `429 Rate Limit` 问题。
3. **节点清洗级联断链防护**：
   - 清洗高倍率与垃圾节点后，自动遍历并清洗所有策略组中的 `proxies` 引用列表，杜绝内核加载时出现 `proxy not found` 致命异常。
