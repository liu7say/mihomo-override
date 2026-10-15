"""最可靠的验证方式：让 mihomo 内核自己告诉我们一个域名命中哪条规则。

手段：启动内核并开启 external-controller，
然后查 /connections 看不到静态匹配；但 /rules 会给出规则表。
真正能确定「某域名走哪个组」的办法：
  1. 起内核，监听 DNS（listen: 127.0.0.1:port）
  2. 发起一个到 chat.deepseek.com:443 的 TCP 连接（经代理端口）
  3. 立刻查 /connections，找到那条连接，看 chains / rule / rulePayload

这等价于真实分流，且能顺带验证规则集是否真的加载。
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

# 配置根目录：优先环境变量 MIHOMO_PARTY_BASE，缺省从用户环境动态推导
BASE = os.environ.get("MIHOMO_PARTY_BASE") or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "mihomo-party"
)
EXE = os.path.join(BASE, "test", "mihomo-test.exe")
WORK = os.path.join(BASE, "test", "_sb", "mrsq")
MIXED = 19200
CTRL_PORT = MIXED + 99          # 19299
CTRL = f"http://127.0.0.1:{CTRL_PORT}"


def api(path):
    try:
        with urllib.request.urlopen(CTRL + path, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def prepare():
    os.makedirs(WORK, exist_ok=True)
    sh = subprocess.run(
        [sys.executable, os.path.join(BASE, "test", "_sb", "build_merged.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    merged = os.path.join(BASE, "test", "_sb", "merged")
    cfg = open(os.path.join(merged, "config.yaml"), encoding="utf-8").read()
    cfg = re.sub(r"^port: .*$", f"port: {MIXED + 1}", cfg, flags=re.M)
    cfg = re.sub(r"^mixed-port: .*$", f"mixed-port: {MIXED}", cfg, flags=re.M)
    cfg = re.sub(r"^external-controller: .*$",
                 f"external-controller: 127.0.0.1:{CTRL_PORT}", cfg, flags=re.M)
    cfg = re.sub(r"^log-level: .*$", "log-level: debug", cfg, flags=re.M)
    cfg = re.sub(r"^(\s*)listen: .*$", rf"\g<1>listen: 127.0.0.1:{MIXED + 2}", cfg,
                 flags=re.M)
    p = os.path.join(WORK, "config.yaml")
    open(p, "w", encoding="utf-8").write(cfg)
    for f in ("country.mmdb", "geoip.metadb", "geoip.dat", "geosite.dat", "ASN.mmdb"):
        s = os.path.join(merged, f)
        if os.path.exists(s):
            shutil.copy2(s, WORK)
    rs = os.path.join(merged, "ruleset")
    if os.path.isdir(rs):
        shutil.copytree(rs, os.path.join(WORK, "ruleset"), dirs_exist_ok=True)
    return p


def probe(host):
    """通过本地代理建立到 host:443 的连接，触发规则匹配。"""
    s = socket.create_connection(("127.0.0.1", MIXED), timeout=3)
    s.sendall(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode())
    try:
        s.recv(200)
    except Exception:
        pass
    return s


def main():
    hosts = sys.argv[1:] or ["chat.deepseek.com", "api.deepseek.com", "chat.openai.com"]
    cfg = prepare()
    logf = open(os.path.join(WORK, "core.log"), "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([EXE, "-d", WORK, "-f", cfg],
                            stdout=logf, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    try:
        for _ in range(40):
            time.sleep(1)
            if api("/version"):
                break
        else:
            print("内核未就绪"); return 1
        print("内核已就绪\n")
        keep = []
        for h in hosts:
            try:
                keep.append(probe(h))
            except Exception as e:
                print(f"  探测 {h} 失败: {e}")
        # 轮询抓连接：走代理的域名握手慢、连接存活短，要多次采样
        seen = {}
        for _ in range(20):
            conns = api("/connections")
            for c in (conns or {}).get("connections") or []:
                h = (c.get("metadata") or {}).get("host") or ""
                if h in hosts and h not in seen:
                    seen[h] = c
            if len(seen) == len(hosts):
                break
            time.sleep(0.6)
        for h in hosts:
            c = seen.get(h)
            print(f"=== {h} ===")
            if not c:
                print("   无连接记录（可能已结束或直连未记录）")
            else:
                print("   rule        :", c.get("rule"))
                print("   rulePayload :", c.get("rulePayload"))
                print("   chains      :", c.get("chains"))
            print()
        return 0
    finally:
        for s in keep if "keep" in dir() else []:
            try: s.close()
            except Exception: pass
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
        logf.close()


if __name__ == "__main__":
    sys.exit(main())
