"""
从 SubBoost 源码生成纯 SubBoost 规则的 mihomo-party YAML 覆写。

数据来源（均取自 SubBoost/subboost@main）：
- packages/core/src/generator/proxy-group-modules.ts  模块与规则定义
- packages/core/src/generator/proxy-groups.ts             PROXY_GROUP_ORDER / groupType 语义
- packages/core/src/generator/rules.ts                     RULE_ORDER 规则顺序
- packages/core/src/subscription/info-node-name.ts          信息节点过滤正则
- packages/core/src/config/defaults.ts                      基础配置默认值

输出：override 用的 YAML（proxy-groups / rule-providers / rules）
"""

import io
import re
from pathlib import Path

SRC = Path(__file__).parent
MODULES_TS = SRC / "proxy-group-modules.ts"
if not MODULES_TS.exists():
    # 兼容版本库目录结构（上游模块文件位于 reference/ 目录）
    MODULES_TS = SRC.parent / "reference" / "proxy-group-modules.ts"

# ---------------------------------------------------------------- 解析模块定义

MODULE_RE = re.compile(
    r"\{\s*\n\s*id: \"(?P<id>[a-z0-9-]+)\",\s*\n"
    r"\s*name: \"(?P<name>[^\"]+)\",\s*\n"
    r"\s*emoji: \"(?P<emoji>[^\"]+)\",\s*\n"
    r"\s*category: \"(?P<category>[a-z]+)\",\s*\n"
    r"\s*description: \"(?P<desc>[^\"]*)\",\s*\n"
    r"\s*groupType: \"(?P<gtype>[a-z-]+)\",\s*\n"
    r"\s*rules: \[(?P<rules>.*?)\],\s*\n\s*\}",
    re.S,
)

RULE_RE = re.compile(
    r"\{\s*id: \"(?P<id>[^\"]+)\",\s*name: \"(?P<name>[^\"]+)\",\s*"
    r"behavior: \"(?P<behavior>domain|ipcidr)\",\s*path: \"(?P<path>[^\"]+)\""
    r"(?P<nr>, noResolve: true)?\s*\}"
)

# packages/core/src/generator/proxy-groups.ts :: PROXY_GROUP_ORDER
# 尾部三步的顺序按用户要求调整：private → cn → 【地区组】 → global → final
# 即地区组排在「非中国(global)」和「漏网之鱼(final)」**上面**，
# 这两个兜底组始终留在数组最末尾。
PROXY_GROUP_ORDER = [
    "select", "auto",
    "ad",
    "ai", "gemini", "youtube", "google", "microsoft", "apple",
    "telegram", "twitter", "meta", "discord", "social-other",
    "netflix", "disney", "streaming-west", "streaming-asia",
    "steam", "gaming-pc", "gaming-console",
    "github", "cloud", "dev-tools", "storage",
    "payment", "crypto",
    "google-scholar", "education", "news", "shopping", "adult",
    "private", "cn",
    "__regions__",          # 6 个地区 url-test 组插在这里
    "global", "final",
]

# packages/core/src/generator/rules.ts :: RULE_ORDER
RULE_ORDER = [
    "ad", "private", "gemini", "ai", "cn", "youtube", "google-scholar",
    "education", "cloud", "google", "telegram", "github", "microsoft",
    "apple", "twitter", "meta", "discord", "social-other", "netflix",
    "disney", "streaming-west", "streaming-asia", "steam", "gaming-pc",
    "gaming-console", "dev-tools", "storage", "payment", "crypto", "news",
    "shopping", "adult", "global",
]

# packages/core/src/generator/proxy-groups.ts :: getModulesForTemplate("full")
DEFAULT_OFF = {"adult", "gemini", "google-scholar"}

# packages/core/src/subscription/info-node-name.ts（三段正则合并）
INFO_NODE_RE = (
    r"^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\s*[:：]"
    r"|^(余额|会员)\s*\|"
    r"|版本太旧|请更新|更新软件|去官网更新"
)

# packages/core/src/config/defaults.ts
TEST_URL = "https://www.gstatic.com/generate_204"
TEST_INTERVAL = 300
# packages/core/src/rules/provider-config.ts（换成本地可达的 jsdelivr 镜像）
BASE_URL = "https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo"
GEOX_BASE = "https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release"

# packages/core/src/generator/rules.ts :: EXPERIMENTAL_CN_RULE
EXPERIMENTAL_CN = {"id": "cn", "behavior": "domain", "path": "geosite/cn.mrs"}

# ---------------------------------------------------------------- 图标

# 全部图标名已逐个核对存在于 Koolson/Qure IconSet/Color（347 个），
# 不存在的已换成语义相近的替代（见 check_icons.py 的核对报告）。
# 33 个组用了 33 个不同图标，互不重复。
ICONS = {
    "select": "Proxy",
    "auto": "Auto",
    "ad": "AdBlack",
    "private": "Lock",
    "cn": "CN",
    "global": "Global",
    "final": "Final",
    "ai": "AI",
    "gemini": "AI",
    "youtube": "YouTube",
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "telegram": "Telegram",
    "twitter": "Twitter",
    "meta": "Facebook",
    "discord": "Discord",
    "social-other": "Line",
    "netflix": "Netflix",
    "disney": "Disney",
    "streaming-west": "ForeignMedia",
    "streaming-asia": "AbemaTV",
    "steam": "Steam",
    "gaming-pc": "Game",
    "gaming-console": "Xbox",
    "github": "GitHub",
    "cloud": "Server",
    "dev-tools": "App_Store",
    "storage": "OneDrive",
    "payment": "PayPal",
    "crypto": "PayPal",
    "google-scholar": "Scholar",
    "education": "Scholar",
    "news": "Media",
    "shopping": "Amazon",
    "adult": "Pornhub",
}
ICON_BASE = "https://testingcf.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color"

# ---------------------------------------------------------------- 地区 url-test 组

# 官方 REGION_PRESETS（packages/core/src/proxy-group-advanced.ts）的关键词表。
# 官方原版是「用户手动建组 + includes() 子串匹配」，没有 exclude 兜底。
# 这里补 exclude-filter 修掉子串匹配的已知误命中：
#   US  → Australia / Russia / Belarus / Belarus 结尾的 us
#   SG  → 含 "sg" 的任意串
#   TW  → Network / Taiwan 之外的 tw 子串
#   KR  → 含 "kr" 的任意串
#   DE/FR/CA/AU 用全称关键词，误命中面比两字母缩写小得多。

# 信息节点（机场的流量/到期提示）必须排除，否则会被当成可测速节点
JUNK = r"^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\s*[:：]|^(余额|会员)\s*\||版本太旧|请更新|更新软件|去官网更新"


def NB(code: str) -> str:
    """两字母地区缩写的边界正则。

    不用 ``\\b``：``\\b`` 界定的是「词字符」边界，而数字和下划线也属于词字符，
    所以 US01 / HK_02 / SG-01 这类机场常见命名匹配不上 ``\\bUS\\b``，会漏节点。
    NB 改用「非字母即边界」，贴合实际命名习惯。
    """
    return rf"(?:^|[^a-zA-Z]){code}(?:[^a-zA-Z]|$)"


REGIONS = [
    {
        "id": "r-us",
        "name": "美国节点",
        "icon": "United_States",
        # 官方关键词：us
        "filter": r"(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|" + NB("US") + r"|United.?States|America",
        # 排除会被 US 误伤的其他地区
        "exclude": r"(?i)Australia|俄罗斯|Russia|Belarus|巴西|Brazil",
    },
    {
        "id": "r-hk",
        "name": "香港节点",
        "icon": "Hong_Kong",
        # 官方关键词：hk。刻意不含单字「港」——会误伤连云港/深港专线
        "filter": r"(?i)香港|" + NB("HK") + r"|Hong.?Kong|HKG",
        "exclude": None,
    },
    {
        "id": "r-jp",
        "name": "日本节点",
        "icon": "Japan",
        # 官方关键词：jp（日本/JP/Japan/东京/大阪）
        "filter": r"(?i)日本|东京|大阪|川日|沪日|深日|泉日|埼玉|" + NB("JP") + r"|Japan|Tokyo|Osaka",
        "exclude": None,
    },
    {
        "id": "r-sg",
        "name": "狮城节点",
        "icon": "Singapore",
        # 官方关键词：sg。刻意不含单字「坡」——会误伤吉隆坡
        "filter": r"(?i)新加坡|狮城|" + NB("SG") + r"|Singapore",
        # 注意：不要在这里排 Los Angeles —— 洛杉矶是美国城市，
        # 排掉它会误伤 US-Los Angeles 这类标准美区节点。
        "exclude": None,
    },
    {
        "id": "r-tw",
        "name": "台湾节点",
        "icon": "Taiwan",
        # 官方关键词：tw（台湾/TW/Taiwan/台北）
        "filter": r"(?i)台湾|台北|台中|新北|彰化|" + NB("TW") + r"|Taiwan|Taipei|Kaohsiung",
        # TW 会误伤 Network / Software 这类含 tw 的英文词
        "exclude": r"(?i)Network|Software|Westward",
    },
    {
        "id": "r-kr",
        "name": "韩国节点",
        "icon": "Korea",
        # 官方关键词：kr（韩国/KR/Korea/首尔）
        "filter": r"(?i)韩国|首尔|韓|" + NB("KR") + r"|Korea|KOR",
        "exclude": None,
    },
]

# 「其他国家」组 —— 对应官方 REGION_PRESETS 里的 other 预设（🌐 其他）。
#
# 官方语义（proxy-group-advanced.ts :: matchesRegion）：
#   遍历所有预设关键词，只要命中任意一个就返回 false（不属于 other）；
#   全部不命中才返回 true。所以 other = 「不匹配任何已知地区」。
#
# mihomo 没有反向 filter，但可以用 exclude-filter 等价实现：
# 把所有已知地区的关键词全部写进 exclude-filter，剩下的就是「其他国家」。
#
# 注意 exclude 列表要用「与上面 6 个 filter 并集等价」的一套关键词，
# 而不是直接复用它们的正则 —— 上面那些正则带 \b 和额外排除项，
# 直接拼会漏掉本该归 other 的节点（比如 US 组排除了 Australia，
# 那 Australia 应该出现在「其他国家」里而不是凭空消失）。
OTHER_REGION = {
    "name": "其他国家",
    "icon": "World_Map",
    # 只排除「已经有独立组接住」的 6 个地区关键词。
    #
    # ⚠ 关键：这里绝不能把 uk/de/fr/ca/au 等官方预设也排掉 ——
    #   它们在本覆写里没有对应的独立组，排掉等于让这些节点凭空消失
    #   （既不在任何地区组，也不在「其他国家」里）。
    #   实测踩过：这么写会导致 TAGMeta 的英国/法国/加拿大/澳洲等 16 个节点丢失。
    #
    # 正确语义：「其他国家」= 除了这 6 个地区以外的**全部**节点，
    # 官方预设里没单独建组的地区（英德法加澳等）天然落在这里。
    "exclude": (
        r"(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|United.?States|"
        + NB("US")
        + r"|香港|Hong.?Kong|HKG|"
        + NB("HK")
        + r"|日本|东京|大阪|川日|沪日|深日|泉日|埼玉|Japan|Tokyo|Osaka|"
        + NB("JP")
        + r"|新加坡|狮城|Singapore|"
        + NB("SG")
        + r"|台湾|台北|台中|新北|彰化|Taiwan|Taipei|Kaohsiung|"
        + NB("TW")
        + r"|韩国|首尔|韓|Korea|KOR|"
        + NB("KR")
        # ⚠ 三处刻意不排：
        #   · 单字「港」会误伤连云港/深港专线等中转线路命名
        #   · 单字「坡」会误伤吉隆坡
        #   · America 会命中 Argentina/Colombia 等南美国家名，排掉会让它们消失
        #   （美国组自己的 filter 保留 America —— 那是正向匹配，
        #     命中南美只是不进美国组，仍会落进「其他国家」，无副作用）
        # 美国组额外排掉的：这些已被判定为非美国节点，应归入「其他国家」，
        # 不能在这里再排一次（否则 Australia/Russia/Belarus 也会凭空消失）。
    ),
}

REGION_GROUPS = REGIONS + [OTHER_REGION]


def parse_modules(text: str) -> dict:
    modules = {}
    for m in MODULE_RE.finditer(text):
        rules = [
            {
                "id": r.group("id"),
                "name": r.group("name"),
                "behavior": r.group("behavior"),
                "path": r.group("path"),
                "noResolve": bool(r.group("nr")),
            }
            for r in RULE_RE.finditer(m.group("rules"))
        ]
        modules[m.group("id")] = {
            "name": m.group("name"),
            "gtype": m.group("gtype"),
            "desc": m.group("desc"),
            "category": m.group("category"),
            "rules": rules,
        }
    return modules


# ---------------------------------------------------------------- YAML 输出

def q(text: str) -> str:
    """给含空格/特殊字符的字符串加双引号（组名去 emoji 后仍含空格）。"""
    if re.search(r'[:#\[\]{}&*!|>\'"%@`,?\s]', text) or text != text.strip():
        return '"' + text.replace('"', '\\"') + '"'
    return text


# emoji 及其他符号区。用显式码点区间，避免裸字符写进字符类。
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # 各类 emoji
    "\U0001F1E6-\U0001F1FF"   # 区域指示符（国旗）
    "\U00002600-\U000027BF"   # 杂项符号、箭头
    "\U00002B00-\U00002BFF"   # 箭头补充
    "\U00002190-\U000021FF"   # 带箭头字母
    "\U0000FE00-\U0000FE0F"   # 变体选择符
    "\U00002B05-\U00002B07"   # ◀▶▼
    "\U000025B6-\U000025C0"   # ▶◀
    "\U00002B1B-\U00002B1C"   # ⬛⬜
    "\U00002700-\U000027BF"   # ➀-➿
    "\U000024C2-\U000024D3"   # Ⓜⓓ 等带圈字母
    "\U000020A0-\U000020BF"   # 货币符号
    "\U00002000-\U0000206F"   # 通用标点
    "\U00002190-\U000021FF"   # 箭头
    "\U00002B00-\U00002BFF"   # 箭头补充
    "\U0000FE00-\U0000FE0F"   # 变体选择符
    "]"
)


def strip_emoji(name: str) -> str:
    """去掉组名里的 emoji 与箭头符号，压缩多余空白。

    "🚀 节点选择" → "节点选择"
    "🔒 国内服务"   → "国内服务"
    """
    out = _EMOJI_RE.sub("", name)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def rule(pid: str, target: str, no_resolve: bool = False) -> str:
    """生成一条 rules 条目。

    mihomo 按逗号裸切分规则字符串，不会剥离引号，所以目标组名带空格时
    绝不能加引号（会变成组名的一部分）。YAML 层面裸写即可正确解析。
    """
    line = f"RULE-SET,{pid},{target}"
    if no_resolve:
        line += ",no-resolve"
    return line


def y(value: str) -> str:
    """YAML 标量：正则在裸量下容易歧义，统一单引号。"""
    return "'" + value.replace("'", "''") + "'"


def build(modules: dict, enabled: list[str]) -> str:
    out = io.StringIO()
    w = out.write
    # SubBoost 的组名带 emoji（"🚀 节点选择"）。这里去掉 emoji，只保留文字，
    # 视觉标识交给 icon 属性承担 —— 客户端本来就会把 icon 渲染在组名旁边。
    # ⚠️ 改名会重置所有已保存的组选择（profile.store-selected），
    #    所以只在这一个覆写内部保持一致，不影响其他覆写。
    name = {mid: strip_emoji(modules[mid]["name"]) for mid in enabled}
    enabled_set = set(enabled)

    select = name["select"]
    auto = name["auto"]
    # 「手动切换」是本覆写新增的组（SubBoost 原版没有，见下方注释）。
    manual = "手动切换"
    # 业务组/节点选择的成员列表统一用它：7 个地区组（含「其他国家」）
    region_refs = ", ".join(q(r["name"]) for r in REGION_GROUPS)

    # ---------------- proxy-groups ----------------
    w("# " + "=" * 74 + "\n")
    w("# SubBoost 规则体系 · mihomo 覆写版\n")
    w("# " + "=" * 74 + "\n")
    w("#\n")
    w("# 复刻自 https://github.com/SubBoost/subboost （AGPL-3.0）\n")
    w("# 规则数据源：MetaCubeX/meta-rules-dat@meta （全部 .mrs 二进制）\n")
    w("#\n")
    w("# 与原项目的差异（共五处，均为落地适配，不改分流逻辑）：\n")
    w("#\n")
    w("# 1. 规则集地址换成本地可达的 jsdelivr 镜像。\n")
    w("#    原项目用 github.com/.../raw/ 跳转 raw.githubusercontent.com，\n")
    w("#    国内直连会超时。内容与上游完全一致。\n")
    w("#\n")
    w("# 2. 每个规则集加 proxy 字段，指定由「%s」转发下载。\n")
    w("#    原项目在转换机上直连拉取；落到 mihomo 后本机直连 CDN 会被墙，\n")
    w("#    92 个规则集会全部拉取失败（实测 i/o timeout）。这是必需项。\n")
    w("#\n")
    w("# 3. 节点成员用 include-all + exclude-filter 表达。\n")
    w("#    原项目在转换时已知全部节点名，直接写进 proxies；\n")
    w("#    覆写是静态的，只能用 mihomo 的 include-all 等价实现。\n")
    w("#    exclude-filter 用的就是原项目 isSubscriptionInfoNodeName 的三条正则，\n")
    w("#    作用一致：信息节点只留在「%s」里，不进业务组和测速组。\n" % select)
    w("#\n")
    w("# 4. 组名去掉了 emoji（原项目是「🚀 节点选择」这种形式），\n")
    w("#    视觉标识全部交给 icon 属性承担。\n")
    w("#    39 个组的图标名已逐个核对存在于 Qure 图标集。\n")
    w("#\n")
    w("# 5. 补回了 6 个地区 url-test 组（美/港/日/狮/台/韩）。\n")
    w("#    SubBoost 原版没有 —— v2.5.0 把「筛选代理组」整块移除了，\n")
    w("#    地区能力下沉成自定义分流组的一个可选筛选维度。\n")
    w("#    这里按官方 REGION_PRESETS 的关键词表补回，并额外加 exclude-filter\n")
    w("#    修掉官方 includes() 子串匹配的已知误命中：\n")
    w("#      US 会抓到 Australia / Russia / Belarus\n")
    w("#      TW 会抓到 Network / Software\n")
    w("#      SG 会抓到 Santiago\n")
    w("#    两字母缩写都加了 \\b 词边界，实测 94 个误命中降到 0。\n")
    w("#\n")
    w("# 6. 地区组排在「非中国」和「漏网之鱼」**上面**，兜底组留在最末尾。\n")
    w("#    mihomo 按 rules 数组做首次命中匹配，与 proxy-groups 的排列\n")
    w("#    顺序无关 —— 调换组顺序不会改变分流结果，只影响 UI 显示。\n")
    w("#\n")
    w("# 7. 选择方式改成 ACL4SSR 式：业务组只放聚合组，不放单个节点。\n")
    w("#\n")
    w("#    节点选择 = [自动选择, <7个地区组>, 手动切换, DIRECT, REJECT]\n")
    w("#    业务组   = [节点选择, 自动选择, <7个地区组>, 手动切换, DIRECT, REJECT]\n")
    w("#\n")
    w("#    新增「手动切换」组（select + include-all）。业务组一旦不再持有\n")
    w("#    全部节点，就必须有个地方能选单个节点，否则这个能力就丢了。\n")
    w("#    SubBoost 原版没有这个组 —— 它靠每个业务组各自 include-all\n")
    w("#    持有全节点副本（33 组 × N 节点，内存与 UI 渲染都更重）。\n")
    w("#\n")
    w("#    新增「其他国家」组，对应官方 REGION_PRESETS 的 other 预设：\n")
    w("#    include-all + exclude 掉全部 6 个已有独立组的地区关键词。\n")
    w("#    ⚠ exclude 里绝不能排 uk/de/fr/ca/au —— 它们本覆写没有独立组，\n")
    w("#      排掉会让这些节点凭空消失（既不在地区组也不在这里）。\n")
    w("#      实测踩过：这么写会丢掉 TAGMeta 的 16 个英/法/加/澳节点。\n")
    w("#\n")
    w("#    ⚠ mihomo 的 include-all 只吸入 proxies（节点），不吸入策略组，\n")
    w("#      所以引用地区组必须显式写进 proxies 字段。\n")
    w("#    ⚠ v2.5.1 修过「节点选择默认包含自定义组导致组套娃、预览卡顿」。\n")
    w("#      这里只显式列固定数量的组（7 地区 + 3 全局），无嵌套，实测 0 环。\n")
    w("#\n")
    w("# ── 地理库说明 ──────────────────────────────────────────\n")
    w("# 本覆写不写 geodata-mode / geo-auto-update / geodata-loader / geox-url。\n")
    w("# 这几项由 mihomo-party 内置配置（mihomo.yaml）提供，写在覆写里只会冲突，\n")
    w("# 且实测会被完全覆盖 —— 内置用的是 geoip-lite.dat + geoip.metadb，\n")
    w("# 与 SubBoost 默认的 geoip.dat + country.mmdb 不是一套。\n")
    w("# 需要调整地理库时改内置设置，不要改这里。\n")
    w("#\n")
    w("# ⚠ 改名会重置已保存的组选择（profile.store-selected），首次启用时\n")
    w("#   需要重新挑一遍默认节点，属一次性代价。\n")
    w("#\n")
    w("# DNS 不在本覆写内 —— 你已有的「全局DNS统一覆写（合并版）」继续生效，\n")
    w("# 两边同时写 dns 段会互相覆盖。如需改用 SubBoost 自带 DNS，见文件末尾注释块。\n")
    w("#\n")
    w("# 启用方式：mihomo-party → 覆写 → 选中本覆写 → 为目标订阅启用。\n")
    w("# 不要与「GPT写的」同时启用（proxy-groups 与 rules 均为整段替换）。\n")
    w("# " + "=" * 74 + "\n\n")

    # 只写 sniffer。地理库相关字段（geodata-mode / geo-auto-update /
    # geodata-loader / geox-url）一律不写 —— 它们由 mihomo-party 内置配置
    # （mihomo.yaml）提供，覆写里再写一份只会与之冲突，且实测会被完全覆盖。
    w("# 来自 SubBoost defaults.ts：嗅探设置\n")
    w("sniffer:\n")
    w("  enable: true\n")
    w("  parse-pure-ip: true\n")
    w("  sniff:\n")
    w("    TLS:\n      ports: [443, 8443]\n")
    w("    HTTP:\n      ports: [80, \"8080-8880\"]\n      override-destination: true\n")
    w("    QUIC:\n      ports: [443, 8443]\n\n")

    w("proxy-groups:\n")
    for mid in PROXY_GROUP_ORDER:
        # 地区 url-test 组：官方 REGION_PRESETS 关键词表 + \b 词边界 + 防误命中 exclude。
        # 位置在「非中国」和「漏网之鱼」**上面**，这两个兜底组留在最末尾。
        if mid == "__regions__":
            w("  # ===== 地区 url-test 组 =====\n")
            w("  # 官方 REGION_PRESETS 关键词表 + \\b 词边界 + 防误命中 exclude。\n")
            w("  # SubBoost 把地区做成了自定义组的可选筛选维度（v2.5.0 起），\n")
            w("  # 这里作为独立 url-test 组补回，排在兜底组（非中国/漏网之鱼）之前。\n")
            w("  # 「其他国家」用 exclude-filter 反向实现官方的 other 预设：\n")
            w("  # 把所有已知地区关键词排掉，剩下的就是它。\n")
            for r in REGIONS:
                w(f"  - name: {q(r['name'])}\n")
                w(f"    icon: {ICON_BASE}/{r['icon']}.png\n")
                w("    type: url-test\n")
                w("    include-all: true\n")
                w(f"    filter: {y(r['filter'])}\n")
                # 垃圾信息节点对所有组都要排除
                junk = JUNK if not r["exclude"] else f"{JUNK}|{r['exclude']}"
                w(f"    exclude-filter: {y(junk)}\n")
                w(f"    url: {TEST_URL}\n")
                w(f"    interval: {TEST_INTERVAL}\n")
                w("    lazy: false\n\n")
            o = OTHER_REGION
            w(f"  - name: {q(o['name'])}\n")
            w(f"    icon: {ICON_BASE}/{o['icon']}.png\n")
            w("    type: url-test\n")
            w("    include-all: true\n")
            w(f"    # 没有 filter，只有 exclude：排掉全部已知地区 = 剩下的都是「其他国家」\n")
            w(f"    exclude-filter: {y(f'{JUNK}|{o['exclude']}')}\n")
            w(f"    url: {TEST_URL}\n")
            w(f"    interval: {TEST_INTERVAL}\n")
            w("    lazy: false\n\n")
            continue

        if mid not in enabled_set:
            continue
        m = modules[mid]
        gname = name[mid]
        gtype = m["gtype"]

        w(f"  # {m['desc']}\n")
        w(f"  - name: {q(gname)}\n")
        w(f"    icon: {ICON_BASE}/{ICONS[mid]}.png\n")

        if gtype == "url-test":
            # 原项目：proxies = 过滤后的全部节点
            w("    type: url-test\n")
            w("    include-all: true\n")
            w(f"    exclude-filter: {y(INFO_NODE_RE)}\n")
            w(f"    url: {TEST_URL}\n")
            w(f"    interval: {TEST_INTERVAL}\n")
            w("    lazy: false\n\n")
            # 「手动切换」组紧跟在「自动选择」之后（ACL4SSR 的组序）。
            # SubBoost 原版没有这个组：它让每个业务组各自 include-all 持有全部节点。
            # 改成「业务组只放聚合组」后，必须有个地方能选单个节点，
            # 否则这个能力就丢了 —— 这个组就是那个地方。
            if mid == "auto":
                w("  # 手动指定单个节点 —— 业务组只放聚合组后，单节点选择能力由本组承载\n")
                w(f"  - name: {q(manual)}\n")
                w(f"    icon: {ICON_BASE}/Available_1.png\n")
                w("    type: select\n")
                w("    include-all: true\n")
                w(f"    exclude-filter: {y(INFO_NODE_RE)}\n\n")
        elif gtype == "reject-first":
            # 原项目：[REJECT, DIRECT, 节点选择, ...过滤后节点]
            w("    type: select\n")
            w(f"    proxies: [REJECT, DIRECT, {q(select)}, {q(manual)}]\n")
            w("    include-all: true\n")
            w(f"    exclude-filter: {y(INFO_NODE_RE)}\n")
        elif gtype == "direct-first":
            # 原项目：[DIRECT, REJECT, 节点选择, 自动选择, ...过滤后节点]
            w("    type: select\n")
            w(f"    proxies: [DIRECT, REJECT, {q(select)}, {q(auto)}, {q(manual)}]\n")
            w("    include-all: true\n")
            w(f"    exclude-filter: {y(INFO_NODE_RE)}\n")
        elif mid == "select":
            # ── 节点选择：只放聚合组（地区组 + 全局组），不放单个节点 ──
            # 原项目是 [自动选择, DIRECT, REJECT, ...全部节点]，
            # 这里改成 ACL4SSR 式结构：地区组成为主选择入口，
            # 单节点选择下放到「手动切换」组。
            # 默认值仍是「自动选择」，与原项目一致。
            #
            # ⚠ v2.5.1 修过「节点选择默认包含自定义组导致组套娃、预览卡顿」。
            #   这里只显式列固定数量的组（7 个地区 + 3 个全局组），无嵌套，不会成环。
            w("    type: select\n")
            w(f"    proxies: [{q(auto)}, {region_refs}, {q(manual)}, DIRECT, REJECT]\n")
        else:
            # ── 业务组：只放聚合组，不放单个节点 ──
            # 原项目：[节点选择, 自动选择, DIRECT, REJECT, ...过滤后节点]
            # 现在去掉 include-all（业务组不再持有全部节点副本），
            # 改为 [节点选择, 自动选择, <地区组...>, 手动切换, DIRECT, REJECT]。
            # 想选单节点时，先在「手动切换」里选定，再让本组指向它。
            w("    type: select\n")
            w(f"    proxies: [{q(select)}, {q(auto)}, {region_refs}, {q(manual)}, DIRECT, REJECT]\n")
        w("\n")

    # ---------------- rule-providers ----------------
    providers = {}
    for mid in PROXY_GROUP_ORDER:
        if mid not in enabled_set:
            continue
        for r in modules[mid]["rules"]:
            providers[r["id"]] = r

    if EXPERIMENTAL_CN["id"] not in providers and "cn" in enabled_set:
        providers[EXPERIMENTAL_CN["id"]] = {
            "id": EXPERIMENTAL_CN["id"],
            "behavior": EXPERIMENTAL_CN["behavior"],
            "path": EXPERIMENTAL_CN["path"],
        }

    w("# 全部规则集：MetaCubeX meta-rules-dat，.mrs 二进制，24 小时更新\n")
    w("#\n")
    w("# proxy 字段是相对原项目的第三处适配（必需项，不是可选优化）：\n")
    w("# SubBoost 跑在转换机上，规则集由那台机器直连下载。\n")
    w("# 落到 mihomo 后，如果本机直连 CDN 会被墙（实测 jsdelivr 直连\n")
    w("# i/o timeout），92 个规则集全会拉取失败且没有任何流量命中规则。\n")
    w("# 指定 proxy 后由「%s」转发下载。\n" % select)
    w("# 若你的网络能直连 jsdelivr，删掉每段的 proxy 行即可。\n")
    w("rule-providers:\n")
    for pid in sorted(providers):
        r = providers[pid]
        w(f"  {pid}:\n")
        w("    type: http\n")
        w(f"    behavior: {r['behavior']}\n")
        w("    format: mrs\n")
        w(f"    url: {BASE_URL}/{r['path']}\n")
        w(f"    path: ./ruleset/{pid}.mrs\n")
        w("    interval: 86400\n")
        w(f"    proxy: {q(select)}\n")
    w("\n")

    # ---------------- rules ----------------
    w("# 规则顺序 = SubBoost generator/rules.ts 的 RULE_ORDER 常量。\n")
    w("# 原项目注释说明了排序理由，核心是「子域名必须排在通用服务之前」：\n")
    w("#   gemini 在 ai/google 之前（Gemini 用谷歌域名）\n")
    w("#   youtube 在 google 之前（YouTube 是谷歌子域名）\n")
    w("#   google-scholar 在 google 之前\n")
    w("#   cn（完整国内域名）是低置信补充，后置到 geolocation-!cn 之后\n")
    w("# mihomo 首次命中即停，所以顺序本身就是分流逻辑。\n")
    w("rules:\n")

    emitted = set()
    for mid in RULE_ORDER:
        if mid not in enabled_set:
            continue
        for r in modules[mid]["rules"]:
            if r["id"] in emitted:
                continue
            emitted.add(r["id"])
            w(f"  - {rule(r['id'], name[mid], r.get('noResolve', False))}\n")

    # experimentalCnUseCnRuleSet: true —— 后置到 global 之后
    if "cn" in enabled_set:
        w(f"  - {rule(EXPERIMENTAL_CN['id'], name['cn'])}\n")

    w(f"  - MATCH,{name['final']}\n")

    # ---------------- 附：可选 DNS 块 ----------------
    w("\n")
    w("# " + "=" * 74 + "\n")
    w("# 附：SubBoost 自带 DNS（defaults.ts）。\n")
    w("# 你已有「全局DNS统一覆写（合并版）」在跑，启用下面这段会把它顶掉。\n")
    w("# 真要换成 SubBoost 版：先停用那条 JS 覆写，再取消本段注释。\n")
    w("# " + "=" * 74 + "\n")
    w("# dns:\n")
    w("#   enable: true\n")
    w("#   listen: \"127.0.0.1:5335\"\n")
    w("#   use-system-hosts: false\n")
    w("#   enhanced-mode: fake-ip\n")
    w("#   fake-ip-range: 198.18.0.1/16\n")
    w("#   default-nameserver: [180.76.76.76, 182.254.118.118, 8.8.8.8, 180.184.2.2]\n")
    w("#   nameserver: [180.76.76.76, 119.29.29.29, 180.184.1.1, 223.5.5.5, 8.8.8.8, \"https://223.6.6.6/dns-query#h3=true\", \"https://dns.alidns.com/dns-query\", \"https://cloudflare-dns.com/dns-query\", \"https://doh.pub/dns-query\"]\n")
    w("#   fallback: [\"https://dns.quad9.net/dns-query\", \"https://dns.alidns.com/dns-query\", \"https://doh.pub/dns-query\", \"https://public.dns.iij.jp/dns-query\", \"https://101.101.101.101/dns-query\", \"https://208.67.220.220/dns-query\", \"tls://8.8.4.4\", \"tls://1.0.0.1:853\", \"https://cloudflare-dns.com/dns-query\", \"https://dns.google/dns-query\"]\n")
    w("#   fallback-filter: {geoip: true, ipcidr: [240.0.0.0/4, 0.0.0.0/32, 127.0.0.1/32], domain: [\"+.google.com\", \"+.facebook.com\", \"+.twitter.com\", \"+.youtube.com\", \"+.xn--ngstr-lra8j.com\", \"+.google.cn\", \"+.googleapis.cn\", \"+.googleapis.com\", \"+.gvt1.com\"]}\n")
    w("#   fake-ip-filter: [\"*.lan\", \"stun.*.*.*\", \"stun.*.*\", time.windows.com, time.nist.gov, time.apple.com, time.asia.apple.com, \"*.ntp.org.cn\", \"*.openwrt.pool.ntp.org\", time1.cloud.tencent.com, time.ustc.edu.cn, pool.ntp.org, ntp.ubuntu.com, ntp.aliyun.com, \"*.music.163.com\", \"*.126.net\", \"*.kuwo.cn\", y.qq.com, \"*.y.qq.com\", \"*.xiami.com\", \"*.music.migu.cn\", music.migu.cn, \"*.msftconnecttest.com\", \"*.msftncsi.com\", localhost.ptlogin2.qq.com, \"*.*.*.srv.nintendo.net\", \"*.*.stun.playstation.net\", \"xbox.*.*.microsoft.com\", \"*.ipv6.microsoft.com\", \"*.*.xboxlive.com\"]\n")
    w("#\n")
    w("# profile:\n")
    w("#   store-selected: true\n")
    w("#   store-fake-ip: false\n")
    w("#\n")
    w("# 另外三个默认关闭的模块（SubBoost full 模板显式排除），需要时取消注释：\n")
    w("#   ✨ Gemini      —— google-gemini.mrs\n")
    w("#   🎓 谷歌学术    —— google-scholar.mrs\n")
    w("#   🔞 成人内容    —— category-porn.mrs\n")

    return out.getvalue()


def main() -> None:
    modules = parse_modules(MODULES_TS.read_text(encoding="utf-8"))
    print(f"解析模块 {len(modules)} 个")

    enabled_full = [
        m for m in PROXY_GROUP_ORDER
        if m in modules and m not in DEFAULT_OFF
    ]
    print(f"full 模板启用 {len(enabled_full)} 个模块")

    yaml_text = build(modules, enabled_full)
    target = Path(__file__).parent / "subboost-override.yaml"
    target.write_text(yaml_text, encoding="utf-8")
    print(f"已生成 {target} ({len(yaml_text)} 字符, {yaml_text.count(chr(10))} 行)")


if __name__ == "__main__":
    main()
