#!/usr/bin/env python3
"""自訂網域自動開通（root 每分鐘跑一次：booking-domains.timer）。

場主在「我的帳號」儲存網域（或平台管理按「重新開通」）後 domain_status 會變成 approved，這支程式接手：
  1. 確認網域的 DNS 已指向這台主機（還沒指過來就下次再試，超過 3 天標成 failed）
  2. 先用 http 讓網域連得上，再用 certbot（webroot）申請 HTTPS 憑證
  3. 成功就寫進 /etc/nginx/sites-available/booking-domains、reload，狀態改成 active
nginx 設定檢查失敗會還原成上一版，不影響主站。
資料庫一律用 booking 使用者寫入，避免 root 產生的檔案讓程式讀不到。
"""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time

DATA = os.environ.get("BOOKING_DATA_DIR", "/opt/booking/data")
PLATFORM_DB = os.path.join(DATA, "platform.db")
SITE = "/etc/nginx/sites-available/booking-domains"
ENABLED = "/etc/nginx/sites-enabled/booking-domains"
WEBROOT = "/var/www/html"
LIVE = "/etc/letsencrypt/live"
STATE = "/var/lib/booking-domains.json"   # 每個網域第一次排入開通的時間與上次申請憑證的時間
GIVE_UP = 3 * 86400
RETRY = 15 * 60                            # 憑證申請失敗後隔 15 分鐘再試，避免撞到 Let's Encrypt 的失敗次數限制

PROXY = """        proxy_pass http://127.0.0.1:8100;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant {slug};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;"""


def log(*a):
    print(*a, flush=True)


def rows():
    conn = sqlite3.connect(f"file:{PLATFORM_DB}?mode=ro", uri=True, timeout=15)
    try:
        return conn.execute("SELECT slug, custom_domain, domain_status FROM tenants "
                            "WHERE custom_domain!='' AND domain_status IN ('approved','active')").fetchall()
    finally:
        conn.close()


def set_status(slug, domain, status):
    code = ("import sqlite3,sys;c=sqlite3.connect(sys.argv[1],timeout=15);"
            "c.execute(\"UPDATE tenants SET domain_status=? WHERE slug=? AND custom_domain=?\",(sys.argv[2],sys.argv[3],sys.argv[4]));c.commit()")
    subprocess.run(["runuser", "-u", "booking", "--", "python3", "-c", code, PLATFORM_DB, status, slug, domain], check=True)


def notify(slug, domain, ok):
    """請程式寄信通知場主與平台管理者（程式有 RESEND 設定）。"""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8100/platform/api/internal/domain-result",
                                     data=json.dumps({"slug": slug, "domain": domain, "ok": ok}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:  # noqa: BLE001 通知失敗不影響開通
        log("通知失敗", e)


def my_ips():
    ips = set()
    try:
        out = subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split()
        ips.update(out)
    except OSError:
        pass
    return ips


def points_here(domain):
    try:
        got = {a[4][0] for a in socket.getaddrinfo(domain, 80, socket.AF_INET)}
    except socket.gaierror:
        return False
    return bool(got) and got <= my_ips()


def taken_names():
    """主機上其他網站（不含自己產生的檔案）已經用掉的網域，不能被場館搶走。"""
    import glob
    import re
    names = set()
    for f in glob.glob("/etc/nginx/sites-enabled/*"):
        if os.path.realpath(f) == os.path.realpath(SITE):
            continue
        try:
            for m in re.finditer(r"server_name\s+([^;]+);", open(f).read()):
                names.update(m.group(1).split())
        except OSError:
            pass
    return names


def has_cert(domain):
    return os.path.exists(f"{LIVE}/{domain}/fullchain.pem")


def render(active, warming):
    out = ["# 由 booking-domains 自動產生，請不要手動修改（每分鐘會覆寫）\n"]
    for slug, domain in sorted(active, key=lambda x: x[1]):
        out.append(f"""server {{
    listen 443 ssl;
    server_name {domain};
    ssl_certificate {LIVE}/{domain}/fullchain.pem;
    ssl_certificate_key {LIVE}/{domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    client_max_body_size 10M;
    charset utf-8;
    location / {{
{PROXY.format(slug=slug)}
    }}
}}
server {{
    listen 80;
    server_name {domain};
    location /.well-known/acme-challenge/ {{ root {WEBROOT}; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
""")
    for slug, domain in sorted(warming, key=lambda x: x[1]):
        # 還沒有憑證：先開 http，讓 certbot 能驗證
        out.append(f"""server {{
    listen 80;
    server_name {domain};
    location /.well-known/acme-challenge/ {{ root {WEBROOT}; }}
    location / {{
{PROXY.format(slug=slug)}
    }}
}}
""")
    return "\n".join(out)


def apply(conf):
    """寫入並 reload；檢查失敗就還原。回傳是否成功。"""
    old = open(SITE).read() if os.path.exists(SITE) else None
    if conf == old and os.path.islink(ENABLED):
        return True
    with open(SITE, "w") as f:
        f.write(conf)
    if not os.path.islink(ENABLED):
        os.symlink(SITE, ENABLED)
    t = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if t.returncode != 0:
        log("nginx 設定檢查失敗，還原：", t.stderr.strip())
        if old is None:
            os.remove(ENABLED)
            os.remove(SITE)
        else:
            with open(SITE, "w") as f:
                f.write(old)
        return False
    subprocess.run(["systemctl", "reload", "nginx"], check=True)
    return True


def main():
    if not os.path.exists(PLATFORM_DB):
        return 0
    try:
        state = {d: v for d, v in json.load(open(STATE)).items() if isinstance(v, dict)}
    except (OSError, ValueError, AttributeError):
        state = {}
    active, warming, newly = [], [], []
    taken = taken_names()
    for slug, domain, status in rows():
        if domain in taken:
            log(f"{domain}：主機上其他網站已經在用，不開通")
            set_status(slug, domain, "failed")
            notify(slug, domain, False)
            continue
        if status == "active" and has_cert(domain):
            active.append((slug, domain))
            continue
        st = state.setdefault(domain, {"first": time.time(), "tried": 0})
        if not points_here(domain):
            if time.time() - st["first"] > GIVE_UP:
                log(f"{domain}：DNS 三天都沒有指到這台主機，標成失敗")
                set_status(slug, domain, "failed")
                notify(slug, domain, False)
                state.pop(domain, None)
            continue
        if has_cert(domain):
            newly.append((slug, domain))
        else:
            warming.append((slug, domain))
    if warming and apply(render(active, warming)):
        for slug, domain in warming:
            st = state[domain]
            if time.time() - st["tried"] < RETRY:
                continue
            st["tried"] = time.time()
            r = subprocess.run(["certbot", "certonly", "--webroot", "-w", WEBROOT, "-d", domain, "--non-interactive",
                                "--agree-tos", "--register-unsafely-without-email", "--keep-until-expiring",
                                "--deploy-hook", "systemctl reload nginx"],
                               capture_output=True, text=True)
            if r.returncode == 0 and has_cert(domain):
                newly.append((slug, domain))
            else:
                log(f"{domain}：憑證申請失敗", (r.stderr or r.stdout).strip()[-400:])
                if time.time() - st["first"] > GIVE_UP:
                    set_status(slug, domain, "failed")
                    notify(slug, domain, False)
                    state.pop(domain, None)
    still_warming = [w for w in warming if w not in newly]
    if apply(render(active + newly, still_warming)):
        for slug, domain in newly:
            set_status(slug, domain, "active")
            notify(slug, domain, True)
            state.pop(domain, None)
            log(f"{domain} → {slug} 已開通 HTTPS")
    # 已經不在清單的網域不用再記
    keep = {d for _, d, _ in rows()}
    state = {d: v for d, v in state.items() if d in keep}
    with open(STATE, "w") as f:
        json.dump(state, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
