import type { LoadBalanceStrategy } from "./config";

export type NodeRegion =
  | "us"
  | "hk"
  | "jp"
  | "sg"
  | "tw"
  | "kr"
  | "uk"
  | "de"
  | "fr"
  | "ca"
  | "au"
  | "other";

export type FilteredProxyGroupType = "select" | "url-test" | "fallback" | "load-balance" | "direct-first" | "reject-first";

export interface FilteredProxyGroup {
  id: string;
  // 仅用于 UI 展示（类似自定义分组的 emoji）；不参与筛选逻辑
  emoji?: string;
  name: string;
  enabled: boolean;
  groupType: FilteredProxyGroupType;
  strategy?: LoadBalanceStrategy;
  sourceIds: string[];
  regions: NodeRegion[];
  includeRegex?: string;
  excludeRegex?: string;
  // 按“当前展示名”精确排除的节点（仅作用于该筛选组）
  excludedNodeNames?: string[];
}
