// 节点清理（垃圾关键字 + 高倍率节点）合并版
// 合并自「移除垃圾关键字节点」与「高倍率节点清除」两个覆写，逻辑与原版完全一致：
// 1. 按关键字正则过滤公告类垃圾节点（剩余流量/到期/官网/套餐等）
// 2. 按名称识别倍率（2x、x2、2.5倍、倍率：3 等格式），移除倍率大于 1 的节点
// 3. 同步清理策略组中对已移除节点的引用，避免内核启动报错
function main(config) {
  // ===== 第一部分：垃圾关键字过滤 =====
  const trashRegex = /剩余流量|到期|过期|官网|套餐|永久地址|Telegram群组|如遇节点失效|欢迎加入|Traffic|Expire/i;

  // ===== 第二部分：高倍率识别 =====
  const MAX_MULTIPLIER = 1;

  function getMultiplier(name) {
    if (typeof name !== 'string') return null;

    const patterns = [
      // 2x / 2.5x / 2 X / 2X（数字在前）
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*[xX](?=$|[^\w])/,
      // x2 / X2 / x 2.5（字母在前）
      // 边界不含连字符：避免误删 IEPL-X2 这类线路代号（X2 是编号不是倍率）
      /(?:^|[^\w-])[xX]\s*(\d+(?:\.\d+)?)(?=$|[^\w])/,
      // 2倍 / 2.5倍 / 2 倍
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*倍(?=$|[^\w])/,
      // 倍率2 / 倍率：2 / 倍率 2.5
      /倍率\s*[:：=]?\s*(\d+(?:\.\d+)?)/i,
      // 2x流量 / 2倍流量
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*[xX]\s*(?:流量|traffic)\b/i,
      /(?:^|[^\w])(\d+(?:\.\d+)?)\s*倍\s*(?:流量|traffic)\b/i,
      // 流量2倍 / traffic 2x
      /(?:流量|traffic)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*[xX倍]?/i,
      // x2流量 / X2流量（字母在前的流量标注，同样排除连字符前界）
      /(?:^|[^\w-])[xX]\s*(\d+(?:\.\d+)?)\s*(?:流量|traffic)\b/i,
    ];

    for (const regex of patterns) {
      const match = name.match(regex);
      if (!match) continue;

      const value = Number(match[1]);
      if (Number.isFinite(value) && value >= 0) {
        return value;
      }
    }

    return null;
  }

  // ===== 过滤底层节点列表 (proxies) =====
  const removedNames = new Set();

  if (Array.isArray(config.proxies)) {
    config.proxies = config.proxies.filter(proxy => {
      if (!proxy || typeof proxy.name !== 'string') {
        return true;
      }

      // 命中垃圾关键字，移除
      if (trashRegex.test(proxy.name)) {
        removedNames.add(proxy.name);
        return false;
      }

      // 倍率大于 1，移除；无法确认倍率则保留
      const multiplier = getMultiplier(proxy.name);
      if (multiplier !== null && multiplier > MAX_MULTIPLIER) {
        removedNames.add(proxy.name);
        return false;
      }

      return true;
    });
  }

  // ===== 同步清理策略组 (proxy-groups) 中的节点引用 =====
  // 关键步骤：不在策略组里同步删掉这些名字，Clash 启动会报错
  if (Array.isArray(config["proxy-groups"])) {
    for (const group of config["proxy-groups"]) {
      if (!Array.isArray(group.proxies)) continue;

      group.proxies = group.proxies.filter(name => {
        // 同时按关键字正则与已移除名单过滤（正则兜底，兼容组内存在而 proxies 中不存在的名字）
        return !removedNames.has(name) && !trashRegex.test(name);
      });
    }
  }

  return config;
}
