# mihomo-override 核心工程与架构守则 (AGENTS.md)

本项目是一套面向 Mihomo (Clash.Meta) 内核的高性能全合一分流覆写体系。任何代码修改、规则增删与配置重构均须严格遵守以下铁律：

## 1. 核心架构与健壮性准则 (Architecture & Reliability Invariants)

1. **测速协议高可靠标准 (HTTPS 204)**：
   - 规则配置文件 (`config/rules_profile.json`) 中的 `testOptions.url` 必须统一使用标准 **HTTPS 204**（`https://www.gstatic.com/generate_204`）；
   - **铁律**：严禁在生产环境冒进切换为明文 HTTP 80 测速。商业中转反代服务器（Nginx/HAProxy）在响应 HTTP 80 204 短连接后会主动 FIN/RST 掐断 TCP，导致连接池复用崩溃、内核频繁抛出 `use of closed network connection` 并在快速测速时爆发超时；且明文 HTTP 会引发 Mihomo 官方强烈劫持告警（160+ 条警告）。高可靠的 HTTPS 端到端探测是真实可用性检验的唯一工业标准。

2. **代理解析与直连 DNS 健壮性**：
   - 主 `nameserver` 与 `proxy-server-nameserver` 必须严格遵循 **“大陆直连高效双 UDP 优先 + 单纯 IP DoH 兜底”** 顺序：`["223.5.5.5", "119.29.29.29", "https://223.5.5.5/dns-query"]`，消除域名式 DoH（如 doh.pub）在 bootstrap 时引发的域名预解析死循环，兼顾秒级竞速解析与超大报文防截断；
   - `direct-nameserver` 必须配置为：`["223.5.5.5", "119.29.29.29", "system"]`，消除仅依赖 Windows WinSock 单点解析的瞬断风险。

3. **顶层强制关闭 IPv6 幽灵重试延时**：
   - JS 覆写主配置入口与 YAML 覆写产物顶层显式注入 `ipv6: false`，彻底杜绝 Windows 在无有效 IPv6 路由时 Go 底层 `connectex 10051 (unreachable network)` 挂起空等与延迟飙升。

4. **地区策略组属地纯净性与零节点动态物理剔除准则**：
   - **绝对纯净属地代理（严禁混入 DIRECT 与全局动态组）**：6 核心地区 `url-test` 策略组与 `其他国家` 策略组必须 100% 仅由属地代理节点构成，**严禁混入 `DIRECT`（直连）或 `自动选择` 等动态组**。杜绝跨区 33ms 延迟劫持，且严禁海外业务流量在极端故障时误走直连被大陆阻断；
   - **JS 运行时零节点物理剔除引擎**：在 JS 覆写运行时，利用已清洗节点池对各地区 filter 执行正则真值检测。若当前订阅中该地区节点数为 0（如缺失韩国节点），**物理不生成该地区策略组**；上游组（「节点选择」、「AI 服务」等）通过死链清理引擎自动抹去对该地区的引用，彻底根治零节点引发的内核测速死锁与 UI 噪音；
   - **双轨纯净对齐**：静态数据模型与纯 YAML 产物同样保持纯净的属地动态过滤（`include-all: true`），绝不掺杂任何虚假保底项。

5. **双轨分离与向后兼容 (Never Break Userspace)**：
   - **JS 覆写产物**：预编译策略组 (`SUBBOOST_PROXY_GROUPS`) 必须彻底剥离已由运行时清洗引擎（`TRASH_REGEX`）处理的冗余垃圾特征正则，消除 Go 内核重复匹配开销；
   - **空正则物理防御**：剥离垃圾特征正则后，必须执行真值检测；若剥离后为空白，**必须物理删除 `exclude-filter` 键**，严禁留空字符串 `""`（否则 Go 内核 `regexp.Compile("")` 将误杀全量节点）；
   - **纯 YAML 覆写产物**：**必须 100% 完整保留原始 `exclude-filter` 正则防御**，确保不支持 JS 的传统 YAML 客户端仍然能完整过滤垃圾信息节点。

## 2. 自动化构建与测试质量门禁 (Testing & Guardrails)

任何涉及规则、生成器或配置的修改，必须按序完成以下全套门禁校验：
1. **生成并自检**：运行 `python scripts/gen_override.py`，确保内置的 `self_check_yaml` 与 `self_check_js` 全部断言通过；
2. **沙箱断言测试**：运行 `python scripts/test_js_override.py`，确保 Node.js 10 项核心断言 100% 通过；
3. **真实级联检测**：测试套件中严禁编写空对空伪断言（如引用已被覆盖替换的未定义组），必须真实遍历输出的全部策略组 `proxies` 数组检测死链；
4. **DAG 拓扑核查**：运行 `python scripts/nest_check.py`，确保策略组全局最大嵌套深度 <= 3（健康阈值）且 0 闭环引用；
5. **真实订阅验证**：运行 `python scripts/verify.py`，基于本地订阅底稿确保双轨模式下全部 PASS。

## 3. 物理级安全隔离铁律 (Security Boundary)

- 本地私有内网配置 (`config/private_work.json`) 与自用生成产物 (`override/js/`) 受 `.gitignore` 严密保护，严禁 stage、commit 或 push 至 Git 远程仓库；
- 远程仓库仅追踪公开脱敏模板 (`override/example/`) 与双轨纯 YAML 备份 (`override/yaml/`)。
