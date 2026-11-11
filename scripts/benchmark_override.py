"""离线测量 JS main 的延迟与独立 Node 进程峰值 RSS，输出 JSON。"""

import argparse
import json
from pathlib import Path
import platform
import subprocess


ROOT = Path(__file__).resolve().parent.parent
DRIVER = r"""
const {performance} = require('perf_hooks');
const [file, count, samples] = process.argv.slice(1);
const {main} = require(file);
const regions = ['香港', '日本', '美国', '狮城', '台湾', '韩国', '德国'];
function input() {
  return {proxies: Array.from({length: Number(count)}, (_, i) => ({
    name: regions[i % regions.length] + ' ' + i + (i % 10 === 0 ? ' [2x]' : ''),
    type: 'ss', server: '127.0.0.1', port: 443, cipher: 'aes-128-gcm', password: 'mock'
  }))};
}
for (let i = 0; i < 5; i++) main(input());
const times = [];
for (let i = 0; i < Number(samples); i++) {
  const config = input(); // 输入生成不计入 main 延迟
  const start = performance.now();
  const out = main(config);
  times.push(performance.now() - start);
  if (!out.proxies.length || !out.rules.length) throw Error('invalid output');
}
times.sort((a, b) => a - b);
const percentile = p => times[Math.ceil(times.length * p) - 1];
console.log(JSON.stringify({nodes: Number(count), samples: times.length,
  p50_ms: percentile(0.5), p95_ms: percentile(0.95),
  node_peak_rss_kib: process.resourceUsage().maxRSS, node: process.version}));
"""


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", nargs="+", type=positive_int, default=[100, 1000, 5000])
    parser.add_argument("--samples", type=positive_int, default=30)
    args = parser.parse_args()
    results = []
    for tier in ("minimal", "standard", "full"):
        # 固定使用公开模板，排除个人配置差异；每个场景用独立进程。
        file = ROOT / "override" / "example" / f"mihomoOverride.{tier}.example.js"
        for count in args.nodes:
            result = subprocess.run(
                ["node", "-e", DRIVER, str(file), str(count), str(args.samples)],
                check=True, capture_output=True, text=True, timeout=120,
            )
            results.append({"tier": tier, **json.loads(result.stdout)})
    print(json.dumps({"platform": platform.platform(), "results": results}, indent=2))


if __name__ == "__main__":
    main()
