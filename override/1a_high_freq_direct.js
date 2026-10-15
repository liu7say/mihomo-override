/**
 * ==============================================================================
 * 高频国内直连与内网前置极速分流覆写 (1a_high_freq_direct.js)
 * ==============================================================================
 * 
 * 【设计定位与性能意义】
 * 针对 PERFORMANCE.md 痛点 2 深度优化：
 * 大陆用户日常 80% 的高频网络访问（微信、QQ、B站、淘宝、京东、网易、百度、抖音等）
 * 在 SubBoost 默认规则链中必须串行遍历穿透 150 条代理规则后，才在 geolocation-cn 命中直连。
 * 
 * 本脚本作为【第一顺位 (注册表最前)】前置覆写执行：
 * 1. 初始化并注入局域网私有网段 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.1/8 等)
 * 2. 注入绝无歧义的大陆主流大厂核心域名与 CDN 后缀
 * 3. 从而使 80% 的日常数据包在规则链第 1 行即刻命中 DIRECT 闪电放行，彻底消除穿透延迟！
 * 
 * 随后后置的 customSubBoost.yaml 通过 `rules+:` 在其后安全追加其余全球分流规则。
 */

function main(config) {
  // 1. 基础局域网与本地回环直连规则
  const privateRules = [
    "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
    "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
    "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
    "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
  ];

  // 2. 绝无歧义的大陆超高频直连顶级域名与核心服务白名单
  const highFreqCnRules = [
    // 腾讯系 (微信、QQ、腾讯视频、腾讯云)
    "DOMAIN-SUFFIX,qq.com,DIRECT",
    "DOMAIN-SUFFIX,weixin.qq.com,DIRECT",
    "DOMAIN-SUFFIX,tenpay.com,DIRECT",
    "DOMAIN-SUFFIX,qpic.cn,DIRECT",
    "DOMAIN-SUFFIX,qlogo.cn,DIRECT",

    // 阿里系 (淘宝、天猫、支付宝、阿里云)
    "DOMAIN-SUFFIX,taobao.com,DIRECT",
    "DOMAIN-SUFFIX,tmall.com,DIRECT",
    "DOMAIN-SUFFIX,alipay.com,DIRECT",
    "DOMAIN-SUFFIX,alicdn.com,DIRECT",
    "DOMAIN-SUFFIX,aliyun.com,DIRECT",

    // 字节跳动系 (抖音、头条、飞书)
    "DOMAIN-SUFFIX,douyin.com,DIRECT",
    "DOMAIN-SUFFIX,bytedance.com,DIRECT",
    "DOMAIN-SUFFIX,pstatp.com,DIRECT",

    // 京东
    "DOMAIN-SUFFIX,jd.com,DIRECT",
    "DOMAIN-SUFFIX,360buyimg.com,DIRECT",

    // 哔哩哔哩 (B站)
    "DOMAIN-SUFFIX,bilibili.com,DIRECT",
    "DOMAIN-SUFFIX,hdslb.com,DIRECT",
    "DOMAIN-SUFFIX,biliapi.net,DIRECT",

    // 网易系 (网易云音乐、网易新闻)
    "DOMAIN-SUFFIX,163.com,DIRECT",
    "DOMAIN-SUFFIX,126.net,DIRECT",
    "DOMAIN-SUFFIX,music.163.com,DIRECT",

    // 百度
    "DOMAIN-SUFFIX,baidu.com,DIRECT",
    "DOMAIN-SUFFIX,bdimg.com,DIRECT",

    // 美团 / 拼多多
    "DOMAIN-SUFFIX,meituan.com,DIRECT",
    "DOMAIN-SUFFIX,pinduoduo.com,DIRECT",
    "DOMAIN-SUFFIX,yangkeduo.com,DIRECT",
  ];

  // 用户本地企业/工作内网规则扩展槽位：
  const customCompanyRules = [
    // "DOMAIN-SUFFIX,corp.internal,DIRECT",
  ];

  // 初始化 config.rules：前置直连规则整段就位
  // 后续由 customSubBoost.yaml 的 rules+: 追加其余 126 条全球分流规则
  config.rules = [
    ...privateRules,
    ...highFreqCnRules,
    ...customCompanyRules,
  ];

  return config;
}
