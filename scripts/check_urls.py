"""逐个拉取覆写里声明的全部规则集，验证 URL 可用（这是 404 事故的复现点）。"""

import concurrent.futures as cf
import time
import urllib.request
from pathlib import Path

import yaml

SB = Path(__file__).parent
BASE_PREFIX = "https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo"


def head(url: str, timeout: int = 40, retries: int = 4) -> tuple[int, int, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "curl/8.0"})
    last = (0, 0, "")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.length or 0, ""
        except urllib.error.HTTPError as e:
            # 4xx 是确定性失败，重试无意义
            if e.code != 429:
                return e.code, 0, str(e.reason)
            last = (e.code, 0, "rate limited")
        except Exception as e:  # noqa: BLE001
            last = (0, 0, type(e).__name__ + ": " + str(e)[:70])
        time.sleep(2.5 * (attempt + 1))
    return last


def main() -> int:
    data = yaml.safe_load((SB / "subboost-override.yaml").read_text(encoding="utf-8"))
    providers = data["rule-providers"]

    items = []
    for pid, cfg in providers.items():
        path = cfg["url"].split("/geo/", 1)[1]  # 取出 geo/ 后面的相对路径
        items.append((pid, f"{BASE_PREFIX}/{path}", cfg["behavior"]))

    print(f"共 {len(items)} 个规则集，3 并发探测（带退避重试）\n")

    results = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(head, url): (pid, url, beh) for pid, url, beh in items}
        for fut in cf.as_completed(futs):
            pid, url, beh = futs[fut]
            code, size, err = fut.result()
            results.append((code, pid, beh, size, url, err))
            print(f"  [{code}] {pid}", flush=True)

    results.sort()
    bad = [r for r in results if r[0] != 200]
    total_bytes = sum(r[3] for r in results if r[0] == 200)

    print(f"200 OK: {len(results) - len(bad)} / {len(results)}   总体积约 {total_bytes / 1024 / 1024:.1f} MB")
    if bad:
        print("\n失败项：")
        for code, pid, beh, _, url, err in bad:
            print(f"  [{code}] {pid:26s} {beh:8s} {err}")
        return 1

    # 分组体积统计，看看谁最重
    print("\n体积最大的 10 个：")
    for code, pid, beh, size, url, _ in sorted(results, key=lambda x: -x[3])[:10]:
        print(f"  {size / 1024:>8.0f} KB  {beh:8s} {pid}")

    print("\n按类型统计：")
    for beh in ("domain", "ipcidr"):
        sel = [r for r in results if r[2] == beh]
        print(f"  {beh:8s} {len(sel):>3} 个  {sum(r[3] for r in sel) / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
