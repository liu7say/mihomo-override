/**
 * ==============================================================================
 * SubBoost 规则体系 · 全合一 Mihomo / Clash JS 覆写版 [极简版 (~15 组)]
 * ==============================================================================
 * 
 * 【支持客户端与全平台兼容】
 * · Clash Party / Sparkle (Windows / macOS)
 * · Flclash & bettbox (Windows / macOS / Linux / Android / iOS)
 * · 纯标准 ECMAScript 语法，无任何 Node.js 或 DOM 专有依赖，完美兼容 QuickJS/V8。
 * 
 * 【三合一能力完整闭环】
 * 1. DNS 统一治理：接管订阅自带回环 DNS，构建 Fake-IP + 国内双 DoH + 工作内网分流策略
 * 2. 节点清洗引擎：过滤公告与流量信息垃圾节点；精准提取倍率并拦截吸血高倍率节点
 * 3. 完整分流体系：16 策略组（含懒测速与50ms容差） + 12 规则集 + 前置游戏与分流规则链
 * 
 * 【使用指南】
 * 直接复制本文件全部代码，粘贴到客户端的「覆写脚本 / Script」编辑器中保存即可生效。
 * 工作内网域名、IP 段和功能开关请直接在下方的 CONFIG 对象中填写。
 */

// ============================================================================
// 【用户自定义全局配置与功能开关】
// 提示：以下参数均在 JS 运行时动态求值，修改后即刻生效，无需重新运行生成器。
// ============================================================================
const CONFIG = {
  // ── 1. 基础功能开关 ──
  enableDnsOverride: true,          // 是否接管并覆盖系统/订阅自带 DNS (Fake-IP + DoH)
  enableLanDirect: true,            // 是否注入局域网直连 (10/8, 172.16/12, 192.168/16, 127/8 等)
  enableFakeIpFilterSteam: true,    // Steam 握手与下载是否直解真实国内 IP (保持 IPCountry=CN)

  // ── 2. 规则集与图标拉取策略 (解决冷启动 EOF 与代理死锁) ──
  ruleProviderProxy: "DIRECT",     // 规则集拉取通道："DIRECT"（推荐，彻底规避冷启动死锁）或 "节点选择"
  ruleProviderCdn: "fastly",       // 镜像源预设："fastly" | "gcore" | "cdn" | "testingcf"

  // ── 3. 节点过滤引擎开关 (运行时执行) ──
  cleanTrashNodes: true,            // 是否过滤公告/流量到期等垃圾信息节点
  cleanHighMultiplier: true,        // 是否过滤高倍率吸血节点
  maxMultiplier: 1.0,               // 允许的最大节点倍率（<= 1.0 保留，> 1.0 剔除）

  // ── 4. 工作内网分流与直连开关 ──
  enableWorkRules: true,            // 是否启用工作内网直连与专属分流

  // ── 5. 工作内网专属 DNS 策略 (nameserver-policy) ──
  // 格式: { "域名通配": "DNS服务器IP或system" }
  workNameserverPolicy: {
    // 示例: "+.corp.internal": "10.0.0.53",
    // 示例: "+.office.internal": "system",
  },

  // ── 6. 工作内网域名白名单 (直连 + 自动绕过 Fake-IP + 防污染过滤) ──
  workDomains: [
    // 示例: "oa.company.com", "+.corp.internal",
  ],

  // ── 7. 工作内网专属 IP / CIDR 网段直连 ──
  workIpCidrs: [
    // 示例: "10.20.0.0/16", "172.16.50.0/24",
  ],

  // ── 8. 工作内网专属进程直连 (桌面端生效，移动端自动忽略) ──
  workProcesses: [
    // 示例: "corp-vpn.exe", "company-agent.exe",
  ],
};

// ============================================================================
// 【预编译核心拓扑数据】(由 scripts/gen_override.py 自动编译，请勿直接编辑此段)
// ============================================================================
const SUBBOOST_PROXY_GROUPS = [
  {
    "name": "节点选择",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Proxy.png",
    "type": "select",
    "proxies": [
      "自动选择",
      "美国节点",
      "香港节点",
      "日本节点",
      "狮城节点",
      "台湾节点",
      "韩国节点",
      "其他国家",
      "手动切换",
      "DIRECT",
      "REJECT"
    ]
  },
  {
    "name": "自动选择",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Auto.png",
    "type": "url-test",
    "include-all": true,
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "手动切换",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Available_1.png",
    "type": "select",
    "include-all": true
  },
  {
    "name": "广告拦截",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AdBlack.png",
    "type": "select",
    "proxies": [
      "REJECT",
      "DIRECT",
      "节点选择",
      "手动切换"
    ]
  },
  {
    "name": "AI 服务",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AI.png",
    "type": "select",
    "proxies": [
      "节点选择",
      "自动选择",
      "美国节点",
      "香港节点",
      "日本节点",
      "狮城节点",
      "台湾节点",
      "韩国节点",
      "其他国家",
      "手动切换",
      "DIRECT",
      "REJECT"
    ]
  },
  {
    "name": "私有网络",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Lock.png",
    "type": "select",
    "proxies": [
      "DIRECT",
      "REJECT",
      "节点选择",
      "自动选择",
      "手动切换"
    ]
  },
  {
    "name": "国内服务",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/CN.png",
    "type": "select",
    "proxies": [
      "DIRECT",
      "REJECT",
      "节点选择",
      "自动选择",
      "手动切换"
    ]
  },
  {
    "name": "美国节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/United_States.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|(?:^|[^a-zA-Z])US(?:[^a-zA-Z]|$)|United.?States|America",
    "exclude-filter": "(?i)Australia|俄罗斯|Russia|Belarus|巴西|Brazil",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "香港节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Hong_Kong.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)香港|(?:^|[^a-zA-Z])HK(?:[^a-zA-Z]|$)|Hong.?Kong|HKG",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "日本节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Japan.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)日本|东京|大阪|川日|沪日|深日|泉日|埼玉|(?:^|[^a-zA-Z])JP(?:[^a-zA-Z]|$)|Japan|Tokyo|Osaka",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "狮城节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Singapore.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)新加坡|狮城|(?:^|[^a-zA-Z])SG(?:[^a-zA-Z]|$)|Singapore",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "台湾节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Taiwan.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)台湾|台北|台中|新北|彰化|(?:^|[^a-zA-Z])TW(?:[^a-zA-Z]|$)|Taiwan|Taipei|Kaohsiung",
    "exclude-filter": "(?i)Network|Software|Westward",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "韩国节点",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Korea.png",
    "type": "url-test",
    "include-all": true,
    "filter": "(?i)韩国|首尔|韓|(?:^|[^a-zA-Z])KR(?:[^a-zA-Z]|$)|Korea|KOR",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "其他国家",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/World_Map.png",
    "type": "select",
    "include-all": true,
    "exclude-filter": "(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|United.?States|(?:^|[^a-zA-Z])US(?:[^a-zA-Z]|$)|香港|Hong.?Kong|HKG|(?:^|[^a-zA-Z])HK(?:[^a-zA-Z]|$)|日本|东京|大阪|川日|沪日|深日|泉日|埼玉|Japan|Tokyo|Osaka|(?:^|[^a-zA-Z])JP(?:[^a-zA-Z]|$)|新加坡|狮城|Singapore|(?:^|[^a-zA-Z])SG(?:[^a-zA-Z]|$)|台湾|台北|台中|新北|彰化|Taiwan|Taipei|Kaohsiung|(?:^|[^a-zA-Z])TW(?:[^a-zA-Z]|$)|韩国|首尔|韓|Korea|KOR|(?:^|[^a-zA-Z])KR(?:[^a-zA-Z]|$)"
  },
  {
    "name": "非中国",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Global.png",
    "type": "select",
    "proxies": [
      "节点选择",
      "自动选择",
      "美国节点",
      "香港节点",
      "日本节点",
      "狮城节点",
      "台湾节点",
      "韩国节点",
      "其他国家",
      "手动切换",
      "DIRECT",
      "REJECT"
    ]
  },
  {
    "name": "漏网之鱼",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Final.png",
    "type": "select",
    "proxies": [
      "节点选择",
      "自动选择",
      "美国节点",
      "香港节点",
      "日本节点",
      "狮城节点",
      "台湾节点",
      "韩国节点",
      "其他国家",
      "手动切换",
      "DIRECT",
      "REJECT"
    ]
  }
];

const SUBBOOST_RULE_PROVIDERS = {
  "category-ads-all": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/category-ads-all.mrs",
    "path": "./ruleset/category-ads-all.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "openai": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/openai.mrs",
    "path": "./ruleset/openai.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "anthropic": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/anthropic.mrs",
    "path": "./ruleset/anthropic.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "category-ai-chat-!cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/category-ai-chat-!cn.mrs",
    "path": "./ruleset/category-ai-chat-!cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "private": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/private.mrs",
    "path": "./ruleset/private.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "private-ip": {
    "type": "http",
    "behavior": "ipcidr",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geoip/private.mrs",
    "path": "./ruleset/private-ip.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "geolocation-cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/geolocation-cn.mrs",
    "path": "./ruleset/geolocation-cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "cn-ip": {
    "type": "http",
    "behavior": "ipcidr",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geoip/cn.mrs",
    "path": "./ruleset/cn-ip.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "geolocation-!cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/geolocation-!cn.mrs",
    "path": "./ruleset/geolocation-!cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "category-games-cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/category-games@cn.mrs",
    "path": "./ruleset/category-games-cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "steam-cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/steam@cn.mrs",
    "path": "./ruleset/steam-cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  },
  "cn": {
    "type": "http",
    "behavior": "domain",
    "format": "mrs",
    "url": "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/cn.mrs",
    "path": "./ruleset/cn.mrs",
    "interval": 86400,
    "proxy": "DIRECT"
  }
};

const SUBBOOST_PRE_GAME_RULES = [
  "DOMAIN-SUFFIX,store.steampowered.com,节点选择",
  "DOMAIN-SUFFIX,steamcommunity.com,节点选择",
  "DOMAIN-SUFFIX,steamstatic.com,节点选择",
  "DOMAIN,steamstore-a.akamaihd.net,节点选择",
  "DOMAIN,steamcommunity-a.akamaihd.net,节点选择",
  "DOMAIN,steamuserimages-a.akamaihd.net,节点选择",
  "RULE-SET,category-games-cn,国内服务",
  "DOMAIN-SUFFIX,cm.steampowered.com,国内服务",
  "DOMAIN-SUFFIX,steamserver.net,国内服务",
  "DOMAIN-SUFFIX,steamcontent.com,国内服务",
  "RULE-SET,steam-cn,国内服务",
  "DOMAIN,epicgames-download1-1251447533.file.myqcloud.com,国内服务",
  "DOMAIN,epicgames-download1.akamaized.net,国内服务",
  "DOMAIN,fastly-download.epicgames.com,国内服务",
  "DOMAIN-SUFFIX,download.epicgames.com,国内服务",
  "DOMAIN-SUFFIX,download2.epicgames.com,国内服务",
  "DOMAIN-SUFFIX,download3.epicgames.com,国内服务",
  "DOMAIN-SUFFIX,download4.epicgames.com,国内服务",
  "DOMAIN,blzddist1-a.akamaihd.net,国内服务",
  "DOMAIN,blzddistkr1-a.akamaihd.net,国内服务",
  "DOMAIN,bnetproduct-a.akamaihd.net,国内服务",
  "DOMAIN,blizzard.nefficient.co.kr,国内服务",
  "DOMAIN-SUFFIX,cdn.blizzard.com,国内服务",
  "DOMAIN,origin-a.akamaihd.net,国内服务",
  "DOMAIN,ssl-lvlt.cdn.ea.com,国内服务",
  "DOMAIN,uplaypc-s-ubisoft.cdn.ubi.com,国内服务",
  "DOMAIN,assets1.xboxlive.com,国内服务",
  "DOMAIN,assets2.xboxlive.com,国内服务",
  "DOMAIN,xvcf1.xboxlive.com,国内服务",
  "DOMAIN,xvcf2.xboxlive.com,国内服务",
  "DOMAIN,dlassets.xboxlive.com,国内服务",
  "DOMAIN-SUFFIX,dl.playstation.net,国内服务",
  "DOMAIN,atum.hac.lp1.d4c.nintendo.net,国内服务"
];

const SUBBOOST_RULES = [
  "RULE-SET,category-ads-all,广告拦截",
  "RULE-SET,private,私有网络",
  "RULE-SET,private-ip,私有网络,no-resolve",
  "RULE-SET,openai,AI 服务",
  "RULE-SET,anthropic,AI 服务",
  "RULE-SET,category-ai-chat-!cn,AI 服务",
  "RULE-SET,geolocation-!cn,非中国",
  "RULE-SET,geolocation-cn,国内服务",
  "RULE-SET,cn-ip,国内服务,no-resolve",
  "RULE-SET,cn,国内服务",
  "MATCH,漏网之鱼"
];

// ============================================================================
// 【静态过滤规则与倍率提取引擎】(模块级单例，杜绝遍历高频分配 GC 压力)
// ============================================================================
// 垃圾与非代理信息节点正则（精确匹配冒号、链接、日期或明确非代理词，杜绝误杀「官网专线」「优质套餐」等正常节点）
const TRASH_REGEX = /(?:剩余流量|剩余订阅流量|距离下次重置剩余|(?:套餐|订阅)?到期(?:时间)?|过期(?:时间)?|套餐|Expire)\s*[:：]|^(?:流量|Traffic)\s*[:：]|(?:官网|发布页|网址|群组|频道)\s*[:：]|^(?:余额|会员)\s*\||版本太旧|请更新|更新软件|去官网更新|非代理节点|请勿连接|如遇节点失效|永久发布页|欢迎加入/i;

// 精准倍率识别正则表 (消除对线路代号如 IEPL X2 与流量容量如 50G 的误杀)
const MULTIPLIER_PATTERNS = [
  // 1. 显式前置关键字 (倍率: 1.5, 流量倍率: 2.0, ratio: 1.5)
  /(?:倍率|倍数|ratio)\s*[:：=]?\s*(\d+(?:\.\d+)?)/i,
  // 2. 流量后紧跟倍率 (流量: 1.5x, traffic: 2倍，必须带 x 或 倍，严禁单独数字)
  /(?:流量|traffic)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*[xX倍]/i,
  // 3. 数字紧跟 x/X 或 倍 (如 1.5x, 2X, 3倍，前驱非数字非点，后继非字母数字)
  /(?:^|[^\d.])(\d+(?:\.\d+)?)\s*(?:[xX]|倍)(?=$|[^\w])/i,
  // 4. 定界符括起的前置 x 倍率 (如 [x2], | x2, (x1.5))
  /(?:[|\[(])\s*[xX]\s*(\d+(?:\.\d+)?)(?=$|[\s\])|])/i,
  // 5. 显式带小数点的 x 倍率 (如 x1.5, x2.0)
  /(?:^|\s)[xX]\s*(\d+\.\d+)(?=$|[\s\])|])/i,
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

  // 顶层强制关闭 IPv6，彻底杜绝 Windows 无 IPv6 路由时的底层 connectex 10051 (unreachable network) 握手重试悬空
  config.ipv6 = false;

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
        "223.5.5.5",
        "119.29.29.29",
        "https://223.5.5.5/dns-query",
        "https://doh.pub/dns-query",
      ],
      "proxy-server-nameserver": [
        "223.5.5.5",
        "119.29.29.29",
        "https://223.5.5.5/dns-query",
        "https://doh.pub/dns-query",
      ],
      "direct-nameserver": [
        "223.5.5.5",
        "119.29.29.29",
        "system",
      ],
      "nameserver-policy": nameserverPolicy,
    };
  }

  // ==========================================================================
  // 第三步：策略组注入与零节点地区组物理剔除 (Linus: 好品味消除视觉噪音与死锁)
  // ==========================================================================
  const rawGroups = JSON.parse(JSON.stringify(SUBBOOST_PROXY_GROUPS));
  const cleanProxies = config.proxies || [];

  // 1. 扫描 6 核心地区策略组：若在已清洗节点池中物理节点数为 0，则物理剔除（不加入 groups 列表）
  const groups = [];
  for (const group of rawGroups) {
    if (group.type === "url-test" && group.filter) {
      const cleanFilter = group.filter.replace(/^\(\?i\)/, "");
      const cleanExclude = group["exclude-filter"] ? group["exclude-filter"].replace(/^\(\?i\)/, "") : null;
      let filterRe = null;
      let excludeRe = null;
      try {
        filterRe = new RegExp(cleanFilter, "i");
        excludeRe = cleanExclude ? new RegExp(cleanExclude, "i") : null;
      } catch (e) {
        // 若正则表达式解析异常，作为防御性安全跳过
      }
      const hasNodes = filterRe && cleanProxies.some(p => {
        if (!p || typeof p.name !== "string") return false;
        return filterRe.test(p.name) && (!excludeRe || !excludeRe.test(p.name));
      });
      if (!hasNodes) {
        // 当前订阅中无该地区物理节点，彻底跳过不生成，消除空组与测速死锁
        continue;
      }
    }
    groups.push(group);
  }

  // 2. 级联净化死链：自动抹去已被剔除的策略组及无效节点引用 (零死锁、零空组)
  const validGroupNames = new Set(groups.map(g => g.name));
  const validProxyNames = new Set(cleanProxies.map(p => p.name));
  const builtInTargets = new Set(["DIRECT", "REJECT", "PASS", "COMPATIBLE"]);
  const isValidTarget = name => validGroupNames.has(name) || validProxyNames.has(name) || builtInTargets.has(name);

  for (const group of groups) {
    if (Array.isArray(group.proxies)) {
      group.proxies = group.proxies.filter(isValidTarget);
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
        const clean = d.replace(/^(\+\.|\*\.)/, "");
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
