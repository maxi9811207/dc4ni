"""Digital Court 平台：場主自助註冊、Polar 訂閱付款、自動開站、方案功能、平台管理。

網址都在 /platform/…（nginx 不帶 X-Tenant，見 tenancy.py）。
付款流程：註冊 → 建立待付款的場館 → Polar 結帳（metadata.tenant＝場館代碼）→ webhook 訂閱生效 → 建好場館資料庫與場主帳號 → 寄歡迎信。

環境變數：
  POLAR_ACCESS_TOKEN        Polar API 金鑰（建立結帳、顧客入口）
  POLAR_API                 預設 https://api.polar.sh（測試可指向假伺服器）
  POLAR_WEBHOOK_SECRET      平台 webhook 的簽章密鑰
  POLAR_PLATFORM_PRODUCTS   JSON {"<product_id>": "standard:month", ...}，只處理這些商品（同組織其他產品的事件一律略過）
  POLAR_PORTAL_URL          顧客入口（沒有 API 金鑰時用），例如 https://polar.sh/dc-tools/portal
  PLATFORM_ADMIN_EMAILS     平台管理員 Email（逗號分隔）
  LEAD_EMAIL_TO             開通申請、付款異常通知收件人
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import app as core
import mailer
import tenancy

log = logging.getLogger("saas")

# 年繳＝付 11 個月（送一個月）。企業方案專人報價，不在線上販售（平台管理手動設定）
PLANS = {
    "lite": {"name": "輕量", "month": 490, "year": 5390},
    "standard": {"name": "標準", "month": 1490, "year": 16390},
    "pro": {"name": "專業", "month": 4900, "year": 53900},
    "advanced": {"name": "進階", "month": 12900, "year": 141900},
    "enterprise": {"name": "企業", "month": 0, "year": 0, "quote": True},
}
PLAN_ORDER = ["lite", "standard", "pro", "advanced", "enterprise"]
SELLABLE = ["lite", "standard", "pro", "advanced"]
FEATURES = {"lite": set()}
FEATURES["standard"] = FEATURES["lite"] | {"fee", "cards", "reminder", "noshow"}
FEATURES["pro"] = FEATURES["standard"] | {"push", "export", "dupr", "slots", "reports", "staff"}
FEATURES["advanced"] = FEATURES["pro"] | {"domain", "multisite", "support"}
FEATURES["enterprise"] = FEATURES["advanced"] | {"app"}
FEATURE_NAMES = {
    "fee": "收費對帳", "cards": "課卡方案", "reminder": "開課前一天提醒", "noshow": "缺席管理",
    "push": "LINE 推播通知", "export": "名單下載 Excel", "dupr": "DUPR 活動", "slots": "時段預約", "reports": "營收與出席報表",
    "staff": "多位管理員與教練帳號", "domain": "自訂網域", "multisite": "多館管理", "support": "優先客服與協助搬家",
    "app": "場館專屬 App",
}
GRACE_DAYS = 7          # 扣款失敗後的寬限期
RETENTION_DAYS = 90     # 停止後保留資料的天數


def feature_plan(feature: str) -> str:
    return next(p for p in PLAN_ORDER if feature in FEATURES[p])


def has(feature: str) -> bool:
    t = tenancy.current_or_none()
    return bool(t) and feature in FEATURES.get(t.plan, set())


def need(feature: str):
    if not has(feature):
        p = PLANS[feature_plan(feature)]["name"]
        raise HTTPException(402, f"「{FEATURE_NAMES[feature]}」是{p}方案以上的功能，請到「方案與帳單」升級")


# 依網址決定需要的功能（課卡、報表等整組 API）；收費、DUPR 這類依內容決定的在 app.py 檢查
FEATURE_RULES = [
    ("POST", re.compile(r"^/api/admin/plans/?$"), "cards"),
    ("PUT", re.compile(r"^/api/admin/plans/\d+$"), "cards"),
    ("POST", re.compile(r"^/api/admin/members/\d+/cards$"), "cards"),
    ("*", re.compile(r"^/api/admin/reports"), "reports"),
    ("GET", re.compile(r"^/api/admin/courses/\d+/roster/export$"), "export"),
    ("*", re.compile(r"^/api/admin/courses/\d+/event"), "dupr"),
    ("POST", re.compile(r"^/api/admin/slot-sets"), "slots"),
    ("PUT", re.compile(r"^/api/admin/slot-sets"), "slots"),
    ("GET", re.compile(r"^/api/admin/fees$"), "fee"),
    ("POST", re.compile(r"^/api/admin/branches/?$"), "multisite"),
    ("PUT", re.compile(r"^/api/admin/branches/\d+$"), "multisite"),
]
# 暫停或停止的場館，後台只能看、匯出、改帳號，不能新增修改
READONLY_ALLOW = [re.compile(r"^/api/admin/courses/\d+/roster/export$"), re.compile(r"^/api/admin/reports/export")]


def check_owner_request(request: Request):
    t = tenancy.current()
    path, method = request.url.path, request.method
    for m, rx, f in FEATURE_RULES:
        if (m == "*" or m == method) and rx.search(path):
            need(f)
    if t.status in ("suspended", "cancelled") and method not in ("GET", "HEAD") and not any(rx.search(path) for rx in READONLY_ALLOW):
        raise HTTPException(402, "場館已暫停服務，後台目前只能查看；請到「方案與帳單」續訂")


def venue_info() -> dict:
    """給前端：目前方案、可用功能、狀態（橫幅、鎖住的功能）。"""
    t = tenancy.current()
    row = tenant_row(t.slug) or {}
    return {
        "slug": t.slug, "plan": t.plan, "plan_name": PLANS.get(t.plan, {}).get("name", ""), "status": t.status,
        "features": sorted(FEATURES.get(t.plan, set())), "comp": bool(row.get("comp")),
        "period_end": row.get("period_end", ""), "cancel_at_period_end": bool(row.get("cancel_at_period_end")),
        "billing_cycle": row.get("billing_cycle", "month"),
        "grace_until": _grace_until(row), "account_url": _root_url("/account"),
        "feature_plans": {f: feature_plan(f) for f in FEATURE_NAMES},
    }


def _grace_until(row: dict) -> str:
    since = row.get("past_due_since") or ""
    return (datetime.fromisoformat(since) + timedelta(days=GRACE_DAYS)).isoformat(timespec="minutes") if since else ""


def _root_url(path: str) -> str:
    root = os.getenv("BOOKING_PUBLIC_ROOT", "").rstrip("/")
    return f"{root}{path}" if root else path


# ---------------------------------------------------------------- 平台資料

def tenant_row(slug: str) -> dict | None:
    with tenancy.platform_db() as conn:
        r = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None


def _stamp() -> str:
    return core.stamp()


def _alert(subject: str, text: str):
    log.error("%s %s", subject, text)
    to = [x.strip() for x in os.getenv("LEAD_EMAIL_TO", "").split(",") if x.strip()]
    if to:
        mailer.send(to, f"【Digital Court】{subject}", text)


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "")


HITS: dict[str, list[float]] = {}


def _limit(key: str, n: int, seconds: int, message: str = "操作太頻繁，請稍後再試"):
    t = time.time()
    recent = [x for x in HITS.get(key, []) if t - x < seconds]
    if len(recent) >= n:
        raise HTTPException(429, message)
    HITS[key] = recent + [t]
    if len(HITS) > 20000:
        HITS.clear()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


def _email(v) -> str:
    e = str(v or "").strip().lower()
    if not EMAIL_RE.match(e) or len(e) > 120:
        raise HTTPException(400, "請輸入正確的 Email")
    return e


# ---------------------------------------------------------------- 平台帳號

def current_account(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    with tenancy.platform_db() as conn:
        r = conn.execute("SELECT a.* FROM account_tokens t JOIN accounts a ON a.id=t.account_id WHERE t.token=? AND t.created_at>=?",
                         (authorization[7:], (core.now() - timedelta(days=90)).isoformat(timespec="seconds"))).fetchone()
        return dict(r) if r else None


def require_account(a=Depends(current_account)) -> dict:
    if not a:
        raise HTTPException(401, "請先登入")
    return a


def is_admin(a: dict) -> bool:
    admins = {x.strip().lower() for x in os.getenv("PLATFORM_ADMIN_EMAILS", "").split(",") if x.strip()}
    return bool(a.get("is_admin")) or a["email"] in admins


def require_admin(a=Depends(require_account)) -> dict:
    if not is_admin(a):
        raise HTTPException(403, "沒有權限")
    return a


def _issue_account_token(conn, account_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO account_tokens VALUES (?,?,?)", (token, account_id, _stamp()))
    return token


def _code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


def send_code(body: dict, request: Request):
    email = _email(body.get("email"))
    ip = _client_ip(request)
    _limit(f"code-ip:{ip}", 20, 3600)
    _limit(f"code-mail:{email}", 1, 50, "驗證碼剛寄出，請稍等一分鐘再重寄")
    _limit(f"code-mail-hour:{email}", 6, 3600)
    code = f"{secrets.randbelow(1000000):06d}"
    with tenancy.platform_db() as conn:
        conn.execute("INSERT OR REPLACE INTO email_codes VALUES (?,?,?,?,?)",
                     (email, _code_hash(email, code), 0, _stamp(), (core.now() + timedelta(minutes=15)).isoformat(timespec="seconds")))
    mailer.send(email, f"Digital Court 驗證碼：{code}",
                f"你的 Digital Court 驗證碼是：{code}\n\n15 分鐘內有效。如果不是你本人申請，可以忽略這封信。")
    return {"ok": True, "mail": mailer.enabled()}


def _check_code(conn, email: str, code: str):
    r = conn.execute("SELECT * FROM email_codes WHERE email=?", (email,)).fetchone()
    if not r or r["expires_at"] < _stamp():
        raise HTTPException(400, "驗證碼已過期，請重新寄送")
    if r["tries"] >= 5:
        raise HTTPException(400, "驗證碼錯誤太多次，請重新寄送")
    if not hmac.compare_digest(r["code_hash"], _code_hash(email, str(code or "").strip())):
        conn.execute("UPDATE email_codes SET tries=tries+1 WHERE email=?", (email,))
        return False
    conn.execute("DELETE FROM email_codes WHERE email=?", (email,))
    return True


def slug_status(slug: str) -> dict:
    slug = (slug or "").strip().lower()
    p = tenancy.slug_problem(slug)
    if p:
        return {"ok": False, "reason": p}
    r = tenant_row(slug)
    if r and not _stale_pending(r):
        return {"ok": False, "reason": "這個網址已經有人用了，換一個試試"}
    return {"ok": True}


def _stale_pending(r: dict) -> bool:
    """註冊後沒付款超過 24 小時的網址可以讓給別人。"""
    return r["status"] == "pending" and r["created_at"] < (core.now() - timedelta(hours=24)).isoformat(timespec="seconds")


def signup(body: dict, request: Request):
    email = _email(body.get("email"))
    _limit(f"signup-ip:{_client_ip(request)}", 10, 3600)
    password = str(body.get("password") or "")
    name = str(body.get("name") or "").strip()[:40]
    venue_name = str(body.get("venue_name") or "").strip()[:60]
    slug = str(body.get("slug") or "").strip().lower()
    plan, cycle = str(body.get("plan") or ""), str(body.get("cycle") or "month")
    if plan not in SELLABLE or cycle not in ("month", "year"):
        raise HTTPException(400, "請選擇方案")
    if not name or not venue_name:
        raise HTTPException(400, "請填寫你的稱呼與場館名稱")
    if not body.get("agree"):
        raise HTTPException(400, "請先同意服務條款與隱私權政策")
    st = slug_status(slug)
    if not st["ok"]:
        raise HTTPException(400, st["reason"])
    with tenancy.platform_db() as conn:
        a = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
        if a:
            if not core.check_password(password, a["password_hash"]):
                raise HTTPException(400, "這個 Email 已經註冊過，請輸入原本的密碼（或先登入再新增場館）")
            account_id = a["id"]
        else:
            if len(password) < 8:
                raise HTTPException(400, "密碼至少 8 碼")
            if not _check_code(conn, email, body.get("code")):
                raise HTTPException(400, "驗證碼不正確")
            account_id = conn.execute("INSERT INTO accounts (email, name, phone, password_hash, email_verified, created_at) VALUES (?,?,?,?,1,?)",
                                      (email, name, str(body.get("phone") or "")[:20], core.hash_password(password), _stamp())).lastrowid
        old = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
        if old:  # 別人放著沒付款的網址
            conn.execute("DELETE FROM tenants WHERE slug=?", (slug,))
        conn.execute("INSERT INTO tenants (slug, name, data_dir, plan, billing_cycle, status, account_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (slug, venue_name, str(tenancy.new_data_dir(slug)), plan, cycle, "pending", account_id, _stamp()))
        token = _issue_account_token(conn, account_id)
    url = create_checkout(slug, plan, cycle, email)
    return {"token": token, "checkout_url": url, "slug": slug}


def login(body: dict, request: Request):
    email = _email(body.get("email"))
    _limit(f"login:{email}", 8, 600, "登入錯誤太多次，請 10 分鐘後再試")
    with tenancy.platform_db() as conn:
        a = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
        if not a or not core.check_password(str(body.get("password") or ""), a["password_hash"]):
            raise HTTPException(400, "Email 或密碼不正確")
        return {"token": _issue_account_token(conn, a["id"])}


def reset_password(body: dict, request: Request):
    """忘記密碼：用 Email 驗證碼重設。"""
    email = _email(body.get("email"))
    password = str(body.get("password") or "")
    if len(password) < 8:
        raise HTTPException(400, "密碼至少 8 碼")
    with tenancy.platform_db() as conn:
        a = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
        if not a or not _check_code(conn, email, body.get("code")):
            raise HTTPException(400, "驗證碼不正確")
        conn.execute("UPDATE accounts SET password_hash=? WHERE id=?", (core.hash_password(password), a["id"]))
        conn.execute("DELETE FROM account_tokens WHERE account_id=?", (a["id"],))
        return {"token": _issue_account_token(conn, a["id"])}


def tenant_view(r: dict) -> dict:
    t = tenancy.get(r["slug"])
    status = t.status if t else r["status"]
    url = t.public_url if t else ""
    return {k: r[k] for k in ("slug", "name", "plan", "billing_cycle", "period_end", "custom_domain", "domain_status", "created_at")} | {
        "status": status, "comp": bool(r["comp"]), "cancel_at_period_end": bool(r["cancel_at_period_end"]),
        "plan_name": PLANS.get(r["plan"], {}).get("name", r["plan"]), "url": url + "/" if url else "",
        "grace_until": _grace_until(r), "price": PLANS.get(r["plan"], {}).get(r["billing_cycle"], 0),
        "features": sorted(FEATURES.get(r["plan"], set())),
    }


def me(a: dict):
    with tenancy.platform_db() as conn:
        ts = [dict(r) for r in conn.execute("SELECT * FROM tenants WHERE account_id=? ORDER BY created_at", (a["id"],))]
    return {"email": a["email"], "name": a["name"], "is_admin": is_admin(a), "tenants": [tenant_view(r) for r in ts]}


def _own_tenant(a: dict, slug: str) -> dict:
    r = tenant_row(slug)
    if not r or (r["account_id"] != a["id"] and not is_admin(a)):
        raise HTTPException(404, "找不到這個場館")
    return r


def retry_checkout(a: dict, slug: str, body: dict):
    """還沒付款／已停止的場館重新結帳（換方案也可以）。訂閱中的場館改方案請用顧客入口。"""
    r = _own_tenant(a, slug)
    if r["status"] in ("active", "past_due") and not r["cancel_at_period_end"]:
        raise HTTPException(400, "這個場館訂閱中；要換方案或付款方式請按「管理訂閱」")
    plan = body.get("plan") or r["plan"]
    cycle = body.get("cycle") or r["billing_cycle"]
    if plan not in SELLABLE or cycle not in ("month", "year"):
        raise HTTPException(400, "請選擇方案")
    with tenancy.platform_db() as conn:
        conn.execute("UPDATE tenants SET plan=?, billing_cycle=? WHERE slug=? AND status='pending'", (plan, cycle, slug))
    return {"checkout_url": create_checkout(slug, plan, cycle, a["email"])}


def enter_admin(a: dict, slug: str):
    """一鍵進場館後台：在場館資料庫裡找（或補建）這個帳號的場主，發一組登入 token。"""
    r = _own_tenant(a, slug)
    t = tenancy.get(slug)
    if not t or t.status == "pending" or not t.db_path.exists():
        raise HTTPException(400, "場館還沒開通，完成付款後就能進入")
    with tenancy.use(t), core.db() as conn:
        u = core.one(conn.execute("SELECT * FROM users WHERE email=? AND deleted=0", (a["email"],)))
        if u and u["role"] != "owner" and r["account_id"] == a["id"]:
            conn.execute("UPDATE users SET role='owner' WHERE id=?", (u["id"],))
        if not u:
            if r["account_id"] != a["id"]:  # 平台管理員協助：不在場館裡建帳號，改用現有場主
                u = core.one(conn.execute("SELECT * FROM users WHERE role='owner' AND deleted=0 ORDER BY id LIMIT 1"))
                if not u:
                    raise HTTPException(400, "這個場館沒有場主帳號")
            else:
                uid = conn.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                                   (a["name"] or "場主", a["email"], a["password_hash"], "owner", _stamp())).lastrowid
                u = {"id": uid}
        token = core.issue_token(conn, u["id"])
    base = t.public_url or ""
    return {"url": f"{base}/#/auth/line?token={token}&next=%2Fadmin"}


def portal(a: dict, slug: str):
    r = _own_tenant(a, slug)
    if r["polar_customer_id"] and os.getenv("POLAR_ACCESS_TOKEN"):
        try:
            d = _polar("POST", "/v1/customer-sessions/", {"customer_id": r["polar_customer_id"]})
            if d.get("customer_portal_url"):
                return {"url": d["customer_portal_url"]}
        except Exception as e:  # noqa: BLE001
            log.warning("customer session failed: %s", e)
    return {"url": os.getenv("POLAR_PORTAL_URL", "https://polar.sh/dc-tools/portal")}


# ---------------------------------------------------------------- Polar

def _products() -> dict[str, tuple[str, str]]:
    try:
        raw = json.loads(os.getenv("POLAR_PLATFORM_PRODUCTS") or "{}")
    except ValueError:
        log.error("POLAR_PLATFORM_PRODUCTS 格式錯誤")
        return {}
    out = {}
    for pid, v in raw.items():
        plan, _, cycle = str(v).partition(":")
        if plan in SELLABLE and cycle in ("month", "year"):
            out[pid] = (plan, cycle)
    return out


def _product_for(plan: str, cycle: str) -> str | None:
    return next((pid for pid, v in _products().items() if v == (plan, cycle)), None)


def _polar(method: str, path: str, body: dict | None = None) -> dict:
    base = os.getenv("POLAR_API", "https://api.polar.sh").rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": f"Bearer {os.environ['POLAR_ACCESS_TOKEN']}", "Content-Type": "application/json",
                                          "Accept": "application/json", "User-Agent": "DigitalCourt/1.0 (+https://dc-studio.cc)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def create_checkout(slug: str, plan: str, cycle: str, email: str) -> str:
    pid = _product_for(plan, cycle)
    if not pid or not os.getenv("POLAR_ACCESS_TOKEN"):
        _alert("結帳設定不完整", f"場館 {slug} 選了 {plan}/{cycle}，但沒有對應的 Polar 商品或 API 金鑰")
        raise HTTPException(503, "付款系統暫時無法使用，請稍後再試或來信 dc@dc-tools.cc")
    success = _root_url(f"/signup/done?t={slug}&checkout_id={{CHECKOUT_ID}}")
    try:
        d = _polar("POST", "/v1/checkouts/", {"products": [pid], "customer_email": email, "metadata": {"tenant": slug, "source": "digital-court"},
                                               "success_url": success})
    except urllib.error.HTTPError as e:
        _alert("建立結帳失敗", f"{slug} {plan}/{cycle}: HTTP {e.code} {e.read()[:300]!r}")
        raise HTTPException(502, "付款頁面建立失敗，請稍後再試")
    return d["url"]


def _verify(raw: bytes, headers) -> bool:
    """Standard Webhooks 簽章。Polar 的密鑰（whsec_…）整串就是 HMAC 金鑰（見 DC Tools 踩過的坑），也接受去掉前綴後 base64 解碼的做法。"""
    secret = os.getenv("POLAR_WEBHOOK_SECRET", "")
    wid, ts, sigs = headers.get("webhook-id", ""), headers.get("webhook-timestamp", ""), headers.get("webhook-signature", "")
    if not (secret and wid and ts and sigs):
        return False
    try:
        if abs(time.time() - int(ts)) > 600:
            return False
    except ValueError:
        return False
    keys = [secret.encode()]
    try:
        keys.append(base64.b64decode(secret.removeprefix("whsec_")))
    except ValueError:
        pass
    msg = f"{wid}.{ts}.".encode() + raw
    given = [s.split(",", 1)[1] for s in sigs.split() if "," in s]
    for k in keys:
        want = base64.b64encode(hmac.new(k, msg, hashlib.sha256).digest()).decode()
        if any(hmac.compare_digest(want, g) for g in given):
            return True
    return False


async def webhook(request: Request):
    raw = await request.body()
    if not _verify(raw, request.headers):
        return JSONResponse({"error": "bad signature"}, status_code=403)
    try:
        ev = json.loads(raw)
    except ValueError:
        return JSONResponse({"error": "bad json"}, status_code=400)
    try:
        result = await run_in_threadpool(apply_event, request.headers.get("webhook-id", ""), ev.get("type", ""), ev.get("data") or {})
    except Exception as e:  # noqa: BLE001 — 回 500 讓 Polar 重送，並通知
        _alert("付款通知處理失敗", f"{ev.get('type')} {request.headers.get('webhook-id')}: {e!r}")
        return JSONResponse({"error": "failed"}, status_code=500)
    return {"ok": True, **result}


def _pid(data: dict) -> str:
    return data.get("product_id") or (data.get("product") or {}).get("id") or ""


def apply_event(event_id: str, etype: str, data: dict) -> dict:
    """處理一筆 Polar 事件（可重送：同一個 event id 只處理一次）。只認 Digital Court 的商品，其他產品的事件略過。"""
    prod = _products().get(_pid(data))
    if not prod:
        return {"applied": False, "reason": "not_ours"}
    plan, cycle = prod
    meta = data.get("metadata") or {}
    with tenancy.platform_db() as conn:
        if event_id and conn.execute("SELECT 1 FROM payment_events WHERE event_id=?", (event_id,)).fetchone():
            return {"applied": False, "reason": "duplicate"}
        sub_id = data.get("id") if etype.startswith("subscription.") else data.get("subscription_id") or ""
        cust = data.get("customer_id") or (data.get("customer") or {}).get("id") or ""
        slug = str(meta.get("tenant") or "")
        r = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone() if slug else None
        if not r and sub_id:
            r = conn.execute("SELECT * FROM tenants WHERE polar_subscription_id=?", (sub_id,)).fetchone()
        if not r:
            conn.execute("INSERT INTO payment_events VALUES (?,?,?,?,?)", (event_id or secrets.token_hex(8), etype, "", "unmatched", _stamp()))
            _alert("付款對不到場館", f"{etype} 商品 {plan}/{cycle}，訂閱 {sub_id}、顧客 {cust}，metadata={meta}")
            return {"applied": False, "reason": "no_tenant"}
        r = dict(r)
        now = _stamp()
        upd: dict = {"plan": plan, "billing_cycle": cycle}
        if cust:
            upd["polar_customer_id"] = cust
        if sub_id:
            upd["polar_subscription_id"] = sub_id
        if etype.startswith("subscription."):
            st = data.get("status") or ""
            if data.get("current_period_end"):
                upd["period_end"] = str(data["current_period_end"])[:19]
            upd["cancel_at_period_end"] = 1 if data.get("cancel_at_period_end") else 0
            if etype == "subscription.revoked" or st in ("canceled", "cancelled"):
                upd.update(status="cancelled", ended_at=now)
            elif st in ("past_due", "unpaid"):
                upd["status"] = "past_due"
                if not r["past_due_since"]:
                    upd["past_due_since"] = now
            elif st in ("active", "trialing"):
                upd.update(status="active", past_due_since="")
        elif etype == "order.paid":
            upd.update(status="active", past_due_since="")
        elif etype == "order.refunded":
            _alert("有訂單退款", f"場館 {r['slug']}（{r['name']}）的訂單已退款，請確認是否要停用")
        first = r["status"] == "pending" and upd.get("status") == "active"
        if upd.get("status") == "active" and not r["activated_at"]:
            upd["activated_at"] = now
        conn.execute(f"UPDATE tenants SET {','.join(k + '=?' for k in upd)} WHERE slug=?", (*upd.values(), r["slug"]))
        conn.execute("INSERT INTO payment_events VALUES (?,?,?,?,?)", (event_id or secrets.token_hex(8), etype, r["slug"], json.dumps(upd, ensure_ascii=False), now))
        account = dict(conn.execute("SELECT * FROM accounts WHERE id=?", (r["account_id"],)).fetchone() or {}) if r["account_id"] else {}
    if upd.get("status") == "active":
        provision(r["slug"], account)
        if first:
            _welcome(r["slug"], account)
    if upd.get("status") == "past_due" and not r["past_due_since"] and account:
        mailer.send(account["email"], "【Digital Court】訂閱扣款失敗，請更新付款方式",
                    f"你的場館「{r['name']}」這期的訂閱扣款沒有成功。\n\n請在 {GRACE_DAYS} 天內到 {_root_url('/account')} 按「管理訂閱」更新付款方式，"
                    "逾期後場館會暫停服務（資料會保留）。")
    return {"applied": True, "tenant": r["slug"], "status": upd.get("status", r["status"])}


def provision(slug: str, account: dict):
    """建立（或補齊）場館資料庫與場主帳號；可重複執行。"""
    r = tenant_row(slug)
    t = tenancy.get(slug)
    if not r or not t:
        return
    owner = {"name": account.get("name") or "場主", "email": account.get("email"), "phone": account.get("phone"),
             "password_hash": account.get("password_hash") or ""} if account.get("email") else None
    core.init_tenant(t, owner=owner, name=r["name"])


def _welcome(slug: str, account: dict):
    if not account.get("email"):
        return
    t = tenancy.get(slug)
    url = (t.public_url + "/") if t and t.public_url else ""
    mailer.send(account["email"], "【Digital Court】你的場館開好了",
                f"{account.get('name') or ''} 你好：\n\n你的場館已經開通，方案：{PLANS[t.plan]['name']}。\n\n"
                f"・場館網址（分享給球友）：{url}\n・進入後台：{_root_url('/account')} 登入後按「進入後台」\n\n"
                "第一次進後台，照著「開站步驟」設定場館名稱與介紹、建立第一個活動，再把報名連結貼到 LINE 群組就可以開始報名了。\n\n"
                "有任何問題直接回覆這封信。\n\nDigital Court")


def sweep():
    """每天：扣款失敗超過寬限期 → 暫停；停止滿保留期 → 提醒與封存。"""
    now = core.now()
    with tenancy.platform_db() as conn:
        for r in conn.execute("SELECT * FROM tenants WHERE status='past_due' AND past_due_since!='' AND past_due_since<?",
                              ((now - timedelta(days=GRACE_DAYS)).isoformat(timespec="seconds"),)).fetchall():
            conn.execute("UPDATE tenants SET status='suspended' WHERE slug=?", (r["slug"],))
            _alert("場館因扣款失敗暫停", f"{r['slug']}（{r['name']}）")
        for r in conn.execute("SELECT * FROM tenants WHERE status='pending' AND created_at<?",
                              ((now - timedelta(days=7)).isoformat(timespec="seconds"),)).fetchall():
            conn.execute("DELETE FROM tenants WHERE slug=?", (r["slug"],))  # 註冊一週都沒付款：釋出網址（沒有資料）


# ---------------------------------------------------------------- 開通申請、檢舉

def lead(body: dict, request: Request):
    if body.get("website"):
        return {"ok": True}
    ip = _client_ip(request)
    _limit(f"lead:{ip}", 5, 3600, "送出太多次了，請稍後再試，或直接寄信到 dc@dc-tools.cc")
    clean = lambda k, n: str(body.get(k) or "").strip()[:n]  # noqa: E731
    name, contact = clean("name", 40), clean("contact", 100)
    if not name or not contact:
        raise HTTPException(400, "請填寫稱呼與聯絡方式")
    needs = body.get("needs") if isinstance(body.get("needs"), list) else []
    needs = "、".join(str(x)[:20] for x in needs[:8])
    org, size, message = clean("org", 80), clean("size", 30), clean("message", 1000)
    with tenancy.platform_db() as conn:
        lead_id = conn.execute("INSERT INTO leads (name, contact, org, size, needs, message, ip, created_at) VALUES (?,?,?,?,?,?,?,?)",
                               (name, contact, org, size, needs, message, ip, _stamp())).lastrowid
    to = [x.strip() for x in os.getenv("LEAD_EMAIL_TO", "").split(",") if x.strip()]
    if to:
        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", contact)
        text = "\n".join([f"有人在 Digital Court 首頁留言詢問（#{lead_id}，{_stamp().replace('T', ' ')}）", "",
                          f"稱呼：{name}", f"聯絡方式：{contact}", f"場館或球團：{org or '（未填）'}", f"規模：{size or '（未填）'}",
                          f"想用的功能：{needs or '（未填）'}", "", "想說的話：", message or "（未填）", "",
                          "—", "這封信由 dc-studio.cc 自動寄出。" + ("直接回覆就會寄給對方。" if email else "")])
        mailer.send(to, f"【Digital Court】新的詢問：{name}" + (f"（{org}）" if org else ""), text,
                    reply_to=email.group(0) if email else None)
    return {"ok": True}


def report(body: dict, request: Request):
    """檢舉可疑的場館或活動頁（詐騙、不當內容）。"""
    ip = _client_ip(request)
    _limit(f"report:{ip}", 5, 3600)
    url = str(body.get("url") or "").strip()[:300]
    reason = str(body.get("reason") or "").strip()[:1000]
    if not url or not reason:
        raise HTTPException(400, "請填寫網址與原因")
    m = re.search(r"dc-studio\.cc/([a-z0-9-]+)", url)
    with tenancy.platform_db() as conn:
        conn.execute("INSERT INTO reports (tenant_slug, url, reason, contact, ip, created_at) VALUES (?,?,?,?,?,?)",
                     (m.group(1) if m else "", url, reason, str(body.get("contact") or "")[:100], ip, _stamp()))
    _alert("收到檢舉", f"{url}\n\n{reason}\n\n聯絡：{body.get('contact') or '（未留）'}")
    return {"ok": True}


# ---------------------------------------------------------------- 平台管理（你）

def admin_overview():
    with tenancy.platform_db() as conn:
        ts = [dict(r) for r in conn.execute("SELECT t.*, a.email owner_email, a.name owner_name FROM tenants t LEFT JOIN accounts a ON a.id=t.account_id ORDER BY t.created_at DESC")]
        leads = [dict(r) for r in conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 100")]
        reports = [dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 100")]
        events = [dict(r) for r in conn.execute("SELECT * FROM payment_events ORDER BY created_at DESC LIMIT 50")]
    out = []
    mrr = 0
    for r in ts:
        v = tenant_view(r) | {"owner_email": r["owner_email"] or "", "owner_name": r["owner_name"] or ""}
        if v["status"] in ("active", "past_due") and not r["comp"] and r["plan"] in SELLABLE:
            mrr += PLANS[r["plan"]]["month"] if r["billing_cycle"] == "month" else round(PLANS[r["plan"]]["year"] / 12)
        out.append(v)
    return {"tenants": out, "mrr": mrr, "leads": leads, "reports": reports, "events": events}


def admin_create_tenant(body: dict):
    """手動開一個場館（合作、贈送、測試），不經過付款。"""
    slug = str(body.get("slug") or "").strip().lower()
    st = slug_status(slug)
    if not st["ok"]:
        raise HTTPException(400, st["reason"])
    plan = body.get("plan") or "advanced"
    if plan not in PLANS:  # 企業方案也可以手動開
        raise HTTPException(400, "方案錯誤")
    email = _email(body.get("email"))
    name = str(body.get("name") or "").strip()[:60] or slug
    with tenancy.platform_db() as conn:
        a = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
        if not a:
            aid = conn.execute("INSERT INTO accounts (email, name, password_hash, created_at) VALUES (?,?,?,?)",
                               (email, str(body.get("owner_name") or "")[:40], "", _stamp())).lastrowid
        else:
            aid = a["id"]
        conn.execute("DELETE FROM tenants WHERE slug=? AND status='pending'", (slug,))
        conn.execute("INSERT INTO tenants (slug, name, data_dir, plan, status, account_id, comp, created_at, activated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (slug, name, str(tenancy.new_data_dir(slug)), plan, "active", aid, 1, _stamp(), _stamp()))
        account = dict(conn.execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone())
    provision(slug, account)
    return {"ok": True, "slug": slug}


def admin_update_tenant(slug: str, body: dict):
    r = tenant_row(slug)
    if not r:
        raise HTTPException(404, "找不到場館")
    upd = {}
    if body.get("status") in ("active", "suspended", "cancelled"):
        upd["status"] = body["status"]
    if body.get("plan") in PLANS:
        upd["plan"] = body["plan"]
    if "comp" in body:
        upd["comp"] = 1 if body["comp"] else 0
    if "domain_status" in body and body["domain_status"] in ("", "pending", "approved", "active", "failed"):
        upd["domain_status"] = body["domain_status"]
    if upd:
        with tenancy.platform_db() as conn:
            conn.execute(f"UPDATE tenants SET {','.join(k + '=?' for k in upd)} WHERE slug=?", (*upd.values(), slug))
    if upd.get("status") == "active":
        with tenancy.platform_db() as conn:
            a = conn.execute("SELECT * FROM accounts WHERE id=?", (r["account_id"],)).fetchone()
        provision(slug, dict(a) if a else {})
    return {"ok": True}


# ---------------------------------------------------------------- 自訂網域（進階方案）

DOMAIN_RE = re.compile(r"^(?=.{4,100}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def set_domain(a: dict, slug: str, body: dict):
    r = _own_tenant(a, slug)
    if "domain" not in FEATURES.get(r["plan"], set()):
        raise HTTPException(402, "自訂網域是進階方案以上的功能")
    domain = str(body.get("domain") or "").strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
    if domain and (not DOMAIN_RE.match(domain) or domain.endswith(("dc-studio.cc", "sslip.io", "nip.io"))):
        raise HTTPException(400, "網域格式不正確，例如 booking.yourclub.tw")
    with tenancy.platform_db() as conn:
        if domain and conn.execute("SELECT 1 FROM tenants WHERE custom_domain=? AND slug!=?", (domain, slug)).fetchone():
            raise HTTPException(400, "這個網域已經被其他場館使用")
        # 直接排入開通：主機上的 booking-domains 每分鐘檢查 DNS，指過來了就自動申請 HTTPS
        conn.execute("UPDATE tenants SET custom_domain=?, domain_status=? WHERE slug=?", (domain, "approved" if domain else "", slug))
    if domain:
        _alert("有場館設定自訂網域", f"{slug}：{domain}\nDNS 指過來後主機會自動開通 HTTPS，完成或失敗都會再通知")
    return {"ok": True, "ip": SERVER_IP}


SERVER_IP = os.getenv("BOOKING_SERVER_IP", "172.237.11.215")


def domain_result(body: dict, request: Request):
    """主機上的 booking-domains 開通（或放棄）網域後呼叫，寄信通知場主。只接受本機直接呼叫。"""
    if request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for") or not request.client \
            or request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(404)
    slug, domain, ok = str(body.get("slug") or ""), str(body.get("domain") or ""), bool(body.get("ok"))
    r = tenant_row(slug)
    if not r or r["custom_domain"] != domain or r["domain_status"] != ("active" if ok else "failed"):
        raise HTTPException(409, "狀態不符")
    with tenancy.platform_db() as conn:
        acc = conn.execute("SELECT email, name FROM accounts WHERE id=?", (r["account_id"],)).fetchone() if r["account_id"] else None
    if ok:
        text = (f"你的自訂網域已經開通：https://{domain}/\n\n之後分享給球友的活動連結都會用這個網址，舊的 dc-studio.cc 網址也還能用。\n"
                "如果有用 LINE 登入，請到 LINE Developers 把 Callback URL 加上 "
                f"https://{domain}/api/auth/line/callback（不會設定的話直接回信，我們幫你處理）。\n\nDigital Court")
    else:
        text = (f"你的自訂網域 {domain} 還沒辦法開通：我們檢查不到它的 DNS 指向 {SERVER_IP}，或 HTTPS 憑證申請沒有成功。\n\n"
                "請確認網域 DNS 有一筆 A 記錄指向上面的 IP，改好後到「我的帳號」重新按一次儲存即可；需要協助請直接回信。\n\nDigital Court")
    if acc and acc["email"]:
        mailer.send(acc["email"], "【Digital Court】自訂網域" + ("已開通" if ok else "開通失敗"), text)
    _alert("自訂網域" + ("已開通" if ok else "開通失敗"), f"{slug}：{domain}")
    return {"ok": True}


# ---------------------------------------------------------------- 路由

def register(app):
    @app.get("/platform/api/plans", include_in_schema=False)
    def _plans():
        return {"plans": [{"key": k, **PLANS[k], "features": sorted(FEATURES[k])} for k in PLAN_ORDER], "feature_names": FEATURE_NAMES,
                "sellable": SELLABLE}

    @app.get("/platform/api/slug/{slug}", include_in_schema=False)
    def _slug(slug: str):
        return slug_status(slug)

    @app.post("/platform/api/code", include_in_schema=False)
    def _code(request: Request, body: dict = Depends(core.json_body)):
        return send_code(body, request)

    @app.post("/platform/api/signup", include_in_schema=False)
    def _signup(request: Request, body: dict = Depends(core.json_body)):
        return signup(body, request)

    @app.post("/platform/api/login", include_in_schema=False)
    def _login(request: Request, body: dict = Depends(core.json_body)):
        return login(body, request)

    @app.post("/platform/api/reset", include_in_schema=False)
    def _reset(request: Request, body: dict = Depends(core.json_body)):
        return reset_password(body, request)

    @app.get("/platform/api/me", include_in_schema=False)
    def _me(a=Depends(require_account)):
        return me(a)

    @app.post("/platform/api/tenants/{slug}/checkout", include_in_schema=False)
    def _checkout(slug: str, a=Depends(require_account), body: dict = Depends(core.json_body)):
        return retry_checkout(a, slug, body)

    @app.post("/platform/api/tenants/{slug}/enter", include_in_schema=False)
    def _enter(slug: str, a=Depends(require_account)):
        return enter_admin(a, slug)

    @app.post("/platform/api/tenants/{slug}/portal", include_in_schema=False)
    def _portal(slug: str, a=Depends(require_account)):
        return portal(a, slug)

    @app.put("/platform/api/tenants/{slug}/domain", include_in_schema=False)
    def _domain(slug: str, a=Depends(require_account), body: dict = Depends(core.json_body)):
        return set_domain(a, slug, body)

    @app.post("/platform/api/internal/domain-result", include_in_schema=False)
    def _domain_result(request: Request, body: dict = Depends(core.json_body)):
        return domain_result(body, request)

    @app.get("/platform/api/tenants/{slug}/status", include_in_schema=False)
    def _status(slug: str, a=Depends(require_account)):
        return tenant_view(_own_tenant(a, slug))

    @app.post("/platform/api/webhooks/polar", include_in_schema=False)
    async def _webhook(request: Request):
        return await webhook(request)

    @app.post("/platform/api/leads", include_in_schema=False)
    def _lead(request: Request, body: dict = Depends(core.json_body)):
        return lead(body, request)

    @app.post("/platform/api/reports", include_in_schema=False)
    def _report(request: Request, body: dict = Depends(core.json_body)):
        return report(body, request)

    @app.get("/platform/api/admin/overview", include_in_schema=False)
    def _overview(a=Depends(require_admin)):
        return admin_overview()

    @app.post("/platform/api/admin/tenants", include_in_schema=False)
    def _create(a=Depends(require_admin), body: dict = Depends(core.json_body)):
        return admin_create_tenant(body)

    @app.put("/platform/api/admin/tenants/{slug}", include_in_schema=False)
    def _update(slug: str, a=Depends(require_admin), body: dict = Depends(core.json_body)):
        return admin_update_tenant(slug, body)

    @app.post("/platform/api/admin/tenants/{slug}/enter", include_in_schema=False)
    def _admin_enter(slug: str, a=Depends(require_admin)):
        return enter_admin(a, slug)
