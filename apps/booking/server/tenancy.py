"""多場館：一台主機服務多個場館，每個場館一個獨立的 SQLite 資料庫與上傳資料夾。

網址 https://<網域>/<場館代碼>/ → nginx 去掉前綴、帶 X-Tenant: <場館代碼> 轉給這個程式；
程式依 X-Tenant 決定這次請求用哪個場館的資料庫（contextvar，背景排程逐館切換）。

沒有 X-Tenant 的請求：
  /platform/…、/auth/… → 平台（註冊、訂閱、LINE 共用登入）
  其他 → 預設場館（本機開發、測試，以及升級前的單場館安裝）

資料位置：
  <BOOKING_DATA_DIR>/platform.db               平台（場館、場主帳號、訂閱、付款事件、開通申請）
  <BOOKING_DATA_DIR>/booking.db、uploads/       預設場館（升級前就在這裡，原地不動）
  <BOOKING_DATA_DIR>/tenants/<代碼>/booking.db   之後開的場館
"""
import contextvars
import os
import re
import sqlite3
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

DATA_ROOT = Path(os.getenv("BOOKING_DATA_DIR", Path(__file__).parent / "data"))
PLATFORM_DB = DATA_ROOT / "platform.db"
DEFAULT_SLUG = os.getenv("BOOKING_DEFAULT_TENANT", "default")

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$")
# 不能當場館代碼：平台自己的路徑、首頁的檔名、容易誤會的字
RESERVED = {
    "platform", "auth", "api", "assets", "uploads", "static", "admin", "www", "app", "signup", "login", "logout",
    "account", "billing", "pricing", "console", "help", "support", "docs", "blog", "about", "terms", "privacy",
    "legal", "status", "mail", "email", "dc", "digitalcourt", "digital-court", "dc-studio", "test", "demo",
    "robots", "sitemap", "favicon", "llms", "og", "e", "s", "t", "null", "undefined", "root", "system",
    # 品牌站的產品頁（landing/<代碼>.html）與圖片
    "booking", "trainer", "ballwall", "climb", "golf", "mobile", "floor", "sandbox", "draw", "sense", "immersive",
    "img", "products", "solutions", "brand",
}


@dataclass(frozen=True)
class Tenant:
    slug: str
    data_dir: Path
    plan: str = "advanced"
    status: str = "active"
    custom_domain: str = ""

    @property
    def db_path(self) -> Path:
        return self.data_dir / "booking.db"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def public_url(self) -> str:
        """對外網址（結尾不含斜線）；沒設定網域時空字串（本機開發）。"""
        if self.custom_domain:
            return f"https://{self.custom_domain}"
        root = os.getenv("BOOKING_PUBLIC_ROOT", "").rstrip("/")
        if root and self.slug != DEFAULT_SLUG:
            return f"{root}/{self.slug}"
        legacy = os.getenv("BOOKING_PUBLIC_URL") or (f"https://{os.getenv('BOOKING_DOMAIN')}" if os.getenv("BOOKING_DOMAIN") else "")
        if legacy:
            return legacy.rstrip("/")
        return f"{root}/{self.slug}" if root else ""


_current: contextvars.ContextVar[Tenant | None] = contextvars.ContextVar("tenant", default=None)


def current() -> Tenant:
    t = _current.get()
    if t is None:
        raise RuntimeError("這個請求沒有指定場館")
    return t


def current_or_none() -> Tenant | None:
    return _current.get()


@contextmanager
def use(t: Tenant | None):
    token = _current.set(t)
    try:
        yield t
    finally:
        _current.reset(token)


# ---------------------------------------------------------------- 平台資料庫

PLATFORM_SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
  slug TEXT PRIMARY KEY, name TEXT NOT NULL, data_dir TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'lite', billing_cycle TEXT NOT NULL DEFAULT 'month',
  status TEXT NOT NULL DEFAULT 'pending',        -- pending 等付款／trial 免費試用／active／past_due／suspended／cancelled
  account_id INTEGER, custom_domain TEXT NOT NULL DEFAULT '', domain_status TEXT NOT NULL DEFAULT '', comp INTEGER NOT NULL DEFAULT 0,
  polar_customer_id TEXT NOT NULL DEFAULT '', polar_subscription_id TEXT NOT NULL DEFAULT '',
  period_end TEXT NOT NULL DEFAULT '', cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
  past_due_since TEXT NOT NULL DEFAULT '', ended_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, activated_at TEXT NOT NULL DEFAULT '',
  trial_end TEXT NOT NULL DEFAULT '', trial_notice INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_tenants_customer ON tenants(polar_customer_id);
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(custom_domain);
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL, email_verified INTEGER NOT NULL DEFAULT 0, is_admin INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, trial_used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS account_tokens (token TEXT PRIMARY KEY, account_id INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS email_codes (
  email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, tries INTEGER NOT NULL DEFAULT 0, sent_at TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payment_events (
  event_id TEXT PRIMARY KEY, type TEXT NOT NULL, tenant_slug TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_links (
  token TEXT PRIMARY KEY, tenant_slug TEXT NOT NULL, owner_user_id INTEGER NOT NULL, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, contact TEXT NOT NULL, org TEXT NOT NULL DEFAULT '', size TEXT NOT NULL DEFAULT '',
  needs TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '', ip TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL);
-- 場主改過的舊網址代碼：舊連結轉到新網址，而且永遠不能再被別的場館拿去用
CREATE TABLE IF NOT EXISTS slug_aliases (old_slug TEXT PRIMARY KEY, slug TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY, tenant_slug TEXT NOT NULL, url TEXT NOT NULL, reason TEXT NOT NULL, contact TEXT NOT NULL DEFAULT '',
  ip TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL);
"""

# 2026-09-29 七天免費試用
PLATFORM_MIGRATIONS = {
    "tenants": {"trial_end": "TEXT NOT NULL DEFAULT ''", "trial_notice": "INTEGER NOT NULL DEFAULT 0"},
    "accounts": {"trial_used": "INTEGER NOT NULL DEFAULT 0"},
}


@contextmanager
def platform_db():
    conn = sqlite3.connect(PLATFORM_DB, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_platform(stamp: str):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    wal = sqlite3.connect(PLATFORM_DB)
    wal.execute("PRAGMA journal_mode = WAL")
    wal.close()
    with platform_db() as conn:
        conn.executescript(PLATFORM_SCHEMA)
        # 已經建好的資料庫補上後來新增的欄位（附加式，可重複執行）
        for table, cols in PLATFORM_MIGRATIONS.items():
            have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        conn.execute("UPDATE tenants SET plan='lite' WHERE plan='basic'")  # 2026-09-28 方案改名
        # 升級前的單場館安裝：把原本的資料夾登記成預設場館（資料原地不動、免費進階方案）
        if not conn.execute("SELECT slug FROM tenants WHERE slug=?", (DEFAULT_SLUG,)).fetchone():
            conn.execute("INSERT INTO tenants (slug, name, data_dir, plan, status, comp, created_at, activated_at)"
                         " VALUES (?,?,?,?,?,?,?,?)", (DEFAULT_SLUG, DEFAULT_SLUG, str(DATA_ROOT), "advanced", "active", 1, stamp, stamp))


def _row_to_tenant(r) -> Tenant:
    return Tenant(slug=r["slug"], data_dir=Path(r["data_dir"]), plan=r["plan"], status=r["status"],
                  custom_domain=(r["custom_domain"] or "") if r["domain_status"] == "active" else "")


def get(slug: str) -> Tenant | None:
    conn = sqlite3.connect(PLATFORM_DB, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
    finally:
        conn.close()
    return _row_to_tenant(r) if r else None


def alias_target(old_slug: str) -> str | None:
    """舊網址代碼現在指向哪個場館（沒改過名回 None）。"""
    conn = sqlite3.connect(PLATFORM_DB, timeout=15)
    try:
        r = conn.execute("SELECT slug FROM slug_aliases WHERE old_slug=?", (old_slug,)).fetchone()
    finally:
        conn.close()
    return r[0] if r else None


def by_domain(host: str) -> Tenant | None:
    conn = sqlite3.connect(PLATFORM_DB, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute("SELECT * FROM tenants WHERE custom_domain=? AND custom_domain!=''", (host.lower(),)).fetchone()
    finally:
        conn.close()
    return _row_to_tenant(r) if r else None


def all_with_data() -> list[Tenant]:
    """資料庫已建立的場館（排程、啟動時升級用）。"""
    conn = sqlite3.connect(PLATFORM_DB, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        rs = conn.execute("SELECT * FROM tenants WHERE status IN ('trial','active','past_due','suspended','cancelled') ORDER BY slug").fetchall()
    finally:
        conn.close()
    return [_row_to_tenant(r) for r in rs if (Path(r["data_dir"]) / "booking.db").exists()]


def slug_problem(slug: str) -> str | None:
    if not SLUG_RE.match(slug or ""):
        return "網址代碼要 3～30 碼，只能用小寫英文、數字與連字號（-），開頭結尾不能是連字號"
    if slug in RESERVED or "--" in slug:
        return "這個網址代碼是系統保留字，換一個試試"
    return None


def new_data_dir(slug: str) -> Path:
    return DATA_ROOT / "tenants" / slug


# ---------------------------------------------------------------- ASGI：依 X-Tenant 決定場館

def _html(status: int, title: str, text: str) -> tuple[int, bytes]:
    page = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{title}｜Digital Court</title>'
            f'<style>body{{font:16px/1.7 -apple-system,"PingFang TC","Noto Sans TC",sans-serif;color:#111;background:#f6f6f7;margin:0;display:grid;place-items:center;min-height:100vh;padding:16px}}'
            f'main{{background:#fff;border-radius:14px;padding:28px;max-width:420px;text-align:center}}a{{color:#0b6b4b;font-weight:700}}</style></head>'
            f'<body><main><h1 style="font-size:20px">{title}</h1><p>{text}</p><p><a href="/">回 Digital Court 首頁</a></p></main></body></html>')
    return status, page.encode()


class TenantMiddleware:
    """每個請求進來先決定場館；找不到或已停用的場館直接回說明頁。"""

    PLATFORM_PREFIXES = ("/platform", "/auth/")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        slug = headers.get("x-tenant", "").strip().lower()
        path = scope.get("path", "")
        tenant = None
        if slug:
            tenant = get(slug)
            if tenant is None and (new := alias_target(slug)):
                # 場主改過網址：平台網址上的舊連結永久轉到新網址；
                # 自訂網域（nginx 設定每分鐘才更新）直接用新場館回應，不轉址
                root = os.getenv("BOOKING_PUBLIC_ROOT", "").rstrip("/")
                host = headers.get("host", "").split(":")[0].lower()
                if root and host == urllib.parse.urlparse(root).hostname:
                    qs = scope.get("query_string", b"").decode()
                    loc = f"{root}/{new}{path}" + (f"?{qs}" if qs else "")
                    code = 301 if scope.get("method", "GET") in ("GET", "HEAD") else 308
                    return await self._redirect(send, code, loc)
                tenant = get(new)
            if tenant is None or tenant.status == "pending":
                return await self._reply(send, *_html(404, "找不到這個場館", "網址可能打錯了，或這個場館還沒開通。"))
        elif not path.startswith(self.PLATFORM_PREFIXES):
            tenant = get(DEFAULT_SLUG)
        token = _current.set(tenant)
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(token)

    @staticmethod
    async def _redirect(send, status: int, location: str):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"location", location.encode()), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": b""})

    @staticmethod
    async def _reply(send, status: int, body: bytes):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"text/html; charset=utf-8"), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": body})
