# Reference 目录资产与契约说明

本项目是一个面向 Mihomo (Clash.Meta) 的高性能自动化覆写生成体系。
`reference/` 目录存放逆向解析上游规则体系时的契约定义与数据源底稿。

## 目录分层架构

### 1. 生产级输入数据源 (Live Production Sources)

以下文件被自动化构建脚本直接读取，**严禁破坏其数据结构与正则提取格式**：
- **[`proxy-group-modules.ts`](./proxy-group-modules.ts)**：分流代理组模块静态字典表（包含 36 个分流规则组元数据），由 `scripts/gen_override.py` 直接解析并生成各档位策略组与规则集。
- **[`qure_names.txt`](./qure_names.txt)**：Qure 图标命名库，供 `scripts/check_icons.py` 校验图标合法性。
- **[`icon_map.json`](./icon_map.json)**：生成的图标映射索引，供生成器索引各策略组对应图标。

### 2. 上游 SubBoost v2.4.0 契约标本库 (Upstream Freeze Snapshots)

以下 `v240_*.ts` 文件是从 SubBoost v2.4.0 仓库中提取的不可变快照，用于本地离线校对字段定义与底层契约，**不参与构建与运行时**：
- **[`v240_config.ts`](./v240_config.ts)**：Clash/Mihomo 配置模型与策略组类型定义（原 `types_v240.ts` 重复文件已物理剔除）。
- **[`v240_definitions.ts`](./v240_definitions.ts)**：SubBoost 核心接口、订阅源数据结构（`SubscriptionSource`）及中转预设名称。
- **[`v240_filtered-proxy-group.ts`](./v240_filtered-proxy-group.ts)**：地区节点枚举（`NodeRegion`）与动态筛选组配置接口。
- **[`v240_proxy-group-modules.ts`](./v240_proxy-group-modules.ts)**：SubBoost v2.4.0 未经工程化改造的原生分流模块底稿。

### 3. 历史逆向参考底稿 (Legacy Reference Prototypes)

以下文件为立项初期用于逆向提取生成算法的原始 TypeScript 参考代码（纯只读备忘，无脚本依赖）：
- `config-template.ts` / `defaults.ts` / `pa.ts` / `yaml.ts` / `proxy-groups.ts` / `provider-config.ts` / `proxy-group-type.ts` / `info-node-name.ts`
