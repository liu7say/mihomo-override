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
│   ├── js/                                ★【本地私有全合一】已注入私有内网配置 (受 .gitignore 隔离保护)
│   │   ├── customSubBoost.minimal.js      【极简版】手机/Bettbox 轻量办公 (16组, 12规则集)
│   │   ├── customSubBoost.standard.js     【标准版】日常黄金主流推荐 (23组, 24规则集)
│   │   └── customSubBoost.full.js         【全量版】桌面/极客细粒度分流 (41组, 94规则集)
│   ├── example/                           ★【公开脱敏模板】开源纯净脱敏样例 (Git 追踪与分享)
│   │   ├── customSubBoost.minimal.example.js
│   │   ├── customSubBoost.standard.example.js
│   │   └── customSubBoost.full.example.js
│   └── yaml/                              ★【双轨纯 YAML】传统规则追加备用 (Git 追踪)
│       ├── customSubBoost.minimal.yaml
│       ├── customSubBoost.standard.yaml
│       └── customSubBoost.full.yaml
└── scripts/
    ├── gen_override.py                ★ 核心生成器：读取配置，自动化并行渲染 3 大预设档位 JS 与 YAML 产物
    ├── test_js_override.py            ★ 自动化测试：Node.js 运行时 10 项核心断言沙箱套件 (全量覆盖 3 档)
    ├── nest_check.py                  策略组拓扑 DFS 检查与环引用检测 (3 档全量校验: 0环，深度<=1)
    ├── verify.py                      ★ 内核实测：基于本地真实订阅 (profiles/) 或 Mock 兜底校验
    ├── check_icons.py                 Qure Color 图标集存在性与语义替代校验
    ├── check_urls.py                  规则集 CDN 资源连通性与体积探测
    └── archive/                       历史探索、单次调试与文档转换工具归档 (含 doc2md.py 等)
```

---

## 客户端一键部署指南

根据使用场景在 `override/js/` 目录挑选最适合您的预设档位：
- **移动端 / Bettbox 推荐**：`override/js/customSubBoost.standard.js`（日常黄金主流）或 `override/js/customSubBoost.minimal.js`（极简省电，仅核心分流）；
- **桌面 / 极客推荐**：`override/js/customSubBoost.full.js`（全量 41 组细粒度分流）。

### 方案 A：Flclash / bettbox (最简推荐)

1. 打开客户端设置 → **配置覆写 (Script / Override)** 或进入配置脚本编辑区。
2. 打开本仓库对应档位的 JS 文件（如 [override/js/customSubBoost.standard.js](file:///d:/Code/项目/我的/self-mihomo-override/override/js/customSubBoost.standard.js)），**全选复制**并粘贴到客户端脚本输入框中。
3. （可选）在脚本开头的 `CONFIG` 对象中按需调整参数（如 `cleanHighMultiplier` 开关或 `maxMultiplier` 上限）。
4. 保存并更新配置，立即生效！

### 方案 B：Clash Party / Sparkle

1. 将所选档位的 JS 脚本复制到客户端覆写目录：
   - 复制源文件：`override/js/customSubBoost.standard.js`
   - 目标路径通常为：%APPDATA%\mihomo-party\override\customSubBoost.standard.js
2. 打开客户端「覆写」管理面板，新建或注册覆写项：
   - **名称**：`SubBoost 标准版覆写`
   - **类型**：`JavaScript` (ext: `js`)
   - **ID**：`customSubBoost.standard`
   - **全局生效 (Global)**：勾选
3. 此时单一脚本即闭环包含 DNS 接管、节点清洗、策略组装配与全量分流。

### 方案 C：仅支持 YAML 的客户端 (双轨备用)

如果客户端不支持 JavaScript 脚本运行，可直接挂载对应档位的 `override/yaml/customSubBoost.{tier}.yaml` 作为 YAML 覆写。

---

## 运行时配置参数说明 (CONFIG)

在 `override/js/customSubBoost.*.js` 顶部，提供了简明易懂的声明式配置字典：

```javascript
const CONFIG = {
  // === 规则集与图标拉取策略 (解决冷启动 EOF 与代理死锁) ===
  ruleProviderProxy: "DIRECT",   // 规则集拉取通道："DIRECT"（推荐，彻底规避冷启动死锁）或 "节点选择"
  ruleProviderCdn: "fastly",     // 规则集与图标 CDN 源："fastly" | "gcore" | "cdn" | "testingcf"

  // === 节点清洗引擎 ===
  cleanTrashNodes: true,        // 是否过滤订阅自带的官网/广告/流量提示等垃圾节点
  cleanHighMultiplier: true,    // 是否剔除高倍率吸血节点 (如 2x, 3x, 5x, 10x 等)
  maxMultiplier: 1.0,           // 允许保留的最高倍率阈值 (超过则自动清洗剔除)

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

本项目轻量纯净，兼容 Python 3.9+ 与 `pyyaml`：

```bash
pip install -r requirements.txt
```

### 2. 本地私有内网配置 (可选)

如需在本地使用生成器直接烧录个人工作内网信息：
1. 复制模板：`cp config/private_work.example.json config/private_work.json`
2. 编辑 `config/private_work.json` 填入您的内网域名、IP 和 Nameserver；
3. `config/private_work.json` 已被 Git 严密忽略，绝不会被意外提交。

### 3. 覆写编译指南 (构建工作流)

核心生成器为 `scripts/gen_override.py`，支持多档预设并行编译、单轨定制与命令行参数：

#### A. 标准一键全量编译 (推荐)

直接运行核心编译脚本，生成器将自动执行「读取模块配置 → 探测私有内网 → 并行构建 3 档预设产物 → Node.js AST 语法树自检 → 规则目标引用完整性断言」闭环：

```bash
python scripts/gen_override.py
```

**编译输出与生成逻辑**：
- `override/js/customSubBoost.{minimal,standard,full}.js`：★ **本地自用全合一脚本**。若检测到 `config/private_work.json`，自动将其中的内网域名、IP、进程和 DNS 策略无缝打包注入顶部 `CONFIG`（已被 `.gitignore` 目录级隔离保护，绝不泄漏）。
- `override/example/customSubBoost.{minimal,standard,full}.example.js`：★ **公开脱敏模板**。永不包含任何个人敏感信息，供 Git 追踪或分享。
- `override/yaml/customSubBoost.{minimal,standard,full}.yaml`：★ **双轨纯 YAML 备份**。供仅支持 YAML 格式的客户端使用。

#### B. 常用构建参数与编译模式

生成器内置了灵活的 CLI 参数，满足不同场景构建需求：

```bash
# 场景 1：仅编译标准版 (standard)
python scripts/gen_override.py --preset standard

# 场景 2：仅编译 All-in-One JS 覆写 (适合 Flclash / bettbox / Clash Party 用户)
python scripts/gen_override.py --js-only

# 场景 3：仅编译纯 YAML 覆写 (适合纯 YAML 客户端)
python scripts/gen_override.py --yaml-only

# 场景 4：指定规则集通过代理拉取并切换 CDN 镜像
python scripts/gen_override.py --provider-proxy 节点选择 --cdn-host gcore.jsdelivr.net
```

| 参数选项 | 类型 | 默认值 | 作用说明 |
|---|---|---|---|
| `--preset <tier>` | string | `all` | 生成档位：`all` (并行产出 3 档) \| `minimal` (极简 ~15组) \| `standard` (标准 ~22组) \| `full` (全量 41组) |
| `--js-only` | flag | `false` | 仅编译生成 All-in-One JS 脚本，跳过 YAML 生成 |
| `--yaml-only` | flag | `false` | 仅编译生成纯 YAML 产物，跳过 JS 生成 |
| `--provider-proxy <name>` | string | `DIRECT` | 规则集提供者默认代理通道（默认 `DIRECT` 彻底规避冷启动死锁；可选 `节点选择` 等） |
| `--cdn-host <host>` | string | `fastly.jsdelivr.net` | 规则集与图标的 CDN 域名（支持 `fastly`, `gcore`, `cdn`, `testingcf` 等） |

#### C. 定制规则集与策略组开关

如需在全量版中增删特定的分流策略组（例如禁用部分小众流媒体、启用特定的游戏模块）：
1. 打开 `config/rules_profile.json`；
2. 在 `modules` 字典中将对应模块设为 `enabled: true` 或 `enabled: false`；
3. （可选）在 `test_options` 中调整 `url-test` 的探测间隔 (`interval`) 或容差 (`tolerance`)；
4. 重新执行 `python scripts/gen_override.py` 即可完成重新编译。

### 4. 运行全套质量门禁与断言测试

```bash
# 1. 运行 Node.js 运行时测试套件 (10项核心功能与外键引用完整性断言，覆盖全部 3 档)
python scripts/test_js_override.py

# 2. 运行代理组拓扑有向图无环检测与最大深度核查 (覆盖全部 3 档)
python scripts/nest_check.py

# 3. 运行多维订阅全量验证 (自动扫描 profiles/ 真实底稿，无环境时自动 Mock 兜底)
python scripts/verify.py

# 4. 图标集存在性与语义替代校验
python scripts/check_icons.py
```

---

## 性能调优亮点 (相比原版 SubBoost)

1. **消除健康检查风暴**：
   - 自动选择组全面引入 `lazy: true`、`tolerance: 50` 与 `interval: 600`，彻底消除了后台并发测速对路由器连接表的侵蚀与频繁乒乓断流。
2. **根治冷启动死锁与 TLS EOF 报错**：
   - 规则集默认解耦为 `DIRECT` 直连通道与高可用 `fastly.jsdelivr.net` CDN，并在 JS 头部暴露 `ruleProviderProxy` 与 `ruleProviderCdn` 开关，支持客户端运行时自由切换，彻底规避冷启动代理通道未就绪引发的 `SSL EOF` 与 `429 Rate Limit` 问题。
3. **三档独立预设架构**：
   - 提供 `minimal` (16组)、`standard` (23组)、`full` (41组) 三大独立档位，既解决了手机/移动端 41 组长列表滑动渲染卡顿与视觉臃肿，又完整保留了桌面端全域细粒度分流能力。
4. **节点清洗级联断链防护与外键完整性**：
   - 清洗高倍率与垃圾节点后，自动遍历并清洗所有策略组中的 `proxies` 引用列表；前置游戏规则智能动态归流，杜绝内核加载时出现 `proxy not found` 致命异常。
