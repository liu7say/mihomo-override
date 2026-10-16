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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "手动切换",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Available_1.png",
    "type": "select",
    "include-all": true,
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新"
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新|(?i)Australia|俄罗斯|Russia|Belarus|巴西|Brazil",
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新",
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新",
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新",
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新|(?i)Network|Software|Westward",
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
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新",
    "url": "https://www.gstatic.com/generate_204",
    "interval": 600,
    "tolerance": 50,
    "lazy": true
  },
  {
    "name": "其他国家",
    "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/World_Map.png",
    "type": "select",
    "proxies": [
      "DIRECT"
    ],
    "include-all": true,
    "exclude-filter": "^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\\s*[:：]|^(余额|会员)\\s*\\||版本太旧|请更新|更新软件|去官网更新|(?i)美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|United.?States|(?:^|[^a-zA-Z])US(?:[^a-zA-Z]|$)|香港|Hong.?Kong|HKG|(?:^|[^a-zA-Z])HK(?:[^a-zA-Z]|$)|日本|东京|大阪|川日|沪日|深日|泉日|埼玉|Japan|Tokyo|Osaka|(?:^|[^a-zA-Z])JP(?:[^a-zA-Z]|$)|新加坡|狮城|Singapore|(?:^|[^a-zA-Z])SG(?:[^a-zA-Z]|$)|台湾|台北|台中|新北|彰化|Taiwan|Taipei|Kaohsiung|(?:^|[^a-zA-Z])TW(?:[^a-zA-Z]|$)|韩国|首尔|韓|Korea|KOR|(?:^|[^a-zA-Z])KR(?:[^a-zA-Z]|$)"
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
  const trashRegex = /剩余流量|到期|过期|官网|套餐|永久地址|Telegram群组|如遇节点失效|欢迎加入|Traffic|Expire/i;

  function getMultiplier(name) {
    if (typeof name !== "string") return null;
    const patterns = [
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*[xX](?=$|[^\w])/,
      /(?:^|[^\w-])[xX]\s*(\d+(?:\.\d+)?)(?=$|[^\w])/,
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*倍(?=$|[^\w])/,
      /倍率\s*[:：=]?\s*(\d+(?:\.\d+)?)/i,
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*[xX]\s*(?:流量|traffic)\b/i,
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*倍\s*(?:流量|traffic)\b/i,
      /(?:流量|traffic)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*[xX倍]?/i,
      /(?:^|[^\w-])[xX]\s*(\d+(?:\.\d+)?)\s*(?:流量|traffic)\b/i,
    ];
    for (const regex of patterns) {
      const match = name.match(regex);
      if (!match) continue;
      const val = Number(match[1]);
      if (Number.isFinite(val) && val >= 0) return val;
    }
    return null;
  }

  const removedNames = new Set();
  if (CONFIG.cleanTrashNodes || CONFIG.cleanHighMultiplier) {
    config.proxies = config.proxies.filter(proxy => {
      if (!proxy || typeof proxy.name !== "string") return true;

      // 规则 A: 命中垃圾公告关键字，移除
      if (CONFIG.cleanTrashNodes && trashRegex.test(proxy.name)) {
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
  }

  // ==========================================================================
  // 第二步：全局 DNS 与 Fake-IP 体系构建 (按 CONFIG 动态执行)
  // ==========================================================================
  if (CONFIG.enableDnsOverride) {
    delete config.dns;

    // Fake-IP 绕过列表
    const fakeIpFilters = [
      "+.lan",
      "+.local",
      "time.*.com",
      "ntp.*.com",
      "+.market.xiaomi.com",
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

    const fallbackFilterDomains = [
      "+.google.com",
      "+.facebook.com",
      "+.youtube.com",
    ];
    if (CONFIG.enableWorkRules && Array.isArray(CONFIG.workDomains)) {
      for (const d of CONFIG.workDomains) {
        if (!d) continue;
        const pattern = d.startsWith("+.") || d.startsWith("*.") ? d : "+." + d;
        if (!fallbackFilterDomains.includes(pattern)) fallbackFilterDomains.push(pattern);
      }
    }

    const nameserverPolicy = {
      "+.captive.apple.com,+.msftconnecttest.com,+.connect.rom.miui.com,+.connectivitycheck.gstatic.com,+.connectivitycheck.platform.hicloud.com": [
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
        "tls://223.5.5.5",
        "tls://223.6.6.6",
        "119.29.29.29",
      ],
      "direct-nameserver": ["system"],
      fallback: [],
      "fallback-filter": {
        geoip: true,
        "geoip-code": "CN",
        ipcidr: ["240.0.0.0/4", "0.0.0.0/32"],
        domain: fallbackFilterDomains,
      },
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
        rules.push("IP-CIDR," + ip + ",DIRECT");
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
