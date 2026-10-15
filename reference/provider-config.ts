/**
 * ==============================================================================
 * SubBoost 上游参考：规则提供者与分类元数据配置 (provider-config.ts)
 * ==============================================================================
 * 
 * 【背景说明】
 * 定义了 MetaCubeX/meta-rules-dat 远程规则集仓库的基础拉取路径、目录划分
 * 以及全部 15 个分流业务分类（广告、AI、流媒体、游戏、金融等）的中英文对照与 Emoji。
 * 
 * ⚠ 落地适配注意：
 * 原版 SubBoost 使用的是 raw.githubusercontent.com 直连地址；
 * 在大陆网络环境下，本覆写项目通过生成器将其全部无缝重定向至 fastly.jsdelivr.net 高可用 CDN 镜像。
 */

export const RULE_PROVIDER_CONFIG = {
  // 规则集上游 Git 根地址（官方默认 raw）
  baseUrl: "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo",
  github: {
    owner: "MetaCubeX",
    repo: "meta-rules-dat",
    ref: "meta",
  },
  treePath: "geo",
  // 规则集两大子目录：geosite (域名规则) 与 geoip (IP/CIDR 规则)
  directories: {
    geosite: "geosite",
    geoip: "geoip",
  },
  // 本地缓存过期时间（默认 24 小时）
  cacheTtlMs: 24 * 60 * 60 * 1000,
  // 业务分类定义与视觉展示
  categories: {
    ads: { name: "广告拦截", emoji: "🛑" },
    ai: { name: "AI 服务", emoji: "🤖" },
    common: { name: "常用服务", emoji: "🌐" },
    media: { name: "流媒体", emoji: "🎬" },
    social: { name: "社交通讯", emoji: "💬" },
    game: { name: "游戏平台", emoji: "🎮" },
    tech: { name: "技术服务", emoji: "🛠️" },
    finance: { name: "金融服务", emoji: "💰" },
    geo: { name: "地理位置", emoji: "🗺️" },
    edu: { name: "教育学术", emoji: "🎓" },
    shopping: { name: "购物电商", emoji: "🛍️" },
    news: { name: "新闻资讯", emoji: "📰" },
    cn: { name: "中国服务", emoji: "🇨🇳" },
    privacy: { name: "隐私安全", emoji: "🔒" },
    other: { name: "其他", emoji: "✨" },
  },
} as const;

export const DEFAULT_RULE_PROVIDER_BASE_URL = RULE_PROVIDER_CONFIG.baseUrl;
export const RULE_CATEGORIES = RULE_PROVIDER_CONFIG.categories;
export type RuleCategory = keyof typeof RULE_CATEGORIES;
