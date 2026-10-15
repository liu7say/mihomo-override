# self-mihomo-override 项目文档

> 本文档是本项目**唯一**的完整上下文来源，合并了历次交接文档与项目记忆。
> 最后更新：2026-10-15

---

## 一、当前状态

### 生效的三份覆写

| 注册表序位 | id | 名称 | 类型 | 作用 |
|---|---|---|---|---|
| 1 | `1a128f773c5` | 全局DNS统一覆写（合并版） | js | DNS + 私有内网直连规则（外部前置脚本） |
| 2 | `1a128e0523d` | 节点清理（垃圾关键字+高倍率） | js | 过滤垃圾节点与倍率节点 |
| 3 | `1b0sb00st01` | SubBoost规则体系 | yaml | 41 组 / 126 规则 / 94 provider |

三者均为 `global: true`，**顺序不可调换**（原因见第二节）。

### 规模

| 项 | 数量 |
|---|---|
| proxy-groups | 41 |
| SubBoost 规则 | 126 |
| 私有内网直连规则（JS 侧） | 若干（本地外部配置） |
| **合并后规则总数** | **126 + 私有规则数** |
| rule-provider | 94（每个都带 `proxy: 节点选择`） |
| 规则条目（解压后） | 约 17.2 万条 |

### 环境

| 项 | 值 |
|---|---|
| 客户端 | Clash Party，`C:\Program Files\Clash Party` |
| 配置根 | `%APPDATA%\mihomo-party`（或客户端工作目录） |
| 版本库 | `self-mihomo-override` 根目录 |
| 验证内核 | `test\mihomo-test.exe`（Mihomo Meta v1.19.31） |
| 规则集源 | `MetaCubeX/meta-rules-dat@meta`（`.mrs` 二进制，经 jsdelivr 镜像） |
| 当前订阅 | `1a0377776c2`（TAGMeta，226 节点） |

### 目录

**版本库**（进 git）：

```
docs/PROJECT.md         本文档
override/               三份覆写产物
scripts/                生成器与校验脚本
reference/              SubBoost 上游 .ts 片段（只读参考）
```

**配置根**（不进 git，含二进制与运行产物）：

```
override.yaml           覆写注册表（决定执行顺序）
override/<id>.{js,yaml} 覆写本体
profiles/<id>.yaml      订阅原始
work/<id>/config.yaml   合并后运行时配置 —— 排查分流看这里
work/<id>/ruleset/      规则集缓存
test/_sb/               脚本工作副本（含 mihomo-test.exe 与 geo 库）
logs/core-*.log         内核日志
```

---

## 二、客户端覆写合并机制

> 从 `C:\Program Files\Clash Party\resources\app.asar` 解出的源码，权威依据。
> **改覆写前必读。**

### 执行流程

```
applyOverrides(profile, overrideIds)
  ├─ ext: js   → runOverrideScript()   main(config) 返回值【整对象替换】
  └─ ext: yaml → deepMerge(profile, patch, isOverride=true)
```

- `overrideIds` = `[...new Set(globalOverride.concat(profileOverride))]`
- **global 覆写按 `override.yaml` 注册表从上到下依次执行**
- `applyRuleOverride()` 是**另一条独立通道**，读 `rules/*.yaml` 的
  `prepend` / `append` / `delete`，与覆写无关 —— **别把两者搞混**

### deepMerge 数组语义

| 键名写法 | 效果 |
|---|---|
| `rules+:` | **追加**到已有数组之后 |
| `+rules:` | 前插到已有数组之前 |
| `rules!:` | 对象整体覆盖 |
| `rules:` | 整段替换（默认） |

键名支持 `<...>` 包裹（内部 `trimWrap` 会剥掉）。

⚠ **不存在** `prepend-rules` / `append-rules` / `delete-rules` 这类键名
（全 asar 搜索零命中，别臆造）。

### 为什么 JS 必须排在 YAML 前面

JS 与 YAML 同时写 `rules` 会**整段互相覆盖** —— 后执行的那份把前一份清空。
这是原方案的 bug 根源（症状：组名和规则莫名变了但找不到原因）。

正确分工：

```
JS  先跑 → config.rules = [...workRules]     重置为私有内网直连规则
YAML 后跑 → rules+:                           在其后追加 126 条
最终为完整合并规则链
```

反过来则 YAML 追加的内容会被 JS 全部清掉。

### YAML 覆写的其他约束

- 别写 `geodata-*` / `geox-url`：与内置 `mihomo.yaml` 冲突且被覆盖
- DNS 不写在 SubBoost 覆写里，由 DNS 覆写负责（两边同写会互相覆盖）
- 启用 `1a128f773c5` 时**必须停用「国内DNS修复」** —— 后者 `delete config.dns` 会清空
- **别同时启用两个 YAML 覆写**（`1a129bbc284`「GPT写的」与 SubBoost 互斥）

---

## 三、SubBoost 规则体系

### 41 个组的结构

```
 1 节点选择          select      1  自动选择         url-test (lazy:false)
 3 手动切换          select      4  广告拦截         select（无 include-all）
 5-30 业务组 26 个   select      AI服务/油管/谷歌/微软/苹果/电报/推特/Meta/
                                Discord/其他社交/奈飞/迪士尼/欧美流媒体/
                                亚洲流媒体/Steam/PC游戏/主机游戏/代码托管/
                                云服务/开发工具/网盘存储/支付/加密货币/
                                教育学术/新闻/海淘
31 私有网络          select      32 国内服务        select（无 include-all）
33-39 地区组 7 个     url-test    美国/香港/日本/狮城/台湾/韩国/其他国家
                                （lazy:true；「其他国家」为 select+DIRECT）
40 非中国            select      41 漏网之鱼        select（兜底，永远最后）
```

### 选择方式（ACL4SSR 式）

```
节点选择 = [自动选择, <7地区组>, 手动切换, DIRECT, REJECT]
业务组   = [节点选择, 自动选择, <7地区组>, 手动切换, DIRECT, REJECT]
```

**「手动切换」是本覆写新增的组**（SubBoost 原版没有）。业务组不再持有全节点副本后，
单节点选择由它承载 —— 原版靠 33 组各自 `include-all`，内存与 UI 都更重。

### 地区组正则：NB() 而非 \b

```python
def NB(code): return rf"(?:^|[^a-zA-Z]){code}(?:[^a-zA-Z]|$)"
```

`\b` 界定的是「词字符」边界，而**数字和下划线也属于词字符**，
所以 `US01` / `HK_02` / `SG-01` 这类机场常见命名匹配不上 `\bUS\b` —— 会漏大量节点。
NB 改用「非字母即边界」，贴合实际命名习惯。

```
美国节点  (?i)美国|洛杉矶|纽约|…|NB(US)|United.?States|America
          exclude: JUNK + Australia|俄罗斯|Russia|Belarus|巴西|Brazil
香港节点  (?i)香港|NB(HK)|Hong.?Kong|HKG
日本节点  (?i)日本|东京|大阪|…|NB(JP)|Japan|Tokyo|Osaka
狮城节点  (?i)新加坡|狮城|NB(SG)|Singapore
台湾节点  (?i)台湾|台北|台中|新北|彰化|NB(TW)|Taiwan|Taipei|Kaohsiung
          exclude: JUNK + Network|Software|Westward
韩国节点  (?i)韩国|首尔|韓|NB(KR)|Korea|KOR
```

效果：官方原版 94 个误命中 → 本覆写 **0**。

`JUNK` = SubBoost 的 `isSubscriptionInfoNodeName` 三条正则
（剩余流量/到期/余额/版本太旧等），必须排除，否则会被当可测速节点。

### 「其他国家」的三个刻意排除

「其他国家」= 官方 `other` 预设的反向实现：exclude 掉 6 个已有独立组的关键词。

| 排除词 | 原因 |
|---|---|
| 单字 `港` | 会误伤连云港、深港专线等中转线路命名 |
| 单字 `坡` | 会误伤「吉隆坡」 |
| `America` | 会命中 Argentina / Colombia 等国家名，排掉会让它们凭空消失 |

⚠ 美国组自己的 filter **保留** `America` —— 那是正向匹配，命中南美只是不进美国组，
仍会落进「其他国家」，无副作用。

⚠ **绝不能排除 `uk/de/fr/ca/au`** —— 它们没有独立地区组，排掉会让节点凭空消失
（既不在任何地区组，也不在「其他国家」）。这条实际踩过，丢了 TAGMeta 的 16 个英/法/加/澳节点。

---

## 四、规则顺序

### 游戏区块（顺序即全部意义）

Steam 商店与静态资源**必须**排在 `category-games-cn` 之前。
该规则集是全平台 @cn 统一集、覆盖面极大，若商店域名被它先捕获就会走直连，商店页加载失败。

```
- DOMAIN-SUFFIX,store.steampowered.com,Steam     ┐
- DOMAIN-SUFFIX,steamcommunity.com,Steam         │ 商店/社区/静态资源
- DOMAIN-SUFFIX,steamstatic.com,Steam            │ 强制代理（防黑屏）
- DOMAIN,steamstore-a.akamaihd.net,Steam         │
- DOMAIN,steamcommunity-a.akamaihd.net,Steam     │
- DOMAIN,steamuserimages-a.akamaihd.net,Steam    ┘
- RULE-SET,category-games-cn,国内服务            ← 全平台 @cn 统一集
- DOMAIN-SUFFIX,cm.steampowered.com,国内服务     ┐
- DOMAIN-SUFFIX,steamserver.net,国内服务         │ 握手与下载直连
- DOMAIN-SUFFIX,steamcontent.com,国内服务        │ （保持 IPCountry=CN）
- RULE-SET,steam-cn,国内服务                     ┘
- DOMAIN,epicgames-download1-*.file.myqcloud.com,国内服务   ┐
- DOMAIN,epicgames-download1.akamaized.net,国内服务        │
- DOMAIN,fastly-download.epicgames.com,国内服务           │ Epic 7 条
- DOMAIN-SUFFIX,download{,2,3,4}.epicgames.com,国内服务   │
- DOMAIN,blzddist{1,kr1}-a.akamaihd.net,国内服务           ┐
- DOMAIN,bnetproduct-a.akamaihd.net,国内服务               │ 暴雪 5 条
- DOMAIN,blizzard.nefficient.co.kr,国内服务               │
- DOMAIN-SUFFIX,cdn.blizzard.com,国内服务                 ┘
- DOMAIN,origin-a.akamaihd.net,国内服务                   ┐
- DOMAIN,ssl-lvlt.cdn.ea.com,国内服务                     │ EA/Ubisoft 3 条
- DOMAIN,uplaypc-s-ubisoft.cdn.ubi.com,国内服务           ┘
- DOMAIN,assets{1,2}.xboxlive.com,国内服务                ┐
- DOMAIN,xvcf{1,2}.xboxlive.com,国内服务                  │
- DOMAIN,dlassets.xboxlive.com,国内服务                   │ 主机 7 条
- DOMAIN-SUFFIX,dl.playstation.net,国内服务               │
- DOMAIN,atum.hac.lp1.d4c.nintendo.net,国内服务           ┘
- RULE-SET,steam,Steam                                   ← 兜底走代理
```

**设计意图**：厂商官方 @cn 域名直连（腾讯云/世纪互联/蔚蓝等国内 CDN，下载满速）；
商店页面/社区/静态资源走代理（直连会黑屏、图裂）；区服握手直连（保持 IPCountry = CN）。

### 其它顺序决策

| 规则 | 位置 | 理由 |
|---|---|---|
| 云服务 7 条 | `ebay` 之后、`geolocation-!cn` 之前 | AWS/Azure/Cloudflare 承载大量非云业务流量，早期拦截会把 coursera CDN、githubusercontent 截胡 |
| 国内三条 | `geolocation-!cn` 之后、`MATCH` 之前 | 覆盖面极大，放前面会把混合业务一并直连 |
| `cn`（完整国内域名） | 三条中的最后 | 低置信补充，原版刻意后置 |

---

## 五、DNS 覆写要点

前置 DNS 脚本负责写入完整 DNS 段与私有内网直连规则。

### fake-ip-filter 绝不能有 `"*"`

`"*"` 会让 filter 变成「全域名排除」，等于**全局关闭 Fake-IP** ——
既拖慢 CDN 解析，又会让 Steam 商店拿到被污染的国外 IP。

只列真正需要真实 IP 的域名：内网、工作域名、NTP/连通性探测，
以及 Steam 区服握手与下载域名（保持 IPCountry=CN，下载走国内 CDN）。

```
"+.lan"  "+.local"  "time.*.com"  "ntp.*.com"  "+.market.xiaomi.com"
"cm.steampowered.com"  "+.cm.steampowered.com"
"+.steamserver.net"    "+.steamcontent.com"
"+.corp.internal"  "+.oa.example.com"  # 企业/工作内网域名示例
```

商店域名（`store.steampowered.com` 等）**不**放进来 —— 仍走 Fake-IP，
避免商店 CDN 被解析到国外节点而加载失败。

### default-nameserver 必须是纯 IP

```
"default-nameserver": ["223.5.5.5", "119.29.29.29"]
```

带 `tls://` 前缀会形成循环依赖：它的作用是「解析上游 DoH 服务器的域名」，
自己却先要做一次 TLS 握手。

### 私有内网与直连规则（外部配置）

含内网大段直连、企业内网域名、企业专线地址段、
工作协同软件进程名（如 `work-client.exe`），以及 172.16/192.168/100.64/127.0.0.1 兜底。
（注：涉密单位的具体 IP、域名与进程名不入版本库，由各端本地前置脚本自行注入）

---

## 六、生成器

**改配置一律改 `scripts/gen_override.py` 再重跑，不要手改 yaml。**

### 架构：DATA 区 / RENDER 区分离

配置数据集中在 DATA 区，RENDER 区只负责拼装 YAML。
`self_check()` 在写盘前跑一遍，违反约束直接退出非零。
数量检查全部动态推导，不写死 41/94/126 —— 写死会在合法增删组时误报，
误报多了会让人养成忽略警告的习惯。

### 数据来源

| 数据 | 上游文件 |
|---|---|
| 模块与规则定义 | `packages/core/src/generator/proxy-group-modules.ts` |
| 组顺序与 groupType | `packages/core/src/generator/proxy-groups.ts` |
| 规则顺序 | `packages/core/src/generator/rules.ts`（`RULE_ORDER`） |
| 信息节点正则 | `packages/core/src/subscription/info-node-name.ts` |
| DNS/sniffer 模板 | `packages/core/src/config/defaults.ts` |
| 规则源基址 | `packages/core/src/rules/provider-config.ts` |

片段已存在 `reference/`。

### 三处必要适配（原版没有，落地必须改）

1. **规则集换 jsdelivr 镜像** —— 原版 `github.com/.../raw/` 会跳
   raw.githubusercontent.com，国内超时
2. **每个 provider 加 `proxy: 节点选择`** —— 最关键的一条。
   不加则全部规则集静默拉取失败，流量默默全走 MATCH，**不报错**
3. **节点成员用 `include-all` + `exclude-filter`** —— 原版转换时已知节点名，
   静态覆写只能这么表达

### ⚠ 生成器必须与产物同步

2026-10-15 发现：产物已用 NB 正则，但生成器还是旧 `\b` 版，
一重跑就会把产物**回退**。已同步，7 组正则与产物逐字一致。

**改动生成器后务必跑一次比对**：

```bash
python -c "
import importlib.util, re
spec = importlib.util.spec_from_file_location('g', 'scripts/gen_override.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
yml = open('override/1b0sb00st01.yaml', encoding='utf-8').read()
for r in m.REGION_GROUPS:
    v = r['filter'] if r.get('filter') else m.JUNK + '|' + r['exclude']
    print(('PASS' if v in yml else 'FAIL'), r['name'])
"
```

---

## 七、工作流

```bash
PY="python"
EXE="${MIHOMO_PARTY_BASE:-$APPDATA/mihomo-party}/test/mihomo-test.exe"

# 1. 改配置 → 改生成器 → 重跑
$PY scripts/gen_override.py

# 2. 模拟合并链（不起内核，秒级，8 项断言）
$PY scripts/merge_sim.py

# 3. 内核语法校验
$PY scripts/build_merged.py
cd <输出目录> && $EXE -t -d . -f config.yaml

# 4. 实测某域名走哪个组
$PY scripts/route_probe.py chat.deepseek.com chat.openai.com
```

`gen_override.py` 依赖 `MODULES_TS`（上游 `proxy-group-modules.ts`），
单独在版本库跑会缺输入 —— 在配置根 `test/_sb/` 下执行即可。

### 脚本清单

| 脚本 | 用途 |
|---|---|
| `gen_override.py` | 生成器。**唯一配置来源** |
| `merge_sim.py` | 模拟 JS+YAML 合并链，8 项断言 |
| `build_merged.py` | 拼完整配置供内核 `-t` 校验 |
| `route_probe.py` | 内核实测域名分流 |
| `verify.py` | 四订阅内核语法校验 |
| `other_check.py` | 7 地区组覆盖完整性（零重叠零遗漏） |
| `nest_check.py` | 组嵌套环检测 + 深度 |
| `region_check.py` | 地区 filter 准确度（对比官方原版） |
| `rgn_verify.py` | 内核实际组成员核对 |
| `check_icons.py` | 图标存在性核对 |
| `check_urls.py` | 规则集 URL 可达性 |
| `doc2md.py` | 资料库组件 XML → Markdown |

### 部署

改完产物要同步回配置根，并在 `override.yaml` 登记（三份的**顺序不能变**）：

```bash
cp override/*.{yaml,js} "${MIHOMO_PARTY_BASE:-$APPDATA/mihomo-party}/override/"
```

---

## 八、验证结果

### 内核实测（真实内核，非推断）

| 验证项 | 脚本 | 结果 |
|---|---|---|
| 内核语法校验 | `build_merged.py` + `mihomo -t` | 通过，27ms |
| 合并链正确性 | `merge_sim.py` | 8 项断言全过 |
| 合并后规则总数 | `merge_sim.py` | 156（30 + 126） |
| 94 个规则集实际下载 | `live_check*.py` | 全落盘，magic `28b52ffd` |
| NB 正则命中 | `region_check.py` | `US01` / `HK_02` / `US-02` 全部正确进组 |
| 三处误伤防护 | `region_check.py` | `NetWork` / `吉隆坡` / `连云港专线` 全落「其他国家」 |
| 组嵌套环 | `nest_check.py` | 0 环、最大深度 2、初始化 0.3s |
| 地区组覆盖 | `other_check.py` | 零重叠零遗漏，4 订阅覆盖 100% |
| 内核实际组成员 | `rgn_verify.py` | 误伤 0、空组 0 |

### 域名分流实测

| 域名 | 命中规则 | 去向 |
|---|---|---|
| chat.deepseek.com | `geolocation-cn` | 国内服务 → **DIRECT** |
| api.deepseek.com | `geolocation-cn` | 国内服务 → **DIRECT** |
| chat.openai.com | `openai` | AI 服务 |
| api.anthropic.com | `anthropic` | AI 服务 |
| claude.ai | `anthropic` | AI 服务 |

**deepseek 不在 AI 服务组** —— 落到 `geolocation-cn` 直连。
这不是 bug：`geosite/category-ai-chat-!cn` / `openai` / `anthropic`
三个规则集都不含 deepseek 域名。它本就是国内服务（IP `116.205.40.x`），直连最快。

若要代理 deepseek，加一条规则并置于 `geolocation-cn` 之前：

```yaml
- DOMAIN-SUFFIX,deepseek.com,AI 服务
```

---

## 九、踩坑清单

### 客户端与内核

- **rule-provider 是懒加载的** —— `mihomo -t` 只校验语法不下载，
  启动 20ms 就 complete 属正常。验证必须启动内核等实际匹配
- 此版本**没有** `/providers/rules/<name>/update` 端点（404）
- **`/providers/rules` 不返回规则内容** —— `updatedAt` 有值但 `rules` 是空数组，别指望它
- **分清两种失败原因** —— `dns resolve failed` 是测试配置 DNS 太简略，
  `i/o timeout` 才是真被墙
- **内核自动注入内建组 `GLOBAL`** —— 核对组数时排除它。
  注意与覆写里手工定义的同名组是两回事
- **空 url-test 组会填 `COMPATIBLE` 占位符** —— 不致命，但该分流不可用。
  「其他国家」改用 `select` + `proxies: [DIRECT]` 规避
- **测试端口不能撞** —— `mixed-port` 与 `external-controller` 设成同值时，
  代理监听被控制器占掉，所有探测连接静默失败。
  用 19200(mixed) / 19201(http) / 19299(controller) / 19202(dns)
- **规则集拉取失败不等于地址错误** —— 94 个并发下载会有 16 个报 EOF，
  逐个 curl 全是 200，纯属 CDN 限流，重启内核即补齐

### YAML 语法

- **`rules` 里带空格的组名绝不能加引号** —— mihomo 按逗号裸切分不剥引号，
  `RULE-SET,x,"🌍 非中国"` 会找不到组。
  生成器里 `q()` 用于 `proxy-groups` 的 `name`（需要引号），`rule()` 不用
- **YAML 注释里不要写正则反斜杠** —— `\b` 会被当转义序列，
  报 `unacceptable character #x0008`。用文字表述「单词边界」
- **正则字符类里不能写裸 emoji** —— 用码点转义（`\U0001F000-\U0001FAFF`）

### 规则集

- **ipcidr 规则集走 `geoip/` 目录且文件名去掉 `-ip` 后缀** ——
  `google-ip` → `geoip/google.mrs`。按 geosite 拼会 404
- **`all_rulesets()` 必须收齐所有引用来源** —— 只遍历 `RULE_ORDER` 会漏掉
  前置块引用的 `category-games-cn`，导致 provider 段不声明它 → **静默失效**。
  且遍历时不能用 `break`（首条通常是注释行）
- **同一规则集只能在一处声明** —— 同时进 `RULE_ORDER` 和 `PRE_GAME_BLOCK`
  会输出两条重复规则
- **锚点机制表达不了「早于整组」** —— 挂 `steam-cn` 只保证在它之前，
  而其后还有 7 个游戏 RULE-SET。必须用 `PRE_GAME_BLOCK`
- **目标组方向不能靠推断** —— `category-games-cn` 漏加 `RULE_TARGET_OVERRIDES`
  会落到 `Steam`（代理）而非 `国内服务`（直连），语义完全相反
- **别靠 HTTP 逐个试错验证资源可达性** —— CDN 限流误判率极高
  （图标那次 33 个里误判 20 个）。拉 GitHub API 目录清单本地比对

### 结构与验证

- **`include-all` 只吸入节点，不吸入策略组** —— 引组必须显式写 `proxies`
- **代理组数组顺序只影响 UI 显示，不参与匹配** —— 只有 `rules` 顺序有意义
- **`REGION_GROUPS = REGIONS + [OTHER_REGION]`** —— 脚本引用地区组清单要用
  `REGION_GROUPS`，用 `REGIONS` 会漏检「其他国家」
  （`nest_check.py` 曾写死 6 而漏掉，已修）
- **校验脚本的「预期值」本身也可能是错的** —— 曾把 Los Angeles（美国城市）
  写进狮城组排除词，导致标准美区节点被误判。
  写校验脚本时「预期值」和「实际值」都要经得起质疑
- **写校验脚本的两个细节** —— 正则键名含 `!`/`-`/`@`，字符类要用
  `[A-Za-z0-9._@!+-]+`；取 YAML 块边界别用 `find("\n  ")`
  （紧邻下一行就命中，块会被截断），用 `re.search(r"\n  \S", rest)`

### 别去解析 .mrs

zstd 压缩 + succinct trie，域名**倒序存储**。
用 Node `zlib.zstdDecompressSync` 能解压出二进制，
但按「扫可打印字节再反转」提域名不可靠（试过，解出 `;.S<\` 之类的垃圾）。

**要判断规则集内容，一律走内核实测**，看 `core.log` 里：

```
[TCP] ... --> chat.deepseek.com:443 match RuleSet(geolocation-cn) using 国内服务[DIRECT]
```

需 `log-level: debug` 才输出，默认 info 级别没有。

### Python

- **隐式字符串拼接不能与函数调用混用** —— `r"a" + NB("X")` 换行接 `r"|b"`
  会 SyntaxError，必须每段都显式 `+`

### 资料库文档导出

- 资料库在线文档导出后是 **HTML 风格组件树，不是合法 XML**
  （标签带裸属性如 `readonly rowHeader`）。用 `xml.etree` 会 ParseError，
  正确做法是 `html.parser` 建树再递归渲染
- **`html.parser` 自动把标签名转小写** —— `BlockQuote` 变 `blockquote`，
  所有比较必须用小写，否则渲染静默返回空
- **文本会出现在开标签之后、子标签之前** —— 若节点分别存 `text` 和 `children`
  再拼接会丢失或错位（`<Paragraph><Mark bold>X</Mark> Y</Paragraph>` 变成 `YX`）。
  必须用 `parts` 列表按文档顺序混装
- **裸 `&` 会破坏解析** —— 需先
  `re.sub(r'&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)', '&amp;', raw)`

---

## 十、待办与可选优化

### 必做

- [ ] `override/1a13ae6610a.js`「全局DNS统一覆写（合并版）修改版」是
      `1a128f773c5` 的重复副本（`global: false`），建议删除避免混淆
- [ ] 仓库 `override/` 是配置根的副本，改完记得双向同步

### 可选优化

1. **补 uk/de/fr/ca/au 独立地区组** —— 官方 `REGION_PRESETS` 共 11 个地区，
   现为 6 + other。关键词表见下节。
   ⚠ 加了之后**必须同步改「其他国家」的 exclude**，否则节点消失
2. **GFW 兜底** —— 当前无 `ProxyGFWlist` 等价规则，
   可考虑加 `geosite/gfw.mrs` 或 `greatfire.mrs` 到「节点选择」
3. **空地区组降级** —— 部分订阅缺某地区节点（如狗子云无台湾），
   可考虑业务组引用空组时自动跳过。实测空组不会崩溃，可延后
4. **代理 deepseek** —— 见第八节，加一条 `DOMAIN-SUFFIX,deepseek.com,AI 服务`
5. **规则顺序可调** —— `RULE_ORDER` 表在 `rules.ts`，当前是原版顺序
6. **图标语义微调** —— 41 组用了 38 个不同图标，
   三处复用：AI（Gemini 归 AI 服务）、PayPal（支付 + 加密货币）、
   Scholar（谷歌学术 + 教育学术）

---

## 十一、SubBoost 上游信息

- 仓库 `github.com/SubBoost/subboost`（934 star / 170 fork / AGPL-3.0 / TypeScript）
- 官网 `subboost.org` · 文档 `docs.subboost.org`
- 当前版本 v2.9.0（2026-10-05），创建于 2026-06-15
- README：「内置 30 多个常用代理组和 2000 多条远程规则集」
  「节点筛选：可在分流组高级模式中按导入源、地区和自定义规则筛选节点」
- SubBoost full 模板默认排除 3 个模块：Gemini、谷歌学术、成人内容
  （生成器 `DEFAULT_OFF` 控制，要开就删对应项）

### 与 ACL4SSR 的差异

两者不是同一层东西：ACL4SSR 是 subconverter 的 `.ini` 规则描述，
SubBoost 是 TypeScript 实现的订阅转换器。

| 维度 | ACL4SSR Online Full | SubBoost full |
|---|---|---|
| 规则条数 | 33 | 90+ |
| 格式 | `.list` 文本 classical | `.mrs` 二进制（domain/ipcidr 严格分离） |
| 分组 | 29 | 36（full 启用 33） |
| 地区 url-test 组 | 6 个 | **完全没有** |
| GFW 兜底 | ProxyGFWlist → 节点选择 | 无，只有 geolocation-!cn |
| IP 规则 | 无 | 8 条独立 ipcidr，全部带 no-resolve |
| DNS/嗅探 | 不管 | 内置完整 fake-ip DNS + sniffer + geox-url |

### 为什么没有内置地区组（重要结论）

**不是遗漏，是 v2.5.0 主动移除的。** 证据链：

1. **v2.5.0 发行说明**：「移除筛选代理组，相关功能转移到分流代理组高级模式和自定义分流组」
2. **v2.4.0 确实有** `FilteredProxyGroup`（`types/filtered-proxy-group.ts`，792 字节），
   含 `regions: NodeRegion[]`、`sourceIds`、`includeRegex`/`excludeRegex`，
   注释写「筛选代理组（从节点池派生）」，配了增删改三个 action
3. **v2.5.0 起该文件直接删除**（v2.5.0/2.6.0/2.7.0 拉取均 404）
4. **内置模块表从头到尾没变** —— v2.4.0 与 main 都是 36 个模块，
   diff 只有类型别名提取和末尾空行两处无关改动。
   地区组从来不在模块表里，而是独立于模块表的第四类组
5. **能力没消失，只是换了入口** —— 现在的 `proxy-group-advanced.ts` 里有
   `REGION_PRESETS`（11 地区 + other）和 `matchesRegion()`，
   挂在「自定义分流组的高级模式」上

**移除理由**（分析，非官方明说）：

- **命名规范不可靠** —— 地区组本质是拿关键词猜节点归属。
  `REGION_PRESETS` 用 `includes()` 子串匹配，实测软肋明显：
  `US` 命中 Australia/Russia/Belarus，`TW` 命中 Network，`SG` 命中 Santiago。
  做成预置组等于把「猜错」变成开箱即有的错误，代价由用户承担；
  做成可选筛选，用户可按机场实际命名自行调 `includeRegex`/`excludeRegex`
- **配置体量与性能** —— 组数膨胀是被记录过的问题：
  v2.5.1 修过「节点选择默认包含自定义组导致套娃、预览卡顿」
- **定位收敛** —— SubBoost 主打「按业务/域名精确分流」，
  地区切换属「节点选择偏好」，不是分流能力

**与 ACL4SSR 的根本差异**：后者假定单一机场订阅、节点命名规范、场景单一，
才敢把地区组写死进核心配置。SubBoost 要处理多订阅混合 + 链式中转，假设不成立。

### REGION_PRESETS 关键词表

| id | 关键词 |
|---|---|
| us | 美国 / US / USA / United States / 洛杉矶 / 纽约 / 西雅图 |
| hk | 香港 / HK / Hong Kong / 港 |
| jp | 日本 / JP / Japan / 东京 / 大阪 |
| sg | 新加坡 / SG / Singapore / 狮城 |
| tw | 台湾 / TW / Taiwan / 台北 |
| kr | 韩国 / KR / Korea / 首尔 |
| uk | 英国 / UK / United Kingdom / London / 伦敦 |
| de | 德国 / DE / Germany / Frankfurt / 法兰克福 |
| fr | 法国 / FR / France / Paris / 巴黎 |
| ca | 加拿大 / CA / Canada / Toronto / 多伦多 |
| au | 澳大利亚 / AU / Australia / Sydney / 悉尼 |
| other | （空，实现为反向排除） |

### 图标

用 Qure 图标集（`Koolson/Qure@master/IconSet/Color`，347 个），
经 jsdelivr 镜像。组名已去 emoji，标识全交给 `icon` 属性。

**核对方法**：拉 GitHub API 目录清单拿权威名单，本地比对。
**别用 HTTP 逐个试错** —— jsdelivr 限流会把大量真实存在的资源报成 000/SSL EOF
（原 36 个图标里 12 个不存在，第一轮 HTTP 测试误判 20 个）。
清单缓存在 `reference/qure_names.txt`，核对脚本 `scripts/check_icons.py`。

关键替换：国内服务→`CN` · 私有网络→`Lock` · 非中国→`Global` ·
云服务→`Server`（清单无 Cloud）· 开发工具→`App_Store` ·
加密货币→`PayPal`（清单无币种图标）· 教育→`Scholar`。

---

## 十二、历史变更记录

| 日期 | 变更 |
|---|---|
| 10-13 | 定位 Bettbox 配置目录（`com.appshub\Bettbox`，与现客户端无关） |
| 10-14 | 审计「GPT写的」覆写（评分 7/10，发现 4 处暗伤）；复刻 SubBoost 覆写落地；补 7 个地区组（`\b` 版）；图标修正；组顺序调整；`\b` 词边界把 94 个误命中降到 0 |
| 10-14 晚 | 另一台机器完成 NB 正则、`PRE_GAME_BLOCK`、游戏区块、94/94 规则集内核实测 |
| 10-15 | 同步 NB 正则到本机生成器；`rules:` → `rules+:`；DNS 覆写补 Steam 四项 + 修 `default-nameserver` + `config.rules` 只留 workRules；Steam 商店规则提到 `category-games-cn` 之前；实测 deepseek 分流；建立版本库 |

### 「GPT写的」覆写审计结论（`1a129bbc284`，已停用）

评分 7/10，骨架干净但有暗伤：

1. **Henry_telegram 规则集 404** —— 上游 `HenryChiao/MIHOMO_YAMLS` 已无此文件。
   后果：电报流量不被捕获，靠 gfw 列表兜底
2. **rules 全量替换** —— 奈云订阅原本 3526 条规则被砍到 43 条
3. **filter 缩写误命中** —— `US` 匹配 Australia/Russia/Belarus（实测
   `Australia 01` 被划进美国组），`TW` 匹配 Network
4. **空地区组** —— 四个订阅各缺不同地区
5. **`exclude-type: direct` 无效** —— 该字段只认 provider 类型，静默忽略
6. **GLOBAL 组名撞 mihomo 内置语义**，且与「手动切换」功能重复

---

## 附：订阅列表

`1a0377776c2` TAGMeta（当前）· 奈云 · 良心云 · 狗子云 · 一元机场 ·
EdgeNova · Glados · L站99积分 · L站

各订阅地区分布差异大（狗子云台湾组为空、Glados 新加坡只有 1 个），
这是订阅本身节点构成所致，属正常。
