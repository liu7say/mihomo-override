"""核对图标名是否存在于 Qure 图标集，并用语义相近的图标替换不存在的。

数据源：本地缓存的 GitHub API 目录清单（347 个 Color 图标），
不靠逐个 HTTP 试错，避免 jsdelivr 限流导致误判。
"""

import json
import re
import sys
from pathlib import Path

# 确保在 Windows 控制台环境下输出 UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

# 项目根目录与 reference 目录推导
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
QURE_NAMES_FILE = REPO_ROOT / "reference" / "qure_names.txt"
if not QURE_NAMES_FILE.exists():
    QURE_NAMES_FILE = HERE / "qure_names.txt"

# 加载本地缓存的 Qure 图标名集合（共 347 个 Color 图标）
AVAILABLE = {
    Path(p).stem
    for p in QURE_NAMES_FILE.read_text(encoding="utf-8").split("\n")
    if p.strip()
}


# 生成器里当前使用的映射（模块 id -> 图标名）
CURRENT = {
    "select": "Proxy", "auto": "Auto", "ad": "AdBlack",
    "private": "Home", "cn": "Direct", "global": "Global", "final": "Final",
    "ai": "AI", "gemini": "AI", "youtube": "YouTube", "google": "Google_Search",
    "microsoft": "Microsoft", "apple": "Apple", "telegram": "Telegram",
    "twitter": "Twitter", "meta": "Facebook", "discord": "Discord",
    "social-other": "SocialMedia", "netflix": "Netflix", "disney": "Disney",
    "streaming-west": "ForeignMedia", "streaming-asia": "AsianMedia",
    "steam": "Game", "gaming-pc": "Game", "gaming-console": "Game",
    "github": "GitHub", "cloud": "Cloud", "dev-tools": "DevTools",
    "storage": "Drive", "payment": "PayPal", "crypto": "Bitcoin",
    "google-scholar": "Google_Scholar", "education": "Education",
    "news": "News", "shopping": "Shopping", "adult": "Adult",
}

# 替换方案：按优先级排列，第一个存在于清单里就用它
# 全部候选都来自 Qure Color 清单（347 个），已逐个核对存在性
CANDIDATES = {
    "select":        ["Proxy", "Auto", "Available"],
    "auto":          ["Auto", "Available_1", "Available"],
    "ad":            ["AdBlack", "Advertising", "AdWhite"],
    "private":       ["Lock", "Available", "Direct"],
    "cn":            ["CN", "China", "Direct"],
    "global":        ["Global", "World_Map", "Available"],
    "final":         ["Final", "Available"],
    "ai":            ["AI", "ChatGPT", "OpenAI"],
    "gemini":        ["AI", "ChatGPT"],
    "youtube":       ["YouTube", "AbemaTV", "Streaming"],
    "google":        ["Google", "Gmail", "GCP"],
    "microsoft":     ["Microsoft", "Office", "OneDrive"],
    "apple":         ["Apple", "iCloud", "App_Store"],
    "telegram":      ["Telegram", "Telegram_X", "Line"],
    "twitter":       ["Twitter", "Telegram_X"],
    "meta":          ["Facebook", "Instagram", "Facebook_1"],
    "discord":       ["Discord", "Line", "Telegram"],
    "social-other":  ["Line", "WeChat", "Telegram"],
    "netflix":       ["Netflix", "ForeignMedia"],
    "disney":        ["Disney", "Apple_TV_Plus", "ITV"],
    "streaming-west":["ForeignMedia", "Netflix", "Prime_Video"],
    "streaming-asia":["AbemaTV", "KKTV", "DomesticMedia"],
    "steam":         ["Steam", "Game", "Epic_Games"],
    "gaming-pc":     ["Game", "Steam", "Epic_Games"],
    "gaming-console":["Xbox", "PlayStation", "Game"],
    "github":        ["GitHub", "GitHub_Letter"],
    "cloud":         ["Server", "Azure", "Cloudflare"],
    "dev-tools":     ["App_Store", "GitHub", "Star"],
    "storage":       ["OneDrive", "iCloud", "Google_Drive"],
    "payment":       ["PayPal", "Available"],
    "crypto":        ["PayPal", "Available_1", "Available"],
    "google-scholar":["Scholar", "Bookpedia", "Available"],
    "education":     ["Scholar", "Bookpedia", "Available_1"],
    "news":          ["Media", "Apple_News", "Available"],
    "shopping":      ["Amazon", "Taobao", "Alibaba"],
    "adult":         ["Pornhub", "Available"],
}


def resolve() -> tuple[dict, list, list]:
    resolved, missing, changed = {}, [], []
    for mid, cur in CURRENT.items():
        cands = CANDIDATES.get(mid, [cur])
        pick = next((c for c in cands if c in AVAILABLE), None)
        if pick is None:
            # 兜底：用清单里第一个语义无关但肯定存在的，作为最后手段
            pick = next(iter(sorted(AVAILABLE)), "Auto")
            missing.append((mid, cur, "无合适候选，临时兜底"))
        resolved[mid] = pick
        if pick != cur:
            changed.append((mid, cur, pick))
    return resolved, missing, changed


def main() -> None:
    print(f"Qure Color 图标集共 {len(AVAILABLE)} 个\n")

    missing_now = {mid: ic for mid, ic in CURRENT.items() if ic not in AVAILABLE}
    print(f"当前映射中不存在的图标：{len(missing_now)} / {len(CURRENT)}")
    for mid, ic in sorted(missing_now.items()):
        print(f"  {mid:16s} {ic}.png  ✗")

    print()
    resolved, missing, changed = resolve()
    print(f"替换方案生效 {len(changed)} 处：")
    for mid, old, new in sorted(changed):
        flag = "⚠ 兜底" if new not in AVAILABLE else "✓"
        print(f"  {mid:16s} {old:18s} → {new:16s} {flag}")

    if missing:
        print("\n未能语义匹配（用了兜底图标）：")
        for mid, old, why in missing:
            print(f"  {mid:16s} {why}")

    uniq = sorted(set(resolved.values()))
    print(f"\n最终使用 {len(uniq)} 个不同图标，全部确认存在于清单：")
    print("  " + ", ".join(uniq))

    out = REPO_ROOT / "reference" / "icon_map.json"
    out.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写出 {out}")



if __name__ == "__main__":
    main()
