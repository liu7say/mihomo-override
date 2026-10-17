# mihomo-override 核心工程与架构守则 (AGENTS.md)

本项目是一套面向 Mihomo (Clash.Meta) 内核的高性能全合一分流覆写体系。任何代码修改、规则增删与配置重构均须严格遵守以下铁律：

## 1. 核心架构与性能准则 (Performance Invariants)

1. **测速协议极轻量化**：
   - 规则配置文件 (`config/rules_profile.json`) 中的 `testOptions.url` 必须统一使用纯 **HTTP 204**（`http://www.gstatic.com/generate_204` 或 `http://cp.cloudflare.com/generate_204`）；
   - **铁律**：严禁在代理加密隧道内套用额外的 HTTPS 握手测速，杜绝 2~3 个 RTT 往返与证书协商造成的延迟膨胀与 CPU 损耗。

2. **代理解析链路直连保序 (Proxy DNS Order)**：
   - `proxy-server-nameserver` 必须严格遵循 **“大陆直连高效 UDP DNS 优先 + DoH 兜底”** 顺序：`["223.5.5.5", "119.29.29.29", "https://223.5.5.5/dns-query"]`；
   - **铁律**：严禁将 DoH 置于首位，确保内核解析机场代理服务器域名在 2~5ms 内完成，避免冷启动与热重载时的握手阻塞。

3. **双轨分离与向后兼容 (Never Break Userspace)**：
   - **JS 覆写产物**：预编译策略组 (`SUBBOOST_PROXY_GROUPS`) 必须彻底剥离已由运行时清洗引擎（`TRASH_REGEX`）处理的冗余垃圾特征正则，消除 Go 内核重复匹配开销；
   - **空正则物理防御**：剥离垃圾特征正则后，必须执行真值检测；若剥离后为空白，**必须物理删除 `exclude-filter` 键**，严禁留空字符串 `""`（否则 Go 内核 `regexp.Compile("")` 将误杀全量节点）；
   - **纯 YAML 覆写产物**：**必须 100% 完整保留原始 `exclude-filter` 正则防御**，确保不支持 JS 的传统 YAML 客户端仍然能完整过滤垃圾信息节点。

## 2. 自动化构建与测试质量门禁 (Testing & Guardrails)

任何涉及规则、生成器或配置的修改，必须按序完成以下全套门禁校验：
1. **生成并自检**：运行 `python scripts/gen_override.py`，确保内置的 `self_check_yaml` 与 `self_check_js` 全部断言通过；
2. **沙箱断言测试**：运行 `python scripts/test_js_override.py`，确保 Node.js 10 项核心断言 100% 通过；
3. **真实级联检测**：测试套件中严禁编写空对空伪断言（如引用已被覆盖替换的未定义组），必须真实遍历输出的全部策略组 `proxies` 数组检测死链；
4. **DAG 拓扑核查**：运行 `python scripts/nest_check.py`，确保策略组全局最大嵌套深度 <= 1 且 0 闭环引用；
5. **真实订阅验证**：运行 `python scripts/verify.py`，基于本地订阅底稿确保双轨模式下全部 PASS。

## 3. 物理级安全隔离铁律 (Security Boundary)

- 本地私有内网配置 (`config/private_work.json`) 与自用生成产物 (`override/js/`) 受 `.gitignore` 严密保护，严禁 stage、commit 或 push 至 Git 远程仓库；
- 远程仓库仅追踪公开脱敏模板 (`override/example/`) 与双轨纯 YAML 备份 (`override/yaml/`)。
