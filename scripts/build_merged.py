"""生成一份可供 mihomo -t 校验的完整配置：
取真实订阅的 proxies/sniffer，套用两份 global 覆写（JS + YAML rules+），
再叠加其余 global JS（节点清理），输出到 test/_sb/merged/config.yaml。
"""
import json
import os
import re
import shutil
import subprocess
import sys

# 配置根目录：优先读取环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
BASE = os.environ.get("MIHOMO_PARTY_BASE") or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "mihomo-party"
)
WORK_SRC = os.path.join(BASE, "work", "1a0377776c2", "config.yaml")
OUT_DIR = os.path.join(BASE, "test", "_sb", "merged")


def load_real_base():
    """复用已生成的合并配置作为底稿（含真实 proxies 与内建 dns）；若不存在则回退到基础占位。"""
    if os.path.exists(WORK_SRC):
        return open(WORK_SRC, encoding="utf-8", errors="replace").read()
    return "proxies:\n  - name: DIRECT\n    type: direct\n"


def extract_proxies_block(s):
    """截取 proxies 段（到下一个顶层键为止）。"""
    i = s.find("\nproxies:")
    if i < 0:
        raise SystemExit("底稿里没有 proxies")
    m = re.search(r"\n[a-zA-Z-]+:", s[i + 1:])
    j = i + 1 + m.start() if m else len(s)
    return s[i:j]


def work_rules(js_text):
    wr = re.search(r"const\s+workRules\s*=\s*\[(.*?)\];", js_text, re.S)
    return re.findall(r'"([^"]+)"', wr.group(1))


def yaml_rules(yml):
    m = re.search(r"^rules(\+?):\s*$", yml, re.M)
    body = yml[m.end():]
    out = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif line.startswith("#") or not line:
            continue
        else:
            break
    return out


def q(s):
    """YAML 双引号转义。"""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    # 优先使用配置根下的覆写，若不存在则回退至本仓库产物
    yml_path = os.path.join(BASE, "override", "1b0sb00st01.yaml")
    if not os.path.exists(yml_path):
        yml_path = os.path.join(os.path.dirname(__file__), "..", "override", "1b0sb00st01.yaml")
    yml = open(yml_path, encoding="utf-8").read()

    js_path = os.path.join(BASE, "override", "1a128f773c5.js")
    if os.path.exists(js_path):
        js = open(js_path, encoding="utf-8").read()
        fip_match = re.search(r'"fake-ip-filter":\s*\[(.*?)\]', js, re.S)
        dns_items = [m for m in re.findall(r'"([^"]+)"', fip_match.group(1))] if fip_match else []
        rules = work_rules(js) + yaml_rules(yml)
    else:
        # 外部无私有 JS 覆写时的通用直连规则与 fake-ip 兜底
        dns_items = ["+.lan", "+.local"]
        default_work_rules = [
            "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
            "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
            "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
            "IP-CIDR,127.0.0.1/8,DIRECT,no-resolve",
        ]
        rules = default_work_rules + yaml_rules(yml)

    base = load_real_base()
    proxies_block = extract_proxies_block(base)

    # rule-providers 与 proxy-groups 整段取自覆写
    pg = yml[yml.find("\nproxy-groups:") + 1: yml.find("\nrule-providers:")]
    rp = yml[yml.find("\nrule-providers:") + 1: yml.find("\nrules+:")]

    # dns 段：生成基础 DNS 配置供语法校验

    parts = []
    parts.append("port: 7890")
    parts.append("mixed-port: 7899")
    parts.append("allow-lan: true")
    parts.append("mode: rule")
    parts.append("log-level: warning")
    parts.append("external-controller: 127.0.0.1:19090")
    parts.append('dns:\n  enable: true\n  ipv6: false\n  enhanced-mode: fake-ip\n'
                 '  fake-ip-range: 198.18.0.1/16\n  fake-ip-filter-mode: blacklist\n'
                 '  fake-ip-filter:\n' + "".join(f"    - {i}\n" for i in dns_items) +
                 '  default-nameserver:\n    - 223.5.5.5\n    - 119.29.29.29\n'
                 '  nameserver:\n    - https://223.5.5.5/dns-query\n'
                 '  proxy-server-nameserver:\n    - 119.29.29.29\n'
                 '  direct-nameserver:\n    - system\n')
    parts.append(proxies_block.rstrip())
    parts.append(pg.rstrip())
    parts.append(rp.rstrip())
    parts.append("rules:")
    parts.extend("  - " + r for r in rules)

    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = os.path.join(OUT_DIR, "config.yaml")
    open(cfg, "w", encoding="utf-8").write("\n".join(parts) + "\n")

    # 复制 geo 资源
    for f in ("country.mmdb", "geoip.metadb", "geoip.dat", "geosite.dat", "ASN.mmdb"):
        src = os.path.join(BASE, "work", "1a0377776c2", f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT_DIR, f))
    rs = os.path.join(BASE, "work", "1a0377776c2", "ruleset")
    if os.path.isdir(rs):
        shutil.copytree(rs, os.path.join(OUT_DIR, "ruleset"), dirs_exist_ok=True)

    print("已生成", cfg)
    print("规则数", len(rules), "| 组数", len(re.findall(r'^  - name:', pg, re.M)),
          "| provider", len(re.findall(r"^  \S+:\s*$", rp, re.M)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
