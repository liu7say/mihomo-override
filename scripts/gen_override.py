"""
==============================================================================
SubBoost 规则体系 · 全合一跨端覆写配置生成器
==============================================================================

【核心功能】
从 SubBoost 规则定义与本地配置中，自动化构建生成适用于 Clash Party、Flclash、
bettbox 等 Mihomo (Clash.Meta) 内核客户端的覆写产物。

【产物多档位输出 (Minimal / Standard / Full)】
1. override/js/customSubBoost.{minimal,standard,full}.js (主力推荐 · 本地自用 All-in-One 覆写):
   - 彻底整合 DNS 统一治理 + 节点清洗引擎 + 策略组与规则集按场景分流
   - 注入个人私有内网工作配置，受 .gitignore 严密隔离保护
2. override/example/customSubBoost.{minimal,standard,full}.example.js (公开脱敏示例模板):
   - 永不包含个人敏感配置，供 Git 追踪与社区分享
3. override/yaml/customSubBoost.{minimal,standard,full}.yaml (双轨备用 · 纯 YAML 覆写):
   - 遵循 rules+: 追加语义，供偏好传统多覆写模式的用户使用

【设计哲学与铁律】
- Good Taste: 数据结构与渲染引擎彻底分离；同一套数据源，同时产出 JS 与 YAML。
- Never break userspace: 全量防御性空安全检查；向后兼容 7 大地区组与游戏直连区块。
- 无注释即垃圾代码: 每一段正则、每一个策略组决策均配有详尽中文注释。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 确保在 Windows 控制台环境下输出 UTF-8，防止 GBK 编码下 Unicode 符号崩溃
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================================
# 第一部分：路径常量定义与环境适配
# ============================================================================

# 当前脚本所在目录 (scripts/)
HERE = Path(__file__).resolve().parent

# 项目根目录 (mihomo-override/)
REPO_ROOT = HERE.parent

# 上游模块源码文件（位于 reference/ 目录）
MODULES_TS = REPO_ROOT / "reference" / "proxy-group-modules.ts"
if not MODULES_TS.exists():
    fallback_ts = HERE / "proxy-group-modules.ts"
    if fallback_ts.exists():
        MODULES_TS = fallback_ts

# 声明式规则模块配置文件 (config/rules_profile.json)
RULES_PROFILE_JSON = REPO_ROOT / "config" / "rules_profile.json"

# 本地私有工作配置文件 (config/private_work.json, 已被 gitignore 隔离)
PRIVATE_WORK_JSON = REPO_ROOT / "config" / "private_work.json"

# 覆写产物输出目录及分层子目录
OVERRIDE_DIR = REPO_ROOT / "override"
OVERRIDE_JS_DIR = OVERRIDE_DIR / "js"             # 本地自用注入私有配置的 JS 脚本目录
OVERRIDE_EXAMPLE_DIR = OVERRIDE_DIR / "example"   # 公开脱敏样例模板目录 (Git 追踪)
OVERRIDE_YAML_DIR = OVERRIDE_DIR / "yaml"         # 双轨纯 YAML 覆写目录 (Git 追踪)

# 三大预设档位定义
PRESETS = {
    "minimal": {
        "name": "极简版 (~15 组)",
        "modules": {
            "select", "auto", "ad", "private", "cn", "global", "final", "__regions__",
            "ai",
        },
    },
    "standard": {
        "name": "标准版 (~22 组)",
        "modules": {
            "select", "auto", "ad", "private", "cn", "global", "final", "__regions__",
            "ai", "youtube", "google", "microsoft", "apple", "telegram", "twitter", "steam",
        },
    },
    "full": {
        "name": "全量版 (41 组)",
        "modules": None,  # None 代表从 rules_profile.json 加载全部启用模块 (26 业务组)
    },
}


def load_private_work_config() -> dict | None:
    """读取本地私有工作配置（若文件不存在则返回 None）。"""
    if PRIVATE_WORK_JSON.exists():
        try:
            data = json.loads(PRIVATE_WORK_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[!] 读取本地私有配置 config/private_work.json 失败: {e}")
    return None


# ============================================================================
# 第二部分：核心拓扑与数据常量声明
# ============================================================================

# 代理组排列顺序 (PROXY_GROUP_ORDER)
# 依据: packages/core/src/generator/proxy-groups.ts
# 优化调整: 业务组前置，地区组 (__regions__) 插在「国内服务」与「非中国」之间，
# 保持兜底组（非中国、漏网之鱼）永远处于数组末尾。
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
    "__regions__",          # 7 个地区组（6 核心国家/地区 url-test + 1 其他国家 select）
    "global", "final",
]

# 规则匹配顺序 (RULE_ORDER)
# 依据: packages/core/src/generator/rules.ts 与 docs/PROJECT.md 优化决策：
# 1. 子服务/高特异性规则排在通用服务之前 (gemini < google, youtube < google)
# 2. 云服务 (cloud) 置于 shopping (amazon/ebay) 之后、geolocation-!cn 之前，防止过早捕获
# 3. 国内服务 (cn) 置于 geolocation-!cn 之后、MATCH 之前，防止混合业务被提前直连
RULE_ORDER = [
    "ad", "private", "gemini", "ai", "youtube", "google-scholar",
    "education", "google", "telegram", "github", "microsoft",
    "apple", "twitter", "meta", "discord", "social-other", "netflix",
    "disney", "streaming-west", "streaming-asia", "steam", "gaming-pc",
    "gaming-console", "dev-tools", "storage", "payment", "crypto", "news",
    "shopping", "cloud", "global", "cn",
]

# SubBoost 默认在 full 模板中排除的模块
DEFAULT_OFF = {"adult", "gemini", "google-scholar"}

# 信息节点（公告、到期提示、剩余流量等非真实可用节点）过滤正则（精准限定结构化上下文，杜绝误杀名为 [官网专线] 或 优质套餐 的正常节点）
INFO_NODE_RE = (
    r"(?:剩余流量|剩余订阅流量|距离下次重置剩余|(?:套餐|订阅)?到期(?:时间)?|过期(?:时间)?|套餐|Expire)\s*[:：]"
    r"|^(?:流量|Traffic)\s*[:：]"
    r"|(?:官网|发布页|网址|群组|频道)\s*[:：]"
    r"|^(?:余额|会员)\s*\|"
    r"|版本太旧|请更新|更新软件|去官网更新|非代理节点|请勿连接|如遇节点失效|永久发布页|欢迎加入"
)
JUNK = INFO_NODE_RE

# 连通性探测直连规则 (Apple / 微软 / 小米 / 华为，排除 Google 防止大陆安卓断网)
CAPTIVE_PORTAL_RULES = [
    "DOMAIN-SUFFIX,captive.apple.com,DIRECT",
    "DOMAIN-SUFFIX,msftconnecttest.com,DIRECT",
    "DOMAIN-SUFFIX,connect.rom.miui.com,DIRECT",
    "DOMAIN-SUFFIX,connectivitycheck.platform.hicloud.com,DIRECT",
]

CAPTIVE_PORTAL_DOMAINS = [
    "captive.apple.com",
    "+.captive.apple.com",
    "msftconnecttest.com",
    "+.msftconnecttest.com",
    "connect.rom.miui.com",
    "+.connect.rom.miui.com",
    "connectivitycheck.platform.hicloud.com",
    "+.connectivitycheck.platform.hicloud.com",
]

# 基础测速参数默认值 (依据 PERFORMANCE.md 优化准则)
DEFAULT_TEST_URL = "https://www.gstatic.com/generate_204"
DEFAULT_TEST_INTERVAL = 600      # 10 分钟一次，减少 50% 测速握手包
DEFAULT_TEST_TOLERANCE = 50      # 50ms 切换容差阈值，消灭乒乓切换
DEFAULT_TEST_LAZY = True         # 懒测速：无流量流经该组时不触发探测

# 规则集基础 CDN 地址与预设映射 (fastly 国内直连高可用，无 TLS 重协商断流)
DEFAULT_CDN_HOST = "fastly.jsdelivr.net"
BASE_URL = f"https://{DEFAULT_CDN_HOST}/gh/MetaCubeX/meta-rules-dat@meta/geo"

# Qure 图标集 CDN 根路径 (Koolson/Qure)
ICON_BASE = f"https://{DEFAULT_CDN_HOST}/gh/Koolson/Qure@master/IconSet/Color"

# 38 个策略组与 Qure 图标映射表
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
    "social-other": "SocialMedia",
    "netflix": "Netflix",
    "disney": "Disney",
    "streaming-west": "ForeignMedia",
    "streaming-asia": "AsianMedia",
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


# ============================================================================
# 第三部分：地区分组与好品味边界正则 (NB)
# ============================================================================

def NB(code: str) -> str:
    """
    两字母地区代码边界正则生成函数 (Non-Letter Boundary)。
    排除词字符数字/下划线对 \\b 的干扰，精准匹配 US01、HK_02 等机场常见节点命名。
    """
    return rf"(?:^|[^a-zA-Z]){code}(?:[^a-zA-Z]|$)"


# 6 个核心地区 url-test 策略组定义
REGIONS = [
    {
        "id": "r-us",
        "name": "美国节点",
        "icon": "United_States",
        "filter": r"(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|" + NB("US") + r"|United.?States|America",
        "exclude": r"(?i)Australia|俄罗斯|Russia|Belarus|巴西|Brazil",
    },
    {
        "id": "r-hk",
        "name": "香港节点",
        "icon": "Hong_Kong",
        "filter": r"(?i)香港|" + NB("HK") + r"|Hong.?Kong|HKG",
        "exclude": None,
    },
    {
        "id": "r-jp",
        "name": "日本节点",
        "icon": "Japan",
        "filter": r"(?i)日本|东京|大阪|川日|沪日|深日|泉日|埼玉|" + NB("JP") + r"|Japan|Tokyo|Osaka",
        "exclude": None,
    },
    {
        "id": "r-sg",
        "name": "狮城节点",
        "icon": "Singapore",
        "filter": r"(?i)新加坡|狮城|" + NB("SG") + r"|Singapore",
        "exclude": None,
    },
    {
        "id": "r-tw",
        "name": "台湾节点",
        "icon": "Taiwan",
        "filter": r"(?i)台湾|台北|台中|新北|彰化|" + NB("TW") + r"|Taiwan|Taipei|Kaohsiung",
        "exclude": r"(?i)Network|Software|Westward",
    },
    {
        "id": "r-kr",
        "name": "韩国节点",
        "icon": "Korea",
        "filter": r"(?i)韩国|首尔|韓|" + NB("KR") + r"|Korea|KOR",
        "exclude": None,
    },
]

# 「其他国家」组定义 (采用排他式 exclude-filter 命中其余节点)
OTHER_REGION = {
    "name": "其他国家",
    "icon": "World_Map",
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
    ),
}

# 完整的 7 大地区组列表
REGION_GROUPS = REGIONS + [OTHER_REGION]


# ============================================================================
# 第四部分：精细化游戏分流与特殊规则集
# ============================================================================

PRE_GAME_RULES = [
    "# === 1. Steam 商店、社区及静态资源强制走代理（置于最前，防黑屏与加载失败） ===",
    "# ⚠ 必须排在 category-games-cn 之前。该规则集是全平台 @cn 统一集，",
    "#   覆盖面极大，若商店域名被它先捕获就会走直连，商店页加载失败。",
    "DOMAIN-SUFFIX,store.steampowered.com,Steam",
    "DOMAIN-SUFFIX,steamcommunity.com,Steam",
    "DOMAIN-SUFFIX,steamstatic.com,Steam",
    "DOMAIN,steamstore-a.akamaihd.net,Steam",
    "DOMAIN,steamcommunity-a.akamaihd.net,Steam",
    "DOMAIN,steamuserimages-a.akamaihd.net,Steam",
    "# === 2. 全平台游戏下载与 Steam 区服握手直连（保持 IPCountry = CN） ===",
    "RULE-SET,category-games-cn,国内服务",
    "DOMAIN-SUFFIX,cm.steampowered.com,国内服务",
    "DOMAIN-SUFFIX,steamserver.net,国内服务",
    "DOMAIN-SUFFIX,steamcontent.com,国内服务",
    "RULE-SET,steam-cn,国内服务",
    "# === Epic Games 下载直连 ===",
    "DOMAIN,epicgames-download1-1251447533.file.myqcloud.com,国内服务",
    "DOMAIN,epicgames-download1.akamaized.net,国内服务",
    "DOMAIN,fastly-download.epicgames.com,国内服务",
    "DOMAIN-SUFFIX,download.epicgames.com,国内服务",
    "DOMAIN-SUFFIX,download2.epicgames.com,国内服务",
    "DOMAIN-SUFFIX,download3.epicgames.com,国内服务",
    "DOMAIN-SUFFIX,download4.epicgames.com,国内服务",
    "# === 暴雪战网 (Battle.net) 下载直连 ===",
    "DOMAIN,blzddist1-a.akamaihd.net,国内服务",
    "DOMAIN,blzddistkr1-a.akamaihd.net,国内服务",
    "DOMAIN,bnetproduct-a.akamaihd.net,国内服务",
    "DOMAIN,blizzard.nefficient.co.kr,国内服务",
    "DOMAIN-SUFFIX,cdn.blizzard.com,国内服务",
    "# === EA (Origin) 与 Ubisoft 下载直连 ===",
    "DOMAIN,origin-a.akamaihd.net,国内服务",
    "DOMAIN,ssl-lvlt.cdn.ea.com,国内服务",
    "DOMAIN,uplaypc-s-ubisoft.cdn.ubi.com,国内服务",
    "# === 主机游戏与 XGP (Xbox/PS/Switch) 下载直连 ===",
    "DOMAIN,assets1.xboxlive.com,国内服务",
    "DOMAIN,assets2.xboxlive.com,国内服务",
    "DOMAIN,xvcf1.xboxlive.com,国内服务",
    "DOMAIN,xvcf2.xboxlive.com,国内服务",
    "DOMAIN,dlassets.xboxlive.com,国内服务",
    "DOMAIN-SUFFIX,dl.playstation.net,国内服务",
    "DOMAIN,atum.hac.lp1.d4c.nintendo.net,国内服务",
    "# === 3. 其余 Steam 流量兜底走代理 ===",
]

# 额外必须补齐的规则集提供者声明
GAME_CN_PROVIDER = {
    "id": "category-games-cn",
    "behavior": "domain",
    "path": "geosite/category-games@cn.mrs",
}

STEAM_CN_PROVIDER = {
    "id": "steam-cn",
    "behavior": "domain",
    "path": "geosite/steam@cn.mrs",
}

EXPERIMENTAL_CN = {
    "id": "cn",
    "behavior": "domain",
    "path": "geosite/cn.mrs",
}


# ============================================================================
# 第五部分：解析器与数据模型提取
# ============================================================================

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

_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U00002190-\U000021FF"
    "\U0000FE00-\U0000FE0F"
    "\U00002B05-\U00002B07"
    "\U000025B6-\U000025C0"
    "\U00002B1B-\U00002B1C"
    "\U00002700-\U000027BF"
    "\U000024C2-\U000024D3"
    "\U000020A0-\U000020BF"
    "\U00002000-\U0000206F"
    "]"
)


def strip_emoji(name: str) -> str:
    """清理字符串中的 emoji 及多余空格，保证组名简洁规范且纯粹。"""
    out = _EMOJI_RE.sub("", name)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def parse_modules(text: str) -> dict:
    """从 TypeScript 源码中解析模块元数据。"""
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


def load_rules_profile() -> tuple[set[str], dict]:
    """
    读取 config/rules_profile.json 中的定制选项。
    若不存在则自动降级到默认 full 预设配置。
    """
    if not RULES_PROFILE_JSON.exists():
        enabled = {m for m in PROXY_GROUP_ORDER if m not in DEFAULT_OFF}
        test_opts = {
            "url": DEFAULT_TEST_URL,
            "interval": DEFAULT_TEST_INTERVAL,
            "tolerance": DEFAULT_TEST_TOLERANCE,
            "lazy": DEFAULT_TEST_LAZY,
        }
        return enabled, test_opts

    data = json.loads(RULES_PROFILE_JSON.read_text(encoding="utf-8"))
    test_opts = data.get("testOptions") or {}
    test_opts = {
        "url": test_opts.get("url", DEFAULT_TEST_URL),
        "interval": test_opts.get("interval", DEFAULT_TEST_INTERVAL),
        "tolerance": test_opts.get("tolerance", DEFAULT_TEST_TOLERANCE),
        "lazy": test_opts.get("lazy", DEFAULT_TEST_LAZY),
    }

    modules_cfg = data.get("modules") or {}
    enabled = set()
    # 核心骨架组恒定启用
    core_groups = {"select", "auto", "ad", "private", "cn", "global", "final", "__regions__"}
    enabled.update(core_groups)

    for mid, item in modules_cfg.items():
        if item.get("enabled", True):
            enabled.add(mid)

    return enabled, test_opts


# ============================================================================
# 第六部分：核心数据结构提取 (Good Taste: Data First)
# ============================================================================

def build_data_models(
    modules: dict,
    enabled_set: set[str],
    test_opts: dict,
    provider_proxy: str = "DIRECT",
    cdn_host: str = DEFAULT_CDN_HOST,
):
    """
    统一提炼三大核心数据模型，供给 YAML 和 JS 双端渲染引擎共用：
    1. proxy_groups_list: 41 个策略组列表
    2. rule_providers_map: 94 个 HTTP MRS 二进制规则集字典
    3. rules_list: 126+ 条规则链列表
    """
    name = {mid: strip_emoji(modules[mid]["name"]) for mid in modules}
    select_name = name["select"]
    auto_name = name["auto"]
    manual_name = "手动切换"

    base_url = f"https://{cdn_host}/gh/MetaCubeX/meta-rules-dat@meta/geo"
    icon_base = f"https://{cdn_host}/gh/Koolson/Qure@master/IconSet/Color"

    # 1. 策略组列表构建
    region_names = [r["name"] for r in REGION_GROUPS]
    groups = []

    for mid in PROXY_GROUP_ORDER:
        if mid == "__regions__":
            for r in REGIONS:
                junk = JUNK if not r["exclude"] else f"{JUNK}|{r['exclude']}"
                groups.append({
                    "name": r["name"],
                    "icon": f"{icon_base}/{r['icon']}.png",
                    "type": "url-test",
                    "include-all": True,
                    "filter": r["filter"],
                    "exclude-filter": junk,
                    "url": test_opts["url"],
                    "interval": test_opts["interval"],
                    "tolerance": test_opts["tolerance"],
                    "lazy": test_opts["lazy"],
                })
            o = OTHER_REGION
            groups.append({
                "name": o["name"],
                "icon": f"{icon_base}/{o['icon']}.png",
                "type": "select",
                "proxies": ["DIRECT"],
                "include-all": True,
                "exclude-filter": f"{JUNK}|{o['exclude']}",
            })
            continue

        if mid not in enabled_set or mid not in modules:
            continue

        m = modules[mid]
        gname = name[mid]
        gtype = m["gtype"]

        if gtype == "url-test":
            groups.append({
                "name": gname,
                "icon": f"{icon_base}/{ICONS[mid]}.png",
                "type": "url-test",
                "include-all": True,
                "exclude-filter": INFO_NODE_RE,
                "url": test_opts["url"],
                "interval": test_opts["interval"],
                "tolerance": test_opts["tolerance"],
                "lazy": test_opts["lazy"],
            })
            if mid == "auto":
                groups.append({
                    "name": manual_name,
                    "icon": f"{icon_base}/Available_1.png",
                    "type": "select",
                    "include-all": True,
                    "exclude-filter": INFO_NODE_RE,
                })
        elif gtype == "reject-first":
            groups.append({
                "name": gname,
                "icon": f"{icon_base}/{ICONS[mid]}.png",
                "type": "select",
                "proxies": ["REJECT", "DIRECT", select_name, manual_name],
            })
        elif gtype == "direct-first":
            groups.append({
                "name": gname,
                "icon": f"{icon_base}/{ICONS[mid]}.png",
                "type": "select",
                "proxies": ["DIRECT", "REJECT", select_name, auto_name, manual_name],
            })
        elif mid == "select":
            groups.append({
                "name": gname,
                "icon": f"{icon_base}/{ICONS[mid]}.png",
                "type": "select",
                "proxies": [auto_name] + region_names + [manual_name, "DIRECT", "REJECT"],
            })
        else:
            groups.append({
                "name": gname,
                "icon": f"{icon_base}/{ICONS[mid]}.png",
                "type": "select",
                "proxies": [select_name, auto_name] + region_names + [manual_name, "DIRECT", "REJECT"],
            })

    # 2. 规则提供者列表构建
    providers = {}
    for mid in PROXY_GROUP_ORDER:
        if mid not in enabled_set or mid not in modules:
            continue
        for r in modules[mid]["rules"]:
            providers[r["id"]] = {
                "type": "http",
                "behavior": r["behavior"],
                "format": "mrs",
                "url": f"{base_url}/{r['path']}",
                "path": f"./ruleset/{r['id']}.mrs",
                "interval": 86400,
                "proxy": provider_proxy,
            }

    # 补齐前置游戏区块所引用的全平台游戏规则集与 Steam CN 直连集
    for ext_r in (GAME_CN_PROVIDER, STEAM_CN_PROVIDER):
        if ext_r["id"] not in providers:
            providers[ext_r["id"]] = {
                "type": "http",
                "behavior": ext_r["behavior"],
                "format": "mrs",
                "url": f"{base_url}/{ext_r['path']}",
                "path": f"./ruleset/{ext_r['id']}.mrs",
                "interval": 86400,
                "proxy": provider_proxy,
            }

    # 补齐实验性国内域名规则集
    if EXPERIMENTAL_CN["id"] not in providers and "cn" in enabled_set:
        providers[EXPERIMENTAL_CN["id"]] = {
            "type": "http",
            "behavior": EXPERIMENTAL_CN["behavior"],
            "format": "mrs",
            "url": f"{base_url}/{EXPERIMENTAL_CN['path']}",
            "path": f"./ruleset/{EXPERIMENTAL_CN['id']}.mrs",
            "interval": 86400,
            "proxy": provider_proxy,
        }

    # 3. 业务规则链构建 (不含内网前置，内网由覆写入口动态拼接)
    steam_target = name["steam"] if "steam" in enabled_set else select_name
    pre_game_clean = [
        line.replace(",Steam", f",{steam_target}")
        for line in PRE_GAME_RULES
        if not line.startswith("#")
    ]

    subboost_rules = []
    emitted = set()
    for mid in RULE_ORDER:
        if mid not in enabled_set or mid not in modules:
            continue
        if mid == "steam":
            # 游戏前置单独存储，便于 JS 引擎前插
            pass

        for r in modules[mid]["rules"]:
            if r["id"] in emitted:
                continue
            emitted.add(r["id"])
            rule_entry = f"RULE-SET,{r['id']},{name[mid]}"
            if r.get("noResolve"):
                rule_entry += ",no-resolve"
            subboost_rules.append(rule_entry)

    if "cn" in enabled_set:
        subboost_rules.append(f"RULE-SET,{EXPERIMENTAL_CN['id']},{name['cn']}")
    subboost_rules.append(f"MATCH,{name['final']}")

    return groups, providers, pre_game_clean, subboost_rules


# ============================================================================
# 第七部分：双轨渲染引擎 (YAML & All-in-One JS)
# ============================================================================

def q(text: str) -> str:
    """给策略组名称加上标准 YAML/JS 双引号并转义反斜杠和引号。"""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_yaml(groups: list[dict], providers: dict, pre_game: list[str], subboost_rules: list[str]) -> str:
    """YAML 渲染器：组装标准的 customSubBoost.yaml 覆写产物。"""
    out = io.StringIO()
    w = out.write

    w("# ==========================================================================\n")
    w("# SubBoost 规则体系 · mihomo 覆写版 (YAML rules: 双轨覆写)\n")
    w("# 由 scripts/gen_override.py 自动生成，请勿手动编辑。\n")
    w("# 核心工程适配说明：\n")
    w("#   · 规则集走 jsdelivr 镜像，全量带 proxy: 节点选择 杜绝静默失败\n")
    w("#   · 节点采用 include-all + exclude-filter 动态过滤\n")
    w("#   · 补全 6 核心地区 url-test (lazy: true, tolerance: 50) 与 1 其他国家 select\n")
    w("#   · 地区代码采用 NB 非字母边界正则，彻底解决 US01/HK_02 漏判\n")
    w("#   · rules: 严格整段替换订阅自带旧规则，彻底避免 MATCH 截断死锁\n")
    w("# ==========================================================================\n\n")

    w("sniffer:\n")
    w("  enable: true\n")
    w("  parse-pure-ip: true\n")
    w("  sniff:\n")
    w("    TLS:\n      ports: [443, 8443]\n")
    w("    HTTP:\n      ports: [80, \"8080-8880\"]\n      override-destination: true\n")
    w("    QUIC:\n      ports: [443, 8443]\n\n")

    w("proxy-groups:\n\n")
    for g in groups:
        w(f"  - name: {q(g['name'])}\n")
        w(f"    icon: {g['icon']}\n")
        w(f"    type: {g['type']}\n")
        if "proxies" in g:
            w(f"    proxies: [{', '.join(g['proxies'])}]\n")
        if g.get("include-all"):
            w("    include-all: true\n")
        if "filter" in g:
            w(f"    filter: {q(g['filter'])}\n")
        if "exclude-filter" in g:
            w(f"    exclude-filter: {q(g['exclude-filter'])}\n")
        if "url" in g:
            w(f"    url: {g['url']}\n")
        if "interval" in g:
            w(f"    interval: {g['interval']}\n")
        if "tolerance" in g:
            w(f"    tolerance: {g['tolerance']}\n")
        if "lazy" in g:
            w(f"    lazy: {'true' if g['lazy'] else 'false'}\n")
        w("\n")

    w("# 全部规则集：MetaCubeX meta-rules-dat，.mrs 二进制，24 小时自动更新\n")
    w("rule-providers:\n")
    for pid in sorted(providers):
        p = providers[pid]
        w(f"  {pid}:\n")
        w(f"    type: {p['type']}\n")
        w(f"    behavior: {p['behavior']}\n")
        w(f"    format: {p['format']}\n")
        w(f"    url: {p['url']}\n")
        w(f"    path: {p['path']}\n")
        w(f"    interval: {p['interval']}\n")
        w(f"    proxy: {q(p['proxy'])}\n")
    w("\n")

    w("rules:\n")
    # 插入连通性探测直连规则，解决公共网络/校园网/酒店 Captive Portal 弹窗失败 (排除 Google 防止安卓断网)
    for r in CAPTIVE_PORTAL_RULES:
        w(f"- {r}\n")
    # 插入前置游戏精细化直连/代理区块与全球业务规则链
    for r in pre_game:
        w(f"- {r}\n")
    for r in subboost_rules:
        w(f"- {r}\n")

    return out.getvalue()


def build_all_in_one_js(
    groups: list[dict],
    providers: dict,
    pre_game: list[str],
    subboost_rules: list[str],
    work_config: dict = None,
    preset_title: str = "全量版 (41 组)",
) -> str:
    """
    全合一 JS 渲染器：组装自包含、跨端通跑的 All-in-One JS 覆写脚本。
    包含顶部用户配置块、节点过滤引擎、DNS治理、策略组注入与全量规则链。
    支持自动将本地 private_work.json 真实配置打包注入顶部 CONFIG 对象。
    """
    out = io.StringIO()
    w = out.write

    enable_work = True
    injected_policy_lines = []
    injected_domains_lines = []
    injected_cidrs_lines = []
    injected_processes_lines = []

    if work_config and isinstance(work_config, dict):
        enable_work = work_config.get("enableWorkRules", True)
        for k, v in (work_config.get("workNameserverPolicy") or {}).items():
            injected_policy_lines.append(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},\n")
        for d in (work_config.get("workDomains") or []):
            injected_domains_lines.append(f"    {json.dumps(d, ensure_ascii=False)},\n")
        for c in (work_config.get("workIpCidrs") or []):
            injected_cidrs_lines.append(f"    {json.dumps(c, ensure_ascii=False)},\n")
        for p in (work_config.get("workProcesses") or []):
            injected_processes_lines.append(f"    {json.dumps(p, ensure_ascii=False)},\n")

    w("/**\n")
    w(" * ==============================================================================\n")
    w(f" * SubBoost 规则体系 · 全合一 Mihomo / Clash JS 覆写版 [{preset_title}]\n")
    w(" * ==============================================================================\n")
    w(" * \n")
    w(" * 【支持客户端与全平台兼容】\n")
    w(" * · Clash Party / Sparkle (Windows / macOS)\n")
    w(" * · Flclash & bettbox (Windows / macOS / Linux / Android / iOS)\n")
    w(" * · 纯标准 ECMAScript 语法，无任何 Node.js 或 DOM 专有依赖，完美兼容 QuickJS/V8。\n")
    w(" * \n")
    w(" * 【三合一能力完整闭环】\n")
    w(" * 1. DNS 统一治理：接管订阅自带回环 DNS，构建 Fake-IP + 国内双 DoH + 工作内网分流策略\n")
    w(" * 2. 节点清洗引擎：过滤公告与流量信息垃圾节点；精准提取倍率并拦截吸血高倍率节点\n")
    w(f" * 3. 完整分流体系：{len(groups)} 策略组（含懒测速与50ms容差） + {len(providers)} 规则集 + 前置游戏与分流规则链\n")
    w(" * \n")
    w(" * 【使用指南】\n")
    w(" * 直接复制本文件全部代码，粘贴到客户端的「覆写脚本 / Script」编辑器中保存即可生效。\n")
    w(" * 工作内网域名、IP 段和功能开关请直接在下方的 CONFIG 对象中填写。\n")
    w(" */\n\n")

    # 1. 顶部全局配置对象
    w("// ============================================================================\n")
    w("// 【用户自定义全局配置与功能开关】\n")
    w("// 提示：以下参数均在 JS 运行时动态求值，修改后即刻生效，无需重新运行生成器。\n")
    w("// ============================================================================\n")
    w("const CONFIG = {\n")
    w("  // ── 1. 基础功能开关 ──\n")
    w("  enableDnsOverride: true,          // 是否接管并覆盖系统/订阅自带 DNS (Fake-IP + DoH)\n")
    w("  enableLanDirect: true,            // 是否注入局域网直连 (10/8, 172.16/12, 192.168/16, 127/8 等)\n")
    w("  enableFakeIpFilterSteam: true,    // Steam 握手与下载是否直解真实国内 IP (保持 IPCountry=CN)\n\n")

    w("  // ── 2. 规则集与图标拉取策略 (解决冷启动 EOF 与代理死锁) ──\n")
    w('  ruleProviderProxy: "DIRECT",     // 规则集拉取通道："DIRECT"（推荐，彻底规避冷启动死锁）或 "节点选择"\n')
    w('  ruleProviderCdn: "fastly",       // 镜像源预设："fastly" | "gcore" | "cdn" | "testingcf"\n\n')

    w("  // ── 3. 节点过滤引擎开关 (运行时执行) ──\n")
    w("  cleanTrashNodes: true,            // 是否过滤公告/流量到期等垃圾信息节点\n")
    w("  cleanHighMultiplier: true,        // 是否过滤高倍率吸血节点\n")
    w("  maxMultiplier: 1.0,               // 允许的最大节点倍率（<= 1.0 保留，> 1.0 剔除）\n\n")

    w("  // ── 4. 工作内网分流与直连开关 ──\n")
    w(f"  enableWorkRules: {'true' if enable_work else 'false'},            // 是否启用工作内网直连与专属分流\n\n")

    w("  // ── 5. 工作内网专属 DNS 策略 (nameserver-policy) ──\n")
    w("  // 格式: { \"域名通配\": \"DNS服务器IP或system\" }\n")
    w("  workNameserverPolicy: {\n")
    w("    // 示例: \"+.corp.internal\": \"10.0.0.53\",\n")
    w("    // 示例: \"+.office.internal\": \"system\",\n")
    for line in injected_policy_lines:
        w(line)
    w("  },\n\n")

    w("  // ── 6. 工作内网域名白名单 (直连 + 自动绕过 Fake-IP + 防污染过滤) ──\n")
    w("  workDomains: [\n")
    w("    // 示例: \"oa.company.com\", \"+.corp.internal\",\n")
    for line in injected_domains_lines:
        w(line)
    w("  ],\n\n")

    w("  // ── 7. 工作内网专属 IP / CIDR 网段直连 ──\n")
    w("  workIpCidrs: [\n")
    w("    // 示例: \"10.20.0.0/16\", \"172.16.50.0/24\",\n")
    for line in injected_cidrs_lines:
        w(line)
    w("  ],\n\n")

    w("  // ── 8. 工作内网专属进程直连 (桌面端生效，移动端自动忽略) ──\n")
    w("  workProcesses: [\n")
    w("    // 示例: \"corp-vpn.exe\", \"company-agent.exe\",\n")
    for line in injected_processes_lines:
        w(line)
    w("  ],\n")
    w("};\n\n")

    # 2. 预编译数据常量
    w("// ============================================================================\n")
    w("// 【预编译核心拓扑数据】(由 scripts/gen_override.py 自动编译，请勿直接编辑此段)\n")
    w("// ============================================================================\n")

    w("const SUBBOOST_PROXY_GROUPS = ")
    w(json.dumps(groups, ensure_ascii=False, indent=2))
    w(";\n\n")

    w("const SUBBOOST_RULE_PROVIDERS = ")
    w(json.dumps(providers, ensure_ascii=False, indent=2))
    w(";\n\n")

    w("const SUBBOOST_PRE_GAME_RULES = ")
    w(json.dumps(pre_game, ensure_ascii=False, indent=2))
    w(";\n\n")

    w("const SUBBOOST_RULES = ")
    w(json.dumps(subboost_rules, ensure_ascii=False, indent=2))
    w(";\n\n")

    # 3. 核心 main(config) 流水线
    w("""// ============================================================================
// 【静态过滤规则与倍率提取引擎】(模块级单例，杜绝遍历高频分配 GC 压力)
// ============================================================================
// 垃圾与非代理信息节点正则（精确匹配冒号、链接、日期或明确非代理词，杜绝误杀「官网专线」「优质套餐」等正常节点）
const TRASH_REGEX = /(?:剩余流量|剩余订阅流量|距离下次重置剩余|(?:套餐|订阅)?到期(?:时间)?|过期(?:时间)?|套餐|Expire)\\s*[:：]|^(?:流量|Traffic)\\s*[:：]|(?:官网|发布页|网址|群组|频道)\\s*[:：]|^(?:余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新|非代理节点|请勿连接|如遇节点失效|永久发布页|欢迎加入/i;

// 精准倍率识别正则表 (消除对线路代号如 IEPL X2 与流量容量如 50G 的误杀)
const MULTIPLIER_PATTERNS = [
  // 1. 显式前置关键字 (倍率: 1.5, 流量倍率: 2.0, ratio: 1.5)
  /(?:倍率|倍数|ratio)\\s*[:：=]?\\s*(\\d+(?:\\.\\d+)?)/i,
  // 2. 流量后紧跟倍率 (流量: 1.5x, traffic: 2倍，必须带 x 或 倍，严禁单独数字)
  /(?:流量|traffic)\\s*[:：=]?\\s*(\\d+(?:\\.\\d+)?)\\s*[xX倍]/i,
  // 3. 数字紧跟 x/X 或 倍 (如 1.5x, 2X, 3倍，前驱非数字非点，后继非字母数字)
  /(?:^|[^\\d.])(\\d+(?:\\.\\d+)?)\\s*(?:[xX]|倍)(?=$|[^\\w])/i,
  // 4. 定界符括起的前置 x 倍率 (如 [x2], | x2, (x1.5))
  /(?:[|\\[(])\\s*[xX]\\s*(\\d+(?:\\.\\d+)?)(?=$|[\\s\\])|])/i,
  // 5. 显式带小数点的 x 倍率 (如 x1.5, x2.0)
  /(?:^|\\s)[xX]\\s*(\\d+\\.\\d+)(?=$|[\\s\\])|])/i,
];

function getMultiplier(name) {
  if (typeof name !== "string") return null;
  for (const regex of MULTIPLIER_PATTERNS) {
    const match = name.match(regex);
    if (!match) continue;
    const val = Number(match[1]);
    if (Number.isFinite(val) && val >= 0) return val;
  }
  return null;
}

// ============================================================================
// 【主入口函数】(Clash Party / Flclash / bettbox 统一运行时执行)
// ============================================================================
function main(config) {
  // 1. 防御性空安全初始化（保证空配置或字段缺失时不发生未捕获异常）
  config = config || {};
  config.proxies = Array.isArray(config.proxies) ? config.proxies : [];
  config["proxy-groups"] = Array.isArray(config["proxy-groups"]) ? config["proxy-groups"] : [];
  config["rule-providers"] = (config["rule-providers"] && typeof config["rule-providers"] === "object") ? config["rule-providers"] : {};
  config.rules = Array.isArray(config.rules) ? config.rules : [];

  // 2. 嗅探配置 (sniffer) 注入
  config.sniffer = {
    enable: true,
    "parse-pure-ip": true,
    sniff: {
      TLS: { ports: [443, 8443] },
      HTTP: { ports: [80, "8080-8880"], "override-destination": true },
      QUIC: { ports: [443, 8443] },
    },
  };

  // ==========================================================================
  // 第一步：节点清洗引擎 (按 CONFIG 动态执行)
  // ==========================================================================
  const removedNames = new Set();
  if (CONFIG.cleanTrashNodes || CONFIG.cleanHighMultiplier) {
    const originalProxies = config.proxies;
    const filteredProxies = originalProxies.filter(proxy => {
      if (!proxy || typeof proxy.name !== "string") return true;

      // 规则 A: 命中垃圾公告关键字，移除
      if (CONFIG.cleanTrashNodes && TRASH_REGEX.test(proxy.name)) {
        removedNames.add(proxy.name);
        return false;
      }

      // 规则 B: 倍率大于阈值，移除；未标注倍率则安全保留
      if (CONFIG.cleanHighMultiplier) {
        const mult = getMultiplier(proxy.name);
        if (mult !== null && mult > CONFIG.maxMultiplier) {
          removedNames.add(proxy.name);
          return false;
        }
      }

      return true;
    });

    // 防御性安全底线 (Never break userspace): 若所有节点均被倍率过滤剔除，降级回退保留原始有效节点
    if (filteredProxies.length === 0 && originalProxies.length > 0) {
      config.proxies = originalProxies.filter(p => !p || typeof p.name !== "string" || !TRASH_REGEX.test(p.name));
    } else {
      config.proxies = filteredProxies;
    }
  }

  // ==========================================================================
  // 第二步：全局 DNS 与 Fake-IP 体系构建 (按 CONFIG 动态执行)
  // ==========================================================================
  if (CONFIG.enableDnsOverride) {
    delete config.dns;

    // Fake-IP 绕过列表 (含常见连通性探测域名放行，排除 Google 防止安卓断网)
    const fakeIpFilters = [
      "+.lan",
      "+.local",
      "time.*.com",
      "ntp.*.com",
      "+.market.xiaomi.com",
      "captive.apple.com",
      "+.captive.apple.com",
      "msftconnecttest.com",
      "+.msftconnecttest.com",
      "connect.rom.miui.com",
      "+.connect.rom.miui.com",
      "connectivitycheck.platform.hicloud.com",
      "+.connectivitycheck.platform.hicloud.com",
    ];

    // Steam 握手与下载域名直解真实国内 IP，保持 IPCountry=CN
    if (CONFIG.enableFakeIpFilterSteam) {
      fakeIpFilters.push(
        "cm.steampowered.com",
        "+.cm.steampowered.com",
        "+.steamserver.net",
        "+.steamcontent.com"
      );
    }

    // 工作内网域名自动并入 Fake-IP 放行列表，确保解析拿真实内网 IP
    if (CONFIG.enableWorkRules && Array.isArray(CONFIG.workDomains)) {
      for (const d of CONFIG.workDomains) {
        if (!d) continue;
        const pattern = d.startsWith("+.") || d.startsWith("*.") ? d : "+." + d;
        if (!fakeIpFilters.includes(pattern)) fakeIpFilters.push(pattern);
      }
    }

    const nameserverPolicy = {
      "+.captive.apple.com,+.msftconnecttest.com,+.connect.rom.miui.com,+.connectivitycheck.platform.hicloud.com": [
        "119.29.29.29",
        "223.5.5.5",
      ],
    };

    if (CONFIG.enableWorkRules && CONFIG.workNameserverPolicy) {
      Object.assign(nameserverPolicy, CONFIG.workNameserverPolicy);
    }

    config.dns = {
      enable: true,
      ipv6: false,
      "enhanced-mode": "fake-ip",
      "fake-ip-range": "198.18.0.1/16",
      "fake-ip-filter-mode": "blacklist",
      "fake-ip-filter": fakeIpFilters,
      "use-hosts": false,
      "use-system-hosts": true,
      "respect-rules": false,
      "default-nameserver": ["223.5.5.5", "119.29.29.29"],
      nameserver: [
        "https://223.5.5.5/dns-query",
        "https://doh.pub/dns-query",
        "https://dns.alidns.com/dns-query",
      ],
      "proxy-server-nameserver": [
        "https://223.5.5.5/dns-query",
        "223.5.5.5",
        "119.29.29.29",
      ],
      "direct-nameserver": ["system"],
      "nameserver-policy": nameserverPolicy,
    };
  }

  // ==========================================================================
  // 第三步：策略组注入与级联引用清理
  // ==========================================================================
  // 注入预编译的 SubBoost 策略组（深拷贝避免受外部修改影响）
  const groups = JSON.parse(JSON.stringify(SUBBOOST_PROXY_GROUPS));

  // 级联清理：若策略组显式声明了 proxies 列表，剔除已被移除的节点名
  for (const group of groups) {
    if (Array.isArray(group.proxies)) {
      group.proxies = group.proxies.filter(name => !removedNames.has(name));
    }
  }
  config["proxy-groups"] = groups;

  // ==========================================================================
  // 第四步：规则提供者 (rule-providers) 注入与运行时动态改写 (解耦冷启动死锁)
  // ==========================================================================
  const CDN_DOMAINS = {
    fastly: "fastly.jsdelivr.net",
    gcore: "gcore.jsdelivr.net",
    cdn: "cdn.jsdelivr.net",
    testingcf: "testingcf.jsdelivr.net",
  };
  const activeCdnHost = (CONFIG.ruleProviderCdn && CDN_DOMAINS[CONFIG.ruleProviderCdn])
    ? CDN_DOMAINS[CONFIG.ruleProviderCdn]
    : (CONFIG.ruleProviderCdn || "fastly.jsdelivr.net");
  const activeProxy = (CONFIG.ruleProviderProxy !== undefined)
    ? CONFIG.ruleProviderProxy
    : "DIRECT";

  const ruleProviders = JSON.parse(JSON.stringify(SUBBOOST_RULE_PROVIDERS));
  for (const p of Object.values(ruleProviders)) {
    if (activeProxy) {
      p.proxy = activeProxy;
    } else {
      delete p.proxy;
    }
    if (activeCdnHost && activeCdnHost !== "fastly.jsdelivr.net") {
      p.url = p.url.replace("fastly.jsdelivr.net", activeCdnHost);
    }
  }

  // 若运行时配置了非默认 CDN，同步重定向策略组中的图标 URL
  if (activeCdnHost && activeCdnHost !== "fastly.jsdelivr.net") {
    for (const group of groups) {
      if (group.icon && typeof group.icon === "string") {
        group.icon = group.icon.replace("fastly.jsdelivr.net", activeCdnHost);
      }
    }
  }

  config["rule-providers"] = Object.assign({}, config["rule-providers"] || {}, ruleProviders);

  // ==========================================================================
  // 第五步：全量分流规则链拼装 (First-Match-Win 严格保序)
  // ==========================================================================
  const rules = [];

  // 0. 连通性探测直连规则 (Apple / 微软 / 小米 / 华为，排除 Google 防止大陆安卓断网)
  rules.push(
    "DOMAIN-SUFFIX,captive.apple.com,DIRECT",
    "DOMAIN-SUFFIX,msftconnecttest.com,DIRECT",
    "DOMAIN-SUFFIX,connect.rom.miui.com,DIRECT",
    "DOMAIN-SUFFIX,connectivitycheck.platform.hicloud.com,DIRECT"
  );

  // 1. 局域网私有网段直连
  if (CONFIG.enableLanDirect) {
    rules.push(
      "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
      "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
      "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
      "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
      "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
      "IP-CIDR6,::1/128,DIRECT,no-resolve"
    );
  }

  // 2. 工作内网专属直连规则 (按域名、IP段、进程精准匹配)
  if (CONFIG.enableWorkRules) {
    if (Array.isArray(CONFIG.workDomains)) {
      for (const d of CONFIG.workDomains) {
        if (!d) continue;
        const clean = d.replace(/^(\\+\\.|\\*\\.)/, "");
        rules.push("DOMAIN-SUFFIX," + clean + ",DIRECT");
      }
    }
    if (Array.isArray(CONFIG.workIpCidrs)) {
      for (const ip of CONFIG.workIpCidrs) {
        if (!ip) continue;
        const ruleType = ip.includes(":") ? "IP-CIDR6" : "IP-CIDR";
        rules.push(ruleType + "," + ip + ",DIRECT,no-resolve");
      }
    }
    if (Array.isArray(CONFIG.workProcesses)) {
      for (const proc of CONFIG.workProcesses) {
        if (!proc) continue;
        rules.push("PROCESS-NAME," + proc + ",DIRECT");
      }
    }
  }

  // 3. 前置游戏精细化直连/代理区块 (Steam 商店走代理, 下载与握手直连)
  rules.push(...SUBBOOST_PRE_GAME_RULES);

  // 4. SubBoost 全球分流业务规则链
  rules.push(...SUBBOOST_RULES);

  config.rules = rules;

  return config;
}

// Node.js 模块导出支持（供测试套件 require 校验，在客户端环境被静默忽略）
if (typeof module !== "undefined" && module.exports) {
  module.exports = { main, CONFIG };
}
""")

    return out.getvalue()


# ============================================================================
# 第八部分：自检与自动化语法校验 (SELF-CHECK)
# ============================================================================

def self_check_yaml(yaml_text: str, expected_provider_count: int = None) -> None:
    """自动化校验生成的 YAML 覆写配置。"""
    if not re.search(r"^rules:\s*$", yaml_text, re.M):
        raise ValueError("【严重错误】未找到 'rules:' 声明！严禁遗漏整段覆盖的 rules:")
    if "category-games-cn" not in yaml_text:
        raise ValueError("【严重错误】未找到 'category-games-cn' 游戏前置直连规则！")
    if r"(?:^|[^a-zA-Z])US(?:[^a-zA-Z]|$)" not in yaml_text:
        raise ValueError("【严重错误】美国组缺少 NB(US) 非字母边界正则！")

    expected_regions = ["美国节点", "香港节点", "日本节点", "狮城节点", "台湾节点", "韩国节点", "其他国家"]
    for reg in expected_regions:
        if f'name: "{reg}"' not in yaml_text and f'name: {reg}' not in yaml_text:
            raise ValueError(f"【严重错误】缺少地区策略组: {reg}")

    rules_block = yaml_text[yaml_text.find("\nrules:") :]
    providers_block = yaml_text[yaml_text.find("\nrule-providers:") : yaml_text.find("\nrules:")]
    rulesets = re.findall(r"^\s*-\s+RULE-SET,([^,]+),", rules_block, re.M)
    for rset in rulesets:
        if f"\n  {rset}:" not in providers_block:
            raise ValueError(f"【严重错误】规则链引用的 RULE-SET '{rset}' 未在 rule-providers 中定义！")

    # 引用完整性断言：确保每一条规则的目标策略组均已在 proxy-groups 中声明
    declared_groups = set(re.findall(r'^\s*-\s+name:\s*["\']?([^"\']+)["\']?', yaml_text[:yaml_text.find("\nrule-providers:")], re.M))
    valid_targets = declared_groups | {"DIRECT", "REJECT", "COMPATIBLE", "PASS"}
    for line in rules_block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        parts = line[2:].split(",")
        if len(parts) >= 3 and parts[2] not in ("no-resolve",):
            target = parts[2].strip()
            if target not in valid_targets:
                raise ValueError(f"【严重错误】规则 '{line[2:]}' 的目标策略组 '{target}' 未在 proxy-groups 中声明！")

    provider_count = len(re.findall(r"^  \S+:\s*$", providers_block, re.M))
    if expected_provider_count is not None and provider_count != expected_provider_count:
        raise ValueError(f"【严重错误】rule-providers 数量预期为 {expected_provider_count}，实测为 {provider_count}！")
    if provider_count == 0:
        raise ValueError("【严重错误】rule-providers 数量为 0！")


def self_check_js(js_text: str) -> None:
    """自动化校验生成的 All-in-One JS 覆写脚本。"""
    if "function main(config)" not in js_text:
        raise ValueError("【严重错误】JS 覆写缺少 'function main(config)' 入口函数！")
    if "const CONFIG = {" not in js_text:
        raise ValueError("【严重错误】JS 覆写缺少顶部 'CONFIG' 配置对象声明！")
    if "SUBBOOST_PROXY_GROUPS" not in js_text:
        raise ValueError("【严重错误】JS 覆写缺少策略组数据声明！")
    if "SUBBOOST_RULE_PROVIDERS" not in js_text:
        raise ValueError("【严重错误】JS 覆写缺少规则集数据声明！")

    # 利用本地 Node.js 进行 JavaScript 语法树静态校验
    try:
        proc = subprocess.run(
            ["node", "-c"],
            input=js_text,
            text=True,
            capture_output=True,
            timeout=15,
        )
        if proc.returncode != 0:
            raise ValueError(f"【严重错误】JS 语法校验失败 (Node.js -c):\n{proc.stderr}")
    except FileNotFoundError:
        # 未安装 node 时跳过动态校验
        pass


# ============================================================================
# 第九部分：CLI 入口
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="SubBoost 规则体系 全合一跨端覆写生成器")
    parser.add_argument(
        "--preset",
        type=str,
        default="all",
        choices=["all", "minimal", "standard", "full"],
        help="生成档位: all (默认直接并行生成 3 档) | minimal (极简 ~15组) | standard (标准 ~22组) | full (全量 41组)",
    )
    parser.add_argument(
        "--yaml-only",
        action="store_true",
        help="仅生成 YAML 覆写产物",
    )
    parser.add_argument(
        "--js-only",
        action="store_true",
        help="仅生成 All-in-One JS 覆写产物",
    )
    parser.add_argument(
        "--provider-proxy",
        type=str,
        default="DIRECT",
        help="规则集提供者默认代理通道 (默认: DIRECT，彻底消除冷启动死锁；可选 节点选择 等)",
    )
    parser.add_argument(
        "--cdn-host",
        type=str,
        default=DEFAULT_CDN_HOST,
        help=f"规则集与图标的 CDN 域名 (默认: {DEFAULT_CDN_HOST})",
    )
    args = parser.parse_args()

    if not MODULES_TS.exists():
        sys.exit(f"【致命错误】找不到模块定义文件: {MODULES_TS}")

    modules = parse_modules(MODULES_TS.read_text(encoding="utf-8"))
    full_enabled_set, test_opts = load_rules_profile()

    tiers = ["minimal", "standard", "full"] if args.preset == "all" else [args.preset]

    work_config = load_private_work_config()
    if work_config:
        print("[*] 检测到本地私有配置 config/private_work.json，正在自动打包注入自用 JS 覆写...")
    else:
        print("[*] 未检测到本地私有配置，使用纯净配置模板生成...")

    # 确保产物根目录及分类子目录全部创建
    OVERRIDE_DIR.mkdir(parents=True, exist_ok=True)
    OVERRIDE_JS_DIR.mkdir(parents=True, exist_ok=True)
    OVERRIDE_EXAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    OVERRIDE_YAML_DIR.mkdir(parents=True, exist_ok=True)

    for tier in tiers:
        preset_info = PRESETS[tier]
        if preset_info["modules"] is not None:
            tier_enabled = set(preset_info["modules"])
        else:
            tier_enabled = set(full_enabled_set)

        groups, providers, pre_game, subboost_rules = build_data_models(
            modules,
            tier_enabled,
            test_opts,
            provider_proxy=args.provider_proxy,
            cdn_host=args.cdn_host,
        )

        enabled_biz = len([m for m in tier_enabled if m in modules and m not in {"select", "auto", "ad", "private", "cn", "global", "final", "__regions__"}])
        print(f"\n[{tier.upper()}] 正在构建 {preset_info['name']} (策略组: {len(groups)} 组, 规则集: {len(providers)} 个, 业务模块: {enabled_biz} 个)...")

        # 1. 构建与写出 JS 产物
        if not args.yaml_only:
            js_path = OVERRIDE_JS_DIR / f"customSubBoost.{tier}.js"
            example_js_path = OVERRIDE_EXAMPLE_DIR / f"customSubBoost.{tier}.example.js"

            # 生成本地直接开箱即用版（注入个人工作内网信息）
            js_text = build_all_in_one_js(
                groups,
                providers,
                pre_game,
                subboost_rules,
                work_config=work_config,
                preset_title=preset_info["name"],
            )
            self_check_js(js_text)
            js_path.write_text(js_text, encoding="utf-8")
            print(f"  [✔] JS 覆写生成成功: {js_path.name} (共 {len(js_text)} 字节, {js_text.count(chr(10))} 行)")

            # 同步生成脱敏纯净示例模板（供 Git 追踪，永不包含个人敏感信息）
            example_js_text = build_all_in_one_js(
                groups,
                providers,
                pre_game,
                subboost_rules,
                work_config=None,
                preset_title=preset_info["name"],
            )
            example_js_path.write_text(example_js_text, encoding="utf-8")
            print(f"  [✔] 脱敏示例模板生成成功: {example_js_path.name} (共 {len(example_js_text)} 字节, 供 Git 追踪)")

        # 2. 构建与写出 YAML 产物
        if not args.js_only:
            yaml_path = OVERRIDE_YAML_DIR / f"customSubBoost.{tier}.yaml"
            yaml_text = build_yaml(groups, providers, pre_game, subboost_rules)
            self_check_yaml(yaml_text)
            yaml_path.write_text(yaml_text, encoding="utf-8")
            print(f"  [✔] 备用 YAML 覆写生成成功: {yaml_path.name} (共 {len(yaml_text)} 字节, {yaml_text.count(chr(10))} 行)")

    print(f"\n[*] 自检断言全部通过：全部 {len(tiers)} 个档位均已成功输出至 {OVERRIDE_DIR.name}/(js, example, yaml) 子目录！")


if __name__ == "__main__":
    main()

