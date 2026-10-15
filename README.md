# self-mihomo-override

自用的 mihomo-party 覆写配置与配套工具。目标客户端是 **Clash Party**（`C:\Program Files\Clash Party`），
本仓库只存放**配置产物、生成器、校验脚本与文档**；内核、geo 库、运行时状态一律不进版本库。

---

## 目录结构

```
docs/
  PROJECT.md                      ★ 项目文档（唯一完整上下文：状态/机制/踩坑/待办）

override/
  1b0sb00st01.yaml              SubBoost 规则体系（yaml 覆写，41 组 / 126 规则 / 94 provider）
  1a128e0523d.js                节点清理（垃圾关键字 + 高倍率）

scripts/
  gen_override.py               ★ 生成器：改配置一律改它再重跑，不要手改 yaml
  merge_sim.py                  模拟 JS + YAML 合并链，8 项断言
  build_merged.py               拼出完整配置，供内核 -t 语法校验
  route_probe.py                内核实测：查某域名实际命中哪条规则、走哪个组
  verify.py / region_check.py / nest_check.py / other_check.py / rgn_verify.py
  check_icons.py / check_urls.py
  doc2md.py                     资料库组件 XML → Markdown

reference/                      SubBoost 上游源码片段（只读参考，不参与构建）
  proxy-groups.ts / proxy-group-modules.ts / defaults.ts / config-template.ts
  v240_*.ts                     v2.4.0 类型定义（用于追溯设计变更）
  icon_map.json / qure_names.txt
```

> **完整上下文看 [`docs/PROJECT.md`](docs/PROJECT.md)** —— 客户端合并机制、
> 规则顺序设计、全部踩坑记录、待办优化都在那里。本 README 只讲怎么用。

---

## 部署到本机

配置文件根目录：默认通常为 `%APPDATA%\mihomo-party`（安装版）或客户端指定的工作根目录。

```bash
# 1. 覆写产物
cp override/1b0sb00st01.yaml  override/1a128e0523d.js  <配置根>/override/

# 2. 在 override.yaml 注册表登记 id / name / type / ext / global
#    global: true 的项顺序推荐为
#      1. 前置DNS/私有直连覆写（JS，可选）    ← 若有必须在前
#      2. 1a128e0523d  节点清理（JS）
#      3. 1b0sb00st01  SubBoost规则体系（YAML） ← 必须在后
```

⚠ **顺序不能换**。若有前置 JS 覆写重置 `config.rules`（如内网直连规则），YAML 需在后用 `rules+:` 追加。
反过来的话 YAML 追加的内容会被 JS 整段清掉。

---

## 核心机制速查

> 日常改配置只需看这三条。完整推导、规则顺序、全部踩坑见
> [`docs/PROJECT.md`](docs/PROJECT.md)。

### 覆写合并语义（从 app.asar 解出，权威）

| 类型 | 行为 |
|---|---|
| `ext: js` | `main(config)` 返回值**整对象替换** |
| `ext: yaml` | `deepMerge(profile, patch, true)` |

`deepMerge` 数组键名约定：

| 写法 | 效果 |
|---|---|
| `rules+:` | **追加**到已有数组之后 |
| `+rules:` | 前插到已有数组之前 |
| `rules!:` | 对象整体覆盖 |
| `rules:` | 整段替换（默认） |

⚠ 没有 `prepend-rules` / `append-rules` 这类键名（全 asar 零命中）。
⚠ `applyRuleOverride` 是另一条独立通道，读 `rules/*.yaml` 的 `prepend`/`append`/`delete`，与覆写无关。

### 规则集必须带 `proxy`

每个 `rule-provider` 都要写 `proxy: 节点选择`。缺失时全部规则集**静默拉取失败**，
流量默默全走 `MATCH`，内核不报错。

### 地区正则用 NB() 而非 \b

```python
def NB(code): return rf"(?:^|[^a-zA-Z]){code}(?:[^a-zA-Z]|$)"
```

`\b` 界定的是「词字符」边界，而数字和下划线也属于词字符，
所以 `US01` / `HK_02` / `SG-01` 匹配不上 `\bUS\b` —— 会漏大量节点。

「其他国家」用 `exclude-filter` 反向实现（排掉全部已知地区）。三处刻意**不排**：
单字 `港`（误伤连云港）、单字 `坡`（误伤吉隆坡）、`America`（误伤 Argentina/Colombia）。
绝不能排 `uk/de/fr/ca/au` —— 它们没有独立地区组，排掉会让节点凭空消失。

---

## 工作流

```bash
PY="python"                                                             # Python 解释器
EXE="${MIHOMO_PARTY_BASE:-$APPDATA/mihomo-party}/test/mihomo-test.exe"  # Mihomo Meta v1.19.31

# 改配置 → 改生成器 → 重跑
$PY scripts/gen_override.py

# 模拟合并链（不需要起内核，秒级）
$PY scripts/merge_sim.py

# 内核语法校验
$PY scripts/build_merged.py
cd <输出目录> && $EXE -t -d . -f config.yaml

# 实测某域名走哪个组
$PY scripts/route_probe.py chat.deepseek.com chat.openai.com
```

`gen_override.py` 依赖 `MODULES_TS`（上游 `proxy-group-modules.ts`），单独拷出来跑会缺输入。
在配置根目录下执行即可。

改完生成器后务必跑一次比对，确认 7 组地区正则与产物**逐字一致**（命令见 PROJECT.md 第六节）。

---

## 文档

完整上下文（状态、合并机制、规则顺序、全部踩坑、待办）都在
**[`docs/PROJECT.md`](docs/PROJECT.md)**。这里不重复，避免两份文档说法不一致。

