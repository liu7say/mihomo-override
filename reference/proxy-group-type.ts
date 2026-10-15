/**
 * ==============================================================================
 * SubBoost 上游参考：策略组类型与工厂构建函数 (proxy-group-type.ts)
 * ==============================================================================
 * 
 * 【功能说明】
 * 提供根据业务声明的 groupType（select、url-test、fallback、load-balance 等）
 * 将抽象策略配置实例化为 Mihomo / Clash 规范对象的工厂方法与节点去重工具。
 */

import {
  DEFAULT_LOAD_BALANCE_STRATEGY,
  type LoadBalanceStrategy,
  type ProxyGroup,
  type ProxyGroupGroupType,
} from "@subboost/core/types/config";

/** 构建策略组参数选项 */
type BuildTypedProxyGroupOptions = {
  name: string;
  groupType: ProxyGroupGroupType;
  proxies: string[];
  testUrl: string;
  testInterval: number;
  strategy?: LoadBalanceStrategy;
  extraFields?: Record<string, unknown>;
  urlTestLazy?: boolean;
};

/**
 * 数组去重函数：保持原有顺序，过滤空值与重复节点名称
 * @param values 原始节点名称列表
 * @returns 去重后的节点名称列表
 */
export function uniqueProxyNames(values: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    if (!value || seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

/**
 * 根据类型工厂构建标准 Mihomo 策略组对象
 */
export function buildTypedProxyGroup({
  name,
  groupType,
  proxies,
  testUrl,
  testInterval,
  strategy,
  extraFields = {},
  urlTestLazy = false,
}: BuildTypedProxyGroupOptions): ProxyGroup {
  // 基础默认模型为 select 选择组
  const base: ProxyGroup = {
    name,
    type: "select",
    proxies,
    ...extraFields,
  };

  switch (groupType) {
    case "url-test":
      // 自动测速组：注入测速目标与间隔，支持 lazy 懒加载
      return {
        ...base,
        type: "url-test",
        url: testUrl,
        interval: testInterval,
        lazy: urlTestLazy,
      };
    case "fallback":
      // 故障回退组：主节点不可用时依次后退
      return {
        ...base,
        type: "fallback",
        url: testUrl,
        interval: testInterval,
      };
    case "load-balance":
      // 负载均衡组：支持 consistent-hashing 或 round-robin
      return {
        ...base,
        type: "load-balance",
        strategy: strategy || DEFAULT_LOAD_BALANCE_STRATEGY,
        url: testUrl,
        interval: testInterval,
      };
    case "select":
    case "direct-first":
    case "reject-first":
    default:
      // 其余派生类型均收敛为标准 select 策略组
      return base;
  }
}
