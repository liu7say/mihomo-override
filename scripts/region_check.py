"""用真实订阅节点验证地区 filter 的准确度。

对比三套：
  A. 官方 REGION_PRESETS 原样（includes 子串匹配）
  B. 本覆写的 filter（含 \\b 词边界 + exclude-filter）
  C. GPT 那份覆写的裸缩写写法（作为反面参照）
"""

import glob
import os
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gen_override import REGIONS, JUNK  # noqa: E402

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
ROOT = Path(os.environ.get("MIHOMO_PARTY_BASE") or (Path.home() / "AppData" / "Roaming" / "mihomo-party"))

# 官方 REGION_PRESETS 关键词（proxy-group-advanced.ts）
OFFICIAL = {
    "us": ["美国", "US", "USA", "United States", "洛杉矶", "纽约", "西雅图"],
    "hk": ["香港", "HK", "Hong Kong", "港"],
    "jp": ["日本", "JP", "Japan", "东京", "大阪"],
    "sg": ["新加坡", "SG", "Singapore", "狮城"],
    "tw": ["台湾", "TW", "Taiwan", "台北"],
    "kr": ["韩国", "KR", "Korea", "首尔"],
}
# 各地区「真正应该属于它」的判定（人工标注，作为基准）
TRUTH = {
    "美国节点": re.compile(r"美国|洛杉矶|纽约|西雅图|圣何塞|圣克拉拉|硅谷|拉斯维加斯|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|芝加哥|United States|USA|\bUS\b"),
    "香港节点": re.compile(r"香港|Hong ?Kong|HKG|\bHK\b|🇭🇰"),
    "日本节点": re.compile(r"日本|东京|大阪|Japan|Tokyo|Osaka|\bJP\b|🇯🇵"),
    "狮城节点": re.compile(r"新加坡|狮城|Singapore|\bSG\b|🇸🇬"),
    "台湾节点": re.compile(r"台湾|台北|台中|新北|彰化|Taiwan|Taipei|Kaohsiung|\bTW\b|🇹🇼"),
    "韩国节点": re.compile(r"韩国|首尔|Korea|\bKR\b|🇰🇷"),
}
# 已知会误命中的"其他地区"标记
# 注意：Los Angeles / Santiago 这类必须排除在"其他地区"之外 ——
# 洛杉矶是美国城市（US-Los Angeles 是标准美区节点名），
# 把它们算作误命中会让基准本身出错。
OTHER_REGION = re.compile(
    r"Australia|澳洲|俄罗斯|Russia|Belarus|白俄罗斯|巴西|Brazil|英国|United Kingdom|伦敦|London|"
    r"德国|Germany|法国|France|加拿大|Canada|荷兰|Netherlands|印度|India|土耳其|Thailand|泰国|"
    r"马来|Malaysia|越南|Vietnam|菲律宾|Indonesia|印尼|阿根廷|墨西哥|Mexico|南非|South Africa|"
    r"Chile|Chilean|Santiago"
)


def official_match(name: str, region: str) -> bool:
    low = name.lower()
    return any(kw.lower() in low for kw in OFFICIAL[region])


def main() -> int:
    print("=" * 78)
    print("地区 filter 准确度对比（真实订阅节点）")
    print("=" * 78)

    profiles = sorted(glob.glob(str(ROOT / "profiles" / "*.yaml")))
    total_nodes = 0
    agg = {r["name"]: {"official_wrong": [], "mine_wrong": []} for r in REGIONS}

    for pf in profiles:
        try:
            data = yaml.safe_load(Path(pf).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        names = [p["name"] for p in (data.get("proxies") or [])]
        if not names:
            continue
        pid = Path(pf).stem
        print(f"\n【{pid}】{len(names)} 节点")

        junk_re = re.compile(JUNK)
        for r in REGIONS:
            gname = r["name"]
            mine = re.compile(r["filter"])
            exc = re.compile(r["exclude"]) if r.get("exclude") else None
            rid = {"美国节点": "us", "香港节点": "hk", "日本节点": "jp",
                   "狮城节点": "sg", "台湾节点": "tw", "韩国节点": "kr"}[gname]
            truth = TRUTH[gname]

            clean = [n for n in names if not junk_re.search(n)]
            mine_hits = [n for n in clean if mine.search(n) and not (exc and exc.search(n))]
            off_hits = [n for n in clean if official_match(n, rid)]

            # 误命中 = 命中了但名字里没有该地区标识，或明确是别的地区
            off_bad = [n for n in off_hits if not truth.search(n) or OTHER_REGION.search(n)]
            mine_bad = [n for n in mine_hits if not truth.search(n) or OTHER_REGION.search(n)]

            agg[gname]["official_wrong"].extend(off_bad)
            agg[gname]["mine_wrong"].extend(mine_bad)

            flag = "" if not mine_bad else "  ← 有残留误命中"
            print(f"  {gname:10s} 官方命中{len(off_hits):>3}(误{len(off_bad):>2})  "
                  f"本覆写命中{len(mine_hits):>3}(误{len(mine_bad):>2}){flag}")
            if off_bad:
                print(f"      官方误命中示例: {off_bad[:4]}")
            if mine_bad:
                print(f"      本覆写误命中:   {mine_bad[:4]}")

        total_nodes += len(names)

    print("\n" + "=" * 78)
    print(f"汇总（{len(profiles)} 个订阅文件）")
    print("=" * 78)
    print(f"{'地区组':<12s} {'官方误命中':>10s} {'本覆写误命中':>12s}")
    to = tm = 0
    for gname, v in agg.items():
        o = len(set(v["official_wrong"]))
        m = len(set(v["mine_wrong"]))
        to += o
        tm += m
        mark = "  ✓" if m == 0 else ""
        print(f"{gname:<12s} {o:>10d} {m:>12d}{mark}")
    print(f"{'合计':<12s} {to:>10d} {tm:>12d}")
    print(f"\n误命中减少 {to - tm} 个（{(1 - tm / to) * 100:.0f}%）" if to else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
