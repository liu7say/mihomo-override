// =====================================================================
// 全局DNS统一覆写（合并版）
// 整合自三处配置，启用本覆写后可停用以下原有覆写：
//   1. 内置「DNS 覆写」（mihomo.yaml 的 dns 段）
//   2. 「国内DNS修复」（垃圾关键字清理 + captive 探测域名策略）
//   3. 「工作地址跳过」（内网域名/IP/进程直连规则 + 内网 DNS 策略）
//
// ⚠ 重要：启用本覆写时，必须停用「国内DNS修复」——
//   它会执行 delete config.dns，若排在本脚本之后将清空这里写入的完整配置。
//   「工作地址跳过」也建议一并停用（本脚本已完整包含其规则与 DNS 策略，
//   保留它只会造成规则重复，不影响正确性）。
// =====================================================================
function main(config) {
  // ===== 第一步：移除订阅自带的 dns 段（如 TAGMeta 的回环 DNS） =====
  delete config.dns;

  // ===== 第二步：写入合并后的完整 DNS 配置 =====
  // 来源：内置 DNS 覆写（mihomo.yaml）+ 国内DNS修复 + 工作地址跳过
  config.dns = {
    enable: true,

    // —— 基础设置（源自内置 DNS 覆写） ——
    ipv6: false,
    "enhanced-mode": "fake-ip",
    "fake-ip-range": "198.18.0.1/16",
    "fake-ip-filter-mode": "blacklist",
    // ⚠ 绝不能有 "*"：它会让 fake-ip-filter 变成「全域名排除」，
    //   等于全局关闭 Fake-IP，所有域名都拿真实 IP —— 既拖慢 CDN 解析，
    //   又会让 Steam 商店拿到被污染的国外 IP。
    // 这里只列真正需要真实 IP 的域名：内网、工作域名、NTP/连通性探测，
    // 以及 Steam 区服握手与下载域名（保持 IPCountry = CN，下载走国内 CDN）。
    "fake-ip-filter": [
      "+.lan",
      "+.local",
      "time.*.com",
      "ntp.*.com",
      "+.market.xiaomi.com",
      // Steam 握手与下载服务器：拿真实国内 IP，保住 IPCountry=CN。
      // 注意只放行握手/下载，商店域名（store.steampowered.com 等）
      // 仍走 Fake-IP，避免商店 CDN 被解析到国外节点而加载失败。
      "cm.steampowered.com",
      "+.cm.steampowered.com",
      "+.steamserver.net",
      "+.steamcontent.com",
      // 工作域名直连白名单（从 config/private_work.json 或 customSubBoost.js 顶部自定义）
      // "+.corp.internal",
      // "+.company.com"
    ],
    "use-hosts": false,
    "use-system-hosts": true,
    "respect-rules": false,

    // —— 上游配置 ——
    // 引导 DNS（源自内置 DNS 覆写）
    // ⚠ 必须是纯 IP，不能带 tls:// 前缀。default-nameserver 的作用是
    //   「解析上游 DoH 服务器的域名」，它自己不做加密解析；
    //   写成 tls:// 会在解析上游之前就先要做一次 TLS 握手，形成循环依赖。
    "default-nameserver": [
      "223.5.5.5",
      "119.29.29.29"
    ],
    // 主上游 = 「国内DNS修复」的 223.5.5.5 DoH + doh.pub，并入内置覆写的阿里 DoH
    nameserver: [
      "https://223.5.5.5/dns-query",
      "https://doh.pub/dns-query",
      "https://dns.alidns.com/dns-query"
    ],
    // 节点域名解析 = 内置覆写的 DoT + 「工作地址跳过」的 119.29.29.29
    "proxy-server-nameserver": [
      "tls://223.5.5.5",
      "tls://223.6.6.6",
      "119.29.29.29"
    ],
    // 直连域名解析走系统 DNS（源自内置 DNS 覆写）
    "direct-nameserver": [
      "system"
    ],
    // 备用上游：与内置覆写一致，保持为空
    fallback: [],
    // 合并内置覆写的污染过滤 + 「工作地址跳过」的内网 IP 合法性声明
    "fallback-filter": {
      geoip: true,
      "geoip-code": "CN",
      ipcidr: [
        "240.0.0.0/4",
        "0.0.0.0/32"
      ],
      domain: [
        "+.google.com",
        "+.facebook.com",
        "+.youtube.com"
      ]
    },

    // —— 分流策略（域名 → 指定 DNS） ——
    // 「国内DNS修复」的 captive 网络认证探测域名（强制国内 DNS）
    // + 工作内网域名策略（可在 customSubBoost.js 或 private_work.json 中定义）
    "nameserver-policy": {
      "+.captive.apple.com,+.msftconnecttest.com,+.connect.rom.miui.com,+.connectivitycheck.gstatic.com,+.connectivitycheck.platform.hicloud.com": [
        "119.29.29.29",
        "223.5.5.5"
      ]
      // "+.corp.internal": "10.0.0.53"
    }
  };

  // ===== 第三步：局域网与工作地址直连规则 =====
  const workRules = [
    // 局域网与本地回环直连
    "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
    "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
    "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
    "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
    "IP-CIDR6,::1/128,DIRECT,no-resolve"
    // 工作专属规则（已统一移至 customSubBoost.js 顶部 CONFIG，避免 Git 泄露）
  ];

  // ⚠ 这里只保留工作内网规则，清空订阅自带的规则。
  //   原因：规则由「SubBoost 规则体系」YAML 覆写用 `rules+:` 追加，
  //   两边都写 rules 会互相覆盖 —— 整段替换时后执行的那份会把前一份清掉。
  //   覆写执行顺序：global 覆写按注册表从上到下，本 JS 在 SubBoost YAML 之前，
  //   所以本脚本先落地 29 条工作规则，SubBoost 再把它们之后的内容追加上去。
  config.rules = [...workRules];

  return config;
}
