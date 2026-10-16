<div align="center">

# mihomo-override

**Industrial-grade All-in-One Rule Override & Multi-tier Preset System**

Engineered for **Clash Party**, **Flclash**, **bettbox**, and **Sparkle** clients powered by the **Mihomo (Clash.Meta)** kernel.

[![Release](https://img.shields.io/github/v/release/liu7say/mihomo-override?style=flat-square&color=blue)](https://github.com/liu7say/mihomo-override/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Kernel](https://img.shields.io/badge/Kernel-Mihomo%20Meta-orange?style=flat-square)](https://github.com/MetaCubeX/mihomo)
[![CI Build](https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square)](https://github.com/liu7say/mihomo-override/actions)

[English](README_EN.md) | [简体中文](README.md)

</div>

---

## Introduction

**mihomo-override** is a high-performance, fully-contained rule override engineering solution tailored for the Mihomo (Clash.Meta) ecosystem.

Traditional rule overrides often suffer from fragile multi-file ordering dependencies, bootstrap deadlocks (TLS EOF errors) during cold startup, ping storms overwhelming router NAT tables, and UI lag on mobile devices caused by dozens of proxy groups. This project resolves these issues through a deterministic generator and defensive runtime execution across multiple hardware tiers.

---

## Key Advantages & Engineering Highlights

| Feature | Problem in Traditional Overrides | Solution in This Project | Practical Benefit |
|---|---|---|---|
| **Zero Cold-start Deadlock** | Rulesets routed through proxies fail to download during initialization (TLS EOF / Timeout) | Decoupled rule-provider fetching to `DIRECT` with high-availability CDN mirrors | Sub-second client startup; zero 429 rate limit or SSL negotiation errors |
| **No Health-check Storms** | Frequent concurrent pings across dozens of groups flood router connection tables | Fully adopted `lazy: true`, `tolerance: 50ms`, and `interval: 600s` | Eliminates idle bandwidth waste and connection jitter in gaming/streaming |
| **All-in-One Single Script** | Dispersed across 3 scripts with strict order dependencies; rule clearing on misorder | Fused into a single ES6 script: DNS override + node cleaning + group assembly | Copy-and-paste portability; zero foreign dependencies; no broken references |
| **Multi-tier Presets Matrix** | A monolithic 41-group config causes rendering lag and battery drain on mobile | Standalone compiled outputs for `Minimal`, `Standard`, and `Full` tiers + YAML fallback | Smooth scrolling on phones; full-spectrum granular control on desktop |
| **Zero Leak Security** | Private corporate domains, intranet DNS, and CIDRs risk accidental git commits | Local private configs isolated via `.gitignore`; public repo tracks only sanitized templates | Absolute enterprise privacy security |

---

## Multi-tier Preset Decision Matrix

Select the preset that best matches your client hardware and routing requirements:

| Preset Tier | Proxy Groups | Rule Providers | Rule Entries | Memory Footprint | Recommended Devices & Use Cases |
|---|:---:|:---:|:---:|:---:|---|
| **Minimal** | 16 | 12 | 55 | ~25 MB | **Mobile & TV Boxes**: Android, iOS, Bettbox, smart TVs; ultra-low power consumption and buttery smooth UI |
| **Standard** | 23 | 24 | 67 | ~45 MB | **Recommended Daily Driver**: Mainstream streaming (YouTube, Netflix, Disney+), Google, Microsoft, and AI services |
| **Full** | 41 | 94 | 137 | ~75 MB | **Desktop & Soft Routers**: Windows, macOS, Linux; comprehensive regional segregation and gaming acceleration |

---

## Quick Start

Download pre-built sanitized overrides directly from the **[GitHub Releases](https://github.com/liu7say/mihomo-override/releases)** or copy directly from this repository.

### Option A: Flclash / bettbox (Cross-platform Recommended)

1. Navigate to client **Settings** -> **Script / Override** editor;
2. Open the desired sanitized template (e.g., [override/example/customSubBoost.standard.example.js](override/example/customSubBoost.standard.example.js));
3. **Select all and copy** the code into the script editor;
4. *(Optional)* Adjust runtime parameters in the top `CONFIG` block (e.g., multiplier threshold);
5. Save and reload the profile.

### Option B: Clash Party / Sparkle (Desktop)

1. Copy the template script into the client's local override directory:
   - Source: `override/example/customSubBoost.standard.example.js`
   - Destination: `%APPDATA%\mihomo-party\override\customSubBoost.standard.js`
2. Open the **Overrides** management panel and register a new item:
   - **Name**: `SubBoost Standard Override`
   - **Type**: `JavaScript` (ext: `js`)
   - **ID**: `customSubBoost.standard`
   - **Global**: Checked
3. The script handles DNS takeover, node sanitization, and routing in a unified pass.

### Option C: YAML-only Clients (Dual-track Fallback)

If your client environment does not support JavaScript execution, mount the corresponding pure YAML override directly:
- Minimal: `override/yaml/customSubBoost.minimal.yaml`
- Standard: `override/yaml/customSubBoost.standard.yaml`
- Full: `override/yaml/customSubBoost.full.yaml`

---

## Runtime Configuration (CONFIG)

Every All-in-One JS override exposes a declarative configuration object at the top. Modify parameters directly inside the client without recompiling:

```javascript
const CONFIG = {
  // ── 1. Core Feature Toggles ──
  enableDnsOverride: true,          // Override upstream DNS with Fake-IP + domestic DoH
  enableLanDirect: true,            // Direct routing for LAN CIDRs (10/8, 172.16/12, 192.168/16)
  enableFakeIpFilterSteam: true,    // Resolve Steam download domains to domestic IPs for full speed

  // ── 2. Rule Provider Fetching Strategy ──
  ruleProviderProxy: "DIRECT",       // Provider fetch channel: "DIRECT" (recommended) or "节点选择"
  ruleProviderCdn: "fastly",         // CDN source: "fastly" | "gcore" | "cdn" | "testingcf"

  // ── 3. Node Sanitization Engine ──
  cleanTrashNodes: true,            // Filter out notice, traffic expiration, and promotional nodes
  cleanHighMultiplier: true,        // Filter out exorbitant node multipliers
  maxMultiplier: 1.0,               // Maximum node multiplier threshold allowed (e.g., <= 1.0)

  // ── 4. Private Intranet Whitelist (Direct Routing) ──
  enableWorkRules: true,            // Enable dedicated intranet direct bypass
  workDomains: [                    // Private domain wildcard whitelist
    // "+.corp.example.com"
  ],
  workIpCidrs: [                    // Private IP subnet whitelist
    // "10.0.0.0/8"
  ],
  workNameserverPolicy: {           // Dedicated DNS resolution for internal domains
    // "+.corp.example.com": "10.0.0.1"
  }
};
```

---

## Repository Layout

```
├── .github/workflows/                 GitHub Actions CI/CD and release automation
├── pyproject.toml                     Modern Python project metadata
├── requirements.txt                   Lightweight runtime dependencies (PyYAML only)
├── config/
│   ├── rules_profile.json             SubBoost 36-module profile catalogue and test settings
│   ├── private_work.example.json      [Public Template] Sanitized intranet sample configuration
│   └── private_work.json              [Local Private] Real intranet config (ignored by git)
├── docs/
│   ├── PROJECT.md                     Technical architecture, merge semantics, and compatibility
│   └── PERFORMANCE.md                 In-depth benchmark analysis on cold start and DNS latency
├── override/
│   ├── js/                            [Local Private] Injected with personal intranet config
│   │   ├── customSubBoost.minimal.js
│   │   ├── customSubBoost.standard.js
│   │   └── customSubBoost.full.js
│   ├── example/                       [Public Templates] Sanitized overrides for open-source sharing
│   │   ├── customSubBoost.minimal.example.js
│   │   ├── customSubBoost.standard.example.js
│   │   └── customSubBoost.full.example.js
│   └── yaml/                          [Dual-track YAML] Pure YAML rule overrides for legacy clients
│       ├── customSubBoost.minimal.yaml
│       ├── customSubBoost.standard.yaml
│       └── customSubBoost.full.yaml
└── scripts/
    ├── gen_override.py                Core generator: compiles 3-tier JS and YAML outputs
    ├── test_js_override.py            Automated test suite: 10 Node.js runtime assertions
    ├── nest_check.py                  Directed acyclic graph (DAG) cycle and depth verification
    ├── verify.py                      Live kernel validation against real subscription profiles
    ├── check_icons.py                 Qure icon set existence and semantic fallback auditing
    └── check_urls.py                  Ruleset CDN connectivity and payload size probing
```

---

## Development & Building

Built with Python 3.9+ with minimal external overhead:

```bash
# 1. Clone repository and install dependencies
git clone https://github.com/liu7say/mihomo-override.git
cd mihomo-override
pip install -r requirements.txt

# 2. Compile all 3 preset tiers (outputs to js/, example/, and yaml/)
python scripts/gen_override.py

# 3. Run automated quality gate test suites
python scripts/test_js_override.py    # 10 runtime assertions in Node.js
python scripts/nest_check.py          # DAG cycle check (0 cycles, max depth <= 1)
```

---

## Acknowledgments

This project is built upon and inspired by the following outstanding open-source projects. We extend our sincere gratitude to their creators and maintainers:

| Project / Resource | Role & Contribution | Repository | License |
|---|---|---|:---:|
| **SubBoost** | Complete rule architecture, group topology design, and module catalogue | [SubBoost/subboost](https://github.com/SubBoost/subboost) | GPL-3.0 |
| **ACL4SSR** | Long-standing foundation and categorization paradigms for Chinese network routing | [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) | GPL-3.0 |
| **Qure IconSet** | High-definition, standardized, full-color proxy group and regional icons | [Koolson/Qure](https://github.com/Koolson/Qure) | MIT |
| **MetaCubeX (meta-rules-dat)** | High-performance compact binary `.mrs` rulesets and high-availability CDN sources | [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | GPL-3.0 |

Special thanks to all community contributors in the Mihomo (Clash.Meta) routing ecosystem!

---

## License

This project is open-source under the [MIT License](LICENSE).
