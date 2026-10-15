/**
 * ==============================================================================
 * SubBoost 上游参考：信息节点识别逻辑 (info-node-name.ts)
 * ==============================================================================
 * 
 * 【背景与意图】
 * 许多机场订阅往往会将账户元数据（如剩余流量、重置倒计时、套餐到期日、官网公告等）
 * 伪装/编码为一个独立的 Proxy 代理节点。
 * 
 * 【处理策略】
 * 这些节点在主选择列表（节点选择/手动切换）中应当保留可见以供用户查阅账户状态；
 * 但【严禁】将其划入 url-test（自动选择、地区测速）或 fallback 自动故障转移组中，
 * 否则测速流量会向这些假节点发包，导致测速全部超时或出现异常分流。
 */

// 1. 常见以到期时间、剩余流量引导的冒号格式正则
const SUBSCRIPTION_INFO_NODE_NAME_RE =
  /^(剩余流量|剩余订阅流量|距离下次重置剩余|套餐到期|订阅到期|到期时间|过期时间)\s*[:：]/;

// 2. 常见以竖线分隔的余额或会员级别格式正则 (例: "余额 | 100元")
const PIPE_STYLE_ACCOUNT_INFO_NODE_NAME_RE = /^(余额|会员)\s*\|/;

// 3. 常见的客户端版本过低、提示更新类软件公告正则
const SUBSCRIPTION_UPDATE_HINT_NODE_NAME_RE = /(版本太旧|请更新|更新软件|去官网更新)/;

/**
 * 判定指定节点名称是否属于非代理用途的账户信息/公告节点
 * @param name 节点原始名称
 * @returns true: 属于信息提示节点; false: 属于正常代理节点
 */
export function isSubscriptionInfoNodeName(name: string): boolean {
  const trimmed = name.trim();
  return (
    SUBSCRIPTION_INFO_NODE_NAME_RE.test(trimmed) ||
    PIPE_STYLE_ACCOUNT_INFO_NODE_NAME_RE.test(trimmed) ||
    SUBSCRIPTION_UPDATE_HINT_NODE_NAME_RE.test(trimmed)
  );
}
