"""約課系統後端：FastAPI + SQLite，單一場館。

學生：瀏覽課程、預約／候補／取消、購買課卡、評價。
場主：排課、名單點名、老師、課卡方案、訂單、會員、場館設定。
"""
import csv
import hashlib
import io
import html
import json
import os
import re
import secrets
import sqlite3
import threading
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import dupr
import line_login
import line_push
import mailer
import matches
import reports
import demo  # noqa: E402
import tenancy

# 每個場館一個資料庫與上傳資料夾（見 tenancy.py）；這裡一律透過 tenancy.current() 取得目前場館
STATIC_DIR = Path(os.getenv("BOOKING_STATIC_DIR", Path(__file__).parent / "static"))
TZ = ZoneInfo(os.getenv("BOOKING_TZ", "Asia/Taipei"))
WEEKDAYS = "一二三四五六日"

DEFAULT_SETTINGS = {
    "name": "我的場館",
    "cover_url": "",
    "address": "",
    "phone": "",
    "line_url": "",
    "about": "",
    "payment_info": "請匯款至：000 銀行 帳號 0000-0000-0000，匯款後請傳訊息告知末五碼。",
    "rules": "課程開始前 2 小時截止預約；課程開始前 12 小時內無法自行取消。",
    "categories": ["教學場次", "球敘場次"],
    "show_reservation_count": True,
    "open_days": 14,
    "waitlist_enabled": True,
    "reminder_enabled": True,  # 開課前一天推播提醒
    "reminder_hour": 20,       # 前一天幾點提醒（0～23）
    "noshow_enabled": True,    # 缺席（no-show）管理
    "noshow_limit": 3,         # 缺席幾次暫停報名
    "noshow_days": 90,         # 只算最近幾天的缺席（0＝不限）
    "noshow_block_days": 14,   # 暫停報名幾天（0＝直到場主解除）
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE, email TEXT UNIQUE, line_user_id TEXT UNIQUE,
  password_hash TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'student',
  suspended INTEGER NOT NULL DEFAULT 0, suspend_reason TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_states (
  state TEXT PRIMARY KEY, nonce TEXT NOT NULL, next TEXT NOT NULL DEFAULT '/', link_user_id INTEGER,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS teachers (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
  bio TEXT NOT NULL DEFAULT '', photo_url TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1, sort INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0, valid_days INTEGER NOT NULL DEFAULT 90,
  price INTEGER NOT NULL DEFAULT 0, description TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1, sort INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, plan_id INTEGER NOT NULL,
  amount INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, plan_id INTEGER,
  name TEXT NOT NULL, type TEXT NOT NULL, total INTEGER NOT NULL DEFAULT 0,
  remaining INTEGER NOT NULL DEFAULT 0, starts_on TEXT NOT NULL, expires_on TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'order', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '',
  teacher_id INTEGER, substitute INTEGER NOT NULL DEFAULT 0,
  date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
  capacity INTEGER NOT NULL DEFAULT 10, cost INTEGER NOT NULL DEFAULT 1,
  beginner INTEGER NOT NULL DEFAULT 0, description TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '', booking_deadline_min INTEGER NOT NULL DEFAULT 120,
  cancel_deadline_min INTEGER NOT NULL DEFAULT 720, plan_ids TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservations (
  id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  status TEXT NOT NULL, card_id INTEGER, charged INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_res_course ON reservations(course_id, status);
CREATE INDEX IF NOT EXISTS idx_res_user ON reservations(user_id, status);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, course_id INTEGER, teacher_id INTEGER,
  rating INTEGER NOT NULL, comment TEXT NOT NULL DEFAULT '', hidden INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS course_templates (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', teacher_id INTEGER,
  substitute INTEGER NOT NULL DEFAULT 0, start_time TEXT NOT NULL DEFAULT '19:00', end_time TEXT NOT NULL DEFAULT '21:00',
  capacity INTEGER NOT NULL DEFAULT 10, cost INTEGER NOT NULL DEFAULT 1, beginner INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
  booking_deadline_min INTEGER NOT NULL DEFAULT 120, cancel_deadline_min INTEGER NOT NULL DEFAULT 720,
  plan_ids TEXT NOT NULL DEFAULT '[]', dupr_required INTEGER NOT NULL DEFAULT 0,
  dupr_format TEXT NOT NULL DEFAULT 'doubles', dupr_min REAL, dupr_max REAL,
  dupr_verified_only INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, sort INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_notifications (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, text TEXT NOT NULL, link TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL UNIQUE, format TEXT NOT NULL, games_to INTEGER NOT NULL DEFAULT 11,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS event_groups (
  id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL, name TEXT NOT NULL, sort INTEGER NOT NULL DEFAULT 0,
  entries TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS event_games (
  id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL, group_id INTEGER NOT NULL, round INTEGER NOT NULL,
  side_a TEXT NOT NULL, side_b TEXT NOT NULL, bye TEXT NOT NULL DEFAULT '[]', score_a INTEGER, score_b INTEGER,
  status TEXT NOT NULL DEFAULT 'pending', reported_by INTEGER, confirmed_by INTEGER, updated_at TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_games_event ON event_games(event_id);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS branches (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
  sort INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, contact TEXT NOT NULL, org TEXT NOT NULL DEFAULT '', size TEXT NOT NULL DEFAULT '',
  needs TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '', ip TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS share_aliases (code TEXT PRIMARY KEY, kind TEXT NOT NULL, target_id INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slot_sets (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', teacher_id INTEGER,
  description TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', cover_url TEXT NOT NULL DEFAULT '',
  capacity INTEGER NOT NULL DEFAULT 1, cost INTEGER NOT NULL DEFAULT 0, fee INTEGER NOT NULL DEFAULT 0,
  pay_hours INTEGER NOT NULL DEFAULT 48, plan_ids TEXT NOT NULL DEFAULT '[]',
  booking_deadline_min INTEGER NOT NULL DEFAULT 60, cancel_deadline_min INTEGER NOT NULL DEFAULT 1440,
  listed INTEGER NOT NULL DEFAULT 1, share_code TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, text TEXT NOT NULL,
  read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
"""

# 既有資料庫升級時補上的欄位
MIGRATIONS = {
    "users": {
        "dupr_id": "TEXT NOT NULL DEFAULT ''",
        "dupr_name": "TEXT NOT NULL DEFAULT ''",
        "dupr_doubles": "REAL",
        "dupr_singles": "REAL",
        "dupr_source": "TEXT NOT NULL DEFAULT ''",
        "dupr_verified": "INTEGER NOT NULL DEFAULT 0",
        "dupr_synced_at": "TEXT NOT NULL DEFAULT ''",
        "admin_seen_id": "INTEGER NOT NULL DEFAULT 0",
        "deleted": "INTEGER NOT NULL DEFAULT 0",
        "avatar_url": "TEXT NOT NULL DEFAULT ''",
        "avatar_source": "TEXT NOT NULL DEFAULT ''",
        "teacher_id": "INTEGER",                        # 教練帳號：綁定的老師（只能看、點這位老師的課）
        "blocked_until": "TEXT NOT NULL DEFAULT ''",   # 缺席太多次，暫停報名到這天（含）；9999-12-31＝直到場主解除
        "block_reason": "TEXT NOT NULL DEFAULT ''",
    },
    "courses": {
        "dupr_required": "INTEGER NOT NULL DEFAULT 0",
        "dupr_format": "TEXT NOT NULL DEFAULT 'doubles'",
        "dupr_min": "REAL",
        "dupr_max": "REAL",
        "dupr_verified_only": "INTEGER NOT NULL DEFAULT 0",
        "template_id": "INTEGER",
        "match_format": "TEXT NOT NULL DEFAULT 'rotating'",
        "games_to": "INTEGER NOT NULL DEFAULT 11",
        "listed": "INTEGER NOT NULL DEFAULT 1",
        "share_code": "TEXT NOT NULL DEFAULT ''",
        "fee": "INTEGER NOT NULL DEFAULT 0",
        "pay_hours": "INTEGER NOT NULL DEFAULT 0",
        "cover_url": "TEXT NOT NULL DEFAULT ''",
        "slot_set_id": "INTEGER",
        "branch_id": "INTEGER",
        "show_attendees": "INTEGER NOT NULL DEFAULT 1",
    },
    "course_templates": {
        "branch_id": "INTEGER",
        "listed": "INTEGER NOT NULL DEFAULT 1",
        "show_attendees": "INTEGER NOT NULL DEFAULT 1",
        "fee": "INTEGER NOT NULL DEFAULT 0",
        "pay_hours": "INTEGER NOT NULL DEFAULT 0",
        "cover_url": "TEXT NOT NULL DEFAULT ''",
        "match_format": "TEXT NOT NULL DEFAULT 'rotating'",
        "games_to": "INTEGER NOT NULL DEFAULT 11",
    },
    "slot_sets": {
        "show_attendees": "INTEGER NOT NULL DEFAULT 0",
        "branch_id": "INTEGER",
    },
    "teachers": {
        "hourly_rate": "INTEGER NOT NULL DEFAULT 0",  # 鐘點費（每小時），給教練時數報表
    },
    "reservations": {
        "partner_id": "INTEGER",
        "fee": "INTEGER NOT NULL DEFAULT 0",
        "paid": "INTEGER NOT NULL DEFAULT 0",
        "pay_note": "TEXT NOT NULL DEFAULT ''",
        "paid_at": "TEXT NOT NULL DEFAULT ''",
        "pay_due": "TEXT NOT NULL DEFAULT ''",
        "reminded": "INTEGER NOT NULL DEFAULT 0",
        "noshow_cleared": "INTEGER NOT NULL DEFAULT 0",  # 缺席不再計入：1＝場主免記，2＝已計入一次暫停報名（歸零重算）
    },
    "oauth_states": {
        "no_email": "INTEGER NOT NULL DEFAULT 0",
    },
}

app = FastAPI(title="約課系統 API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(tenancy.TenantMiddleware)


# ---------------------------------------------------------------- helpers

def now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def stamp() -> str:
    return now().isoformat(timespec="seconds")


@contextmanager
def db():
    conn = sqlite3.connect(tenancy.current().db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        # 端點在 threadpool 同時執行：一開始就取得寫入鎖，所有「先查再寫」（扣卡、遞補、開卡、點名…）都不會交錯
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
        for to, text in PENDING_PUSH.pop(id(conn), []):  # 確定寫入後才推播，失敗回滾的不會送出
            line_push.push(to, text)
    except Exception:
        conn.rollback()
        raise
    finally:
        PENDING_PUSH.pop(id(conn), None)
        conn.close()


PENDING_PUSH: dict[int, list[tuple[str, str]]] = {}


def site_url(path: str = "") -> str:
    """目前場館的對外網址（推播訊息裡的連結用）；沒設定網域時不附連結。"""
    base = tenancy.current().public_url
    return (base + "/" + path.lstrip("/")) if base else ""


def queue_push(conn, line_user_id: str | None, text: str, link: str = "", force: bool = False):
    if line_user_id and line_push.enabled() and (force or saas.has("push")):
        PENDING_PUSH.setdefault(id(conn), []).append((line_user_id, f"{text}\n{link}" if link else text))


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def one(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


def fail(status: int, message: str):
    raise HTTPException(status_code=status, detail=message)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False  # LINE 註冊、尚未設定密碼
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(hash_password(password, salt), stored)


def get_settings(conn) -> dict:
    out = dict(DEFAULT_SETTINGS)
    for r in conn.execute("SELECT key, value FROM settings"):
        out[r["key"]] = json.loads(r["value"])
    return out


OWNER_PUSH_KINDS = {"order", "payment", "refund", "digest", "lead"}  # 需要場主動手的事才推到 LINE，其餘只在後台通知


def admin_notify(conn, kind: str, text: str, link: str = ""):
    """場主後台通知（所有場主共用，各自記錄已讀位置）；待處理的事另外推到場主的 LINE。"""
    conn.execute("INSERT INTO admin_notifications (kind, text, link, created_at) VALUES (?,?,?,?)",
                 (kind, text, link, stamp()))
    if kind in OWNER_PUSH_KINDS:
        for o in conn.execute("SELECT line_user_id FROM users WHERE role='owner' AND deleted=0 AND line_user_id IS NOT NULL"):
            queue_push(conn, o["line_user_id"], f"【後台】{text}", site_url("#/admin" + link.removeprefix("/admin")),
                       force=kind == "digest")  # 明日總覽屬於「開課前一天提醒」


def course_label(c: dict) -> str:
    return f"「{c['name']}」{c['date'][5:].replace('-', '/')} {c['start_time']}"


def notify(conn, user_id: int, text: str, course: dict | None = None, reminder: bool = False):
    """站內通知；有綁 LINE 的會員同時推到 LINE（附活動頁連結）。
    reminder：開課前一天提醒——標準方案沒有「LINE 推播通知」，但提醒本身一定要推到 LINE 才有用。"""
    conn.execute("INSERT INTO notifications (user_id, text, created_at) VALUES (?,?,?)",
                 (user_id, text, stamp()))
    u = conn.execute("SELECT line_user_id FROM users WHERE id=?", (user_id,)).fetchone()
    if u and u["line_user_id"]:
        link = site_url(course["share_code"]) if course and course.get("share_code") else site_url("#/me?tab=notifications")
        queue_push(conn, u["line_user_id"], text, link, force=reminder)


def course_start(c: dict) -> datetime:
    return datetime.fromisoformat(f"{c['date']}T{c['start_time']}")


USER_FIELDS = ("id", "name", "phone", "role", "suspended", "suspend_reason", "created_at", "dupr_id", "dupr_name",
               "dupr_doubles", "dupr_singles", "dupr_source", "dupr_verified", "dupr_synced_at", "avatar_url", "teacher_id")


def public_user(u: dict) -> dict:
    return {**{k: u[k] for k in USER_FIELDS}, "email": u["email"], "avatar_source": u["avatar_source"], "line_linked": bool(u["line_user_id"]),
            "has_password": bool(u["password_hash"])}


def mask_name(name: str) -> str:
    return (name[:1] + "**") if name else "**"


# ---------------------------------------------------------------- auth

async def json_body(request: Request) -> dict:
    """讀 JSON 請求內容（空白視為 {}）。端點本身寫成一般 def，交給 threadpool 執行，避免 pbkdf2、SQLite 鎖、連外阻塞整個伺服器。"""
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        fail(400, "資料格式錯誤")
    if not isinstance(data, dict):
        fail(400, "資料格式錯誤")
    return data


def current_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    with db() as conn:
        return one(conn.execute(
            "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ? AND t.created_at >= ?",
            (authorization[7:], (now() - timedelta(days=TOKEN_DAYS)).isoformat(timespec="seconds"))))


TOKEN_DAYS = 180  # 登入有效期；改密碼、停權、被刪除時會立即登出其他裝置


def revoke_tokens(conn, user_id: int, keep: str | None = None):
    conn.execute("DELETE FROM tokens WHERE user_id=? AND token IS NOT ?", (user_id, keep))


def require_user(user=Depends(current_user)) -> dict:
    if not user:
        fail(401, "請先登入")
    return user


def require_staff(request: Request, user=Depends(require_user)) -> dict:
    """場主或教練（教練只能看、點自己的課，見 coach_course）。"""
    if user["role"] == "owner":
        saas.check_owner_request(request)
        return user
    if user["role"] == "coach" and user.get("teacher_id") and saas.has("staff"):
        if tenancy.current().status in ("suspended", "cancelled") and request.method not in ("GET", "HEAD"):
            fail(402, "場館已暫停服務，後台目前只能查看")
        return user
    fail(403, "僅限場主使用")


def coach_course(user: dict, c: dict):
    if user["role"] == "coach" and c.get("teacher_id") != user.get("teacher_id"):
        fail(403, "這堂不是你的課")


def require_owner(request: Request, user=Depends(require_user)) -> dict:
    if user["role"] != "owner":
        fail(403, "僅限場主使用")
    saas.check_owner_request(request)  # 方案功能、暫停中的場館只能查看
    return user


def issue_token(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO tokens VALUES (?,?,?)", (token, user_id, stamp()))
    return token


# ---------------------------------------------------------------- startup

def rebuild_users(conn):
    """舊版 users 表（手機必填、沒有信箱／LINE 欄位）改成新結構，保留所有資料。"""
    info = {r["name"]: r for r in conn.execute("PRAGMA table_info(users)")}
    if "email" in info and not info["phone"]["notnull"]:
        return
    extra = ",\n".join(f"  {col} {ddl}" for col, ddl in MIGRATIONS["users"].items())
    conn.executescript(f"""
CREATE TABLE users_new (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE, email TEXT UNIQUE, line_user_id TEXT UNIQUE,
  password_hash TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'student',
  suspended INTEGER NOT NULL DEFAULT 0, suspend_reason TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
{extra});""")
    new_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users_new)")}
    cols = ",".join(c for c in info if c in new_cols)
    conn.execute(f"INSERT INTO users_new ({cols}) SELECT {cols} FROM users")
    conn.execute("UPDATE users_new SET phone=NULL WHERE phone=''")
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")


@app.on_event("startup")
def startup():
    tenancy.init_platform(stamp())
    init_tenant(tenancy.get(tenancy.DEFAULT_SLUG))  # 預設場館一定要有資料庫（全新安裝、本機測試）
    for t in tenancy.all_with_data():
        if t.slug != tenancy.DEFAULT_SLUG:
            init_tenant(t)
    threading.Thread(target=sweeper, name="sweeper", daemon=True).start()


def init_tenant(t: "tenancy.Tenant", owner: dict | None = None, name: str = ""):
    """建立或升級一個場館的資料庫（新場館開通、每次啟動都會跑；可重複執行）。
    owner：新場館的第一位場主 {name, email, phone, password_hash}。"""
    t.data_dir.mkdir(parents=True, exist_ok=True)
    t.upload_dir.mkdir(parents=True, exist_ok=True)
    wal = sqlite3.connect(t.db_path)  # journal_mode 不能在交易中切換，另開一條連線設定
    wal.execute("PRAGMA journal_mode = WAL")
    wal.close()
    legacy = t.slug == tenancy.DEFAULT_SLUG
    with tenancy.use(t), db() as conn:
        conn.executescript(SCHEMA)
        rebuild_users(conn)
        for r in rows(conn.execute("SELECT id, phone FROM users WHERE phone IS NOT NULL")):
            fixed = clean_phone(r["phone"])
            if fixed != r["phone"] and not one(conn.execute("SELECT id FROM users WHERE phone=? AND id!=?", (fixed, r["id"]))):
                conn.execute("UPDATE users SET phone=? WHERE id=?", (fixed, r["id"]))
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                    if (table, col) == ("slot_sets", "show_attendees"):  # 既有時段預約：時段跟著活動（預設不公開名單）
                        conn.execute("UPDATE courses SET show_attendees=0 WHERE slot_set_id IS NOT NULL")
        if owner and not one(conn.execute("SELECT id FROM users WHERE role='owner' AND deleted=0")):
            conn.execute("INSERT INTO users (name, phone, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                         (owner["name"] or "場主", clean_phone(owner.get("phone")) or None, owner["email"], owner["password_hash"], "owner", stamp()))
        if name and not one(conn.execute("SELECT key FROM settings WHERE key='name'")):
            conn.execute("INSERT INTO settings VALUES ('name', ?)", (json.dumps(name, ensure_ascii=False),))
        phone = os.getenv("BOOKING_OWNER_PHONE") if legacy else None
        password = os.getenv("BOOKING_OWNER_PASSWORD")
        phone = clean_phone(phone)
        # 只在第一次安裝（還沒有任何場主）時建立；之後改手機、刪除或降級場主都不會被設定檔「長回來」
        if phone and password and not one(conn.execute("SELECT id FROM users WHERE role='owner' AND deleted=0")) \
                and not one(conn.execute("SELECT id FROM users WHERE phone=?", (phone,))):
            conn.execute(
                "INSERT INTO users (name, phone, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                (os.getenv("BOOKING_OWNER_NAME", "場主"), phone, hash_password(password), "owner", stamp()))
        if legacy and os.getenv("BOOKING_SEED_DEMO") == "1" and not one(conn.execute("SELECT id FROM courses LIMIT 1")):
            seed_demo(conn)
        for r in rows(conn.execute("SELECT id FROM courses WHERE share_code=''")):
            conn.execute("UPDATE courses SET share_code=? WHERE id=?", (new_share_code(conn), r["id"]))
        if not one(conn.execute("SELECT key FROM kv WHERE key='share_codes_v2'")):
            # 分享代碼從 8 碼改成 4 碼：舊代碼留作別名，已經分享出去的連結照樣能開
            for table, kind in (("courses", "course"), ("slot_sets", "slots")):
                for r in rows(conn.execute(f"SELECT id, share_code FROM {table} WHERE length(share_code)=8")):
                    conn.execute("INSERT OR IGNORE INTO share_aliases VALUES (?,?,?,?)", (r["share_code"], kind, r["id"], stamp()))
                    conn.execute(f"UPDATE {table} SET share_code=? WHERE id=?", (new_share_code(conn), r["id"]))
            conn.execute("INSERT INTO kv VALUES ('share_codes_v2', ?)", (stamp(),))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_courses_share ON courses(share_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_courses_slot ON courses(slot_set_id, date)")
        if demo.kind_of(t.slug):  # 虛構的示範場館：補齊未來兩週的活動
            demo.top_up(conn)


SHARE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # 去掉容易看錯的 0/o、1/l/i


SHARE_CODE_RE = re.compile(r"^[a-z0-9]{4,18}$")
# 活動網址是 <網站>/<代碼>，不能跟網站本身的路徑撞名
SHARE_RESERVED = {"api", "assets", "uploads", "admin", "index", "static", "login", "slots", "course", "teachers", "plans", "about"}


def code_taken(conn, code: str) -> bool:
    return code in SHARE_RESERVED or bool(one(conn.execute("SELECT id FROM courses WHERE share_code=?", (code,)))
                or one(conn.execute("SELECT id FROM slot_sets WHERE share_code=?", (code,)))
                or one(conn.execute("SELECT code FROM share_aliases WHERE code=?", (code,))))


def new_share_code(conn) -> str:
    """分享代碼（預設 4 碼英文數字，去掉容易看錯的字），網址 /e/<代碼>；場主可自訂 4～18 碼。"""
    for n in range(200):
        code = "".join(secrets.choice(SHARE_ALPHABET) for _ in range(4 if n < 100 else 5))
        if not code_taken(conn, code):
            return code
    fail(500, "產生分享代碼失敗，請再試一次")


def find_by_code(conn, code: str) -> tuple[str, dict] | tuple[None, None]:
    """依分享代碼（含改過之前的舊代碼）找活動：('course', 課程) 或 ('slots', 時段預約)。"""
    code = (code or "").strip().lower()
    if not code:
        return None, None
    c = one(conn.execute("SELECT * FROM courses WHERE share_code=?", (code,)))
    if c:
        return "course", c
    ss = one(conn.execute("SELECT * FROM slot_sets WHERE share_code=?", (code,)))
    if ss:
        return "slots", ss
    a = one(conn.execute("SELECT * FROM share_aliases WHERE code=?", (code,)))
    if a:
        table = "courses" if a["kind"] == "course" else "slot_sets"
        row = one(conn.execute(f"SELECT * FROM {table} WHERE id=?", (a["target_id"],)))
        if row:
            return a["kind"], row
    return None, None


def set_share_code(conn, kind: str, row: dict, value) -> str:
    """場主自訂分享代碼：4～18 碼英文或數字、不分大小寫、不能跟別的活動重複；舊代碼留作別名。"""
    code = str(value or "").strip().lower()
    if code == row["share_code"]:
        return code
    if not SHARE_CODE_RE.match(code):
        fail(400, "自訂網址只能用英文或數字，長度 4～18 碼")
    if code in SHARE_RESERVED:
        fail(400, "這個網址是系統保留字，換一個試試")
    a = one(conn.execute("SELECT * FROM share_aliases WHERE code=?", (code,)))
    if a and (a["kind"], a["target_id"]) == (kind, row["id"]):
        conn.execute("DELETE FROM share_aliases WHERE code=?", (code,))  # 改回自己以前用過的代碼
    elif code_taken(conn, code):
        fail(400, "這個網址已經被其他活動用了，換一個試試")
    conn.execute("INSERT OR REPLACE INTO share_aliases VALUES (?,?,?,?)", (row["share_code"], kind, row["id"], stamp()))
    conn.execute(f"UPDATE {'courses' if kind == 'course' else 'slot_sets'} SET share_code=? WHERE id=?", (code, row["id"]))
    return code


CODE_MISSES: dict[str, list[float]] = {}


def guard_code_guess(request: Request, missed: bool):
    """分享代碼只有 4 碼：同一個來源 10 分鐘內猜錯太多次就先擋下，避免被逐一猜出不公開的活動。"""
    import time
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "")
    t = time.time()
    recent = [x for x in CODE_MISSES.get(ip, []) if t - x < 600]
    if len(recent) >= 30:
        fail(429, "嘗試太多次，請稍後再試")
    if missed:
        CODE_MISSES[ip] = recent + [t]
        if len(CODE_MISSES) > 5000:
            CODE_MISSES.clear()


def seed_demo(conn):
    conn.executemany("INSERT INTO settings VALUES (?,?)", [
        ("name", json.dumps("Active Pickleball Club")),
        ("address", json.dumps("新北市中和區自強國小")),
        ("about", json.dumps("新手友善的匹克球俱樂部，提供教學課程與分級球敘。")),
        ("categories", json.dumps(["教學場次", "球敘（初中階場次）", "球敘（高階場次）", "DUPR 場"])),
    ])
    teachers = [("Mark 教練", "USAPA 認證教練", "專長基礎動作與雙打站位，課程循序漸進。"),
                ("小昱", "球敘團主", "負責分級球敘與配對，讓每個人都打得開心。")]
    for i, t in enumerate(teachers):
        conn.execute("INSERT INTO teachers (name, title, bio, sort) VALUES (?,?,?,?)", (*t, i))
    conn.executemany(
        "INSERT INTO plans (name, type, quantity, valid_days, price, description, sort) VALUES (?,?,?,?,?,?,?)", [
            ("單堂體驗", "sessions", 1, 30, 500, "適合第一次來的朋友", 0),
            ("10 堂課卡", "sessions", 10, 120, 4500, "每堂 450 元", 1),
            ("100 點數卡", "points", 100, 180, 4000, "教學課 10 點、球敘 5 點", 2),
            ("月無限卡", "unlimited", 0, 30, 3200, "30 天內不限堂數", 3),
        ])
    today = now().date()
    for d in range(-2, 12):
        day = (today + timedelta(days=d)).isoformat()
        for name, cat, tid, s, e, cap, cost, beg in [
            ("匹克球初階實戰班 Lv.1", "教學場次", 1, "19:00", "21:00", 6, 10, 1),
            ("匹克球敘", "球敘（初中階場次）", 2, "12:00", "15:00", 20, 5, 0),
        ]:
            conn.execute(
                "INSERT INTO courses (name, category, teacher_id, date, start_time, end_time, capacity, cost,"
                " beginner, location, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (name, cat, tid, day, s, e, cap, cost, beg, "自強國小體育館", stamp()))
    for d in range(0, 12, 2):
        conn.execute(
            "INSERT INTO courses (name, category, teacher_id, date, start_time, end_time, capacity, cost, location,"
            " description, dupr_required, dupr_format, dupr_min, dupr_max, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("DUPR 積分雙打團 3.0–4.0", "DUPR 場", 2, (today + timedelta(days=d)).isoformat(), "20:00", "22:00", 16, 5,
             "自強國小體育館", "上傳 DUPR 計分的雙打團，需綁定 DUPR 帳號，雙打分數 3.000–4.000。",
             1, "doubles", 3.0, 4.0, stamp()))
    past = rows(conn.execute("SELECT * FROM courses WHERE date<? ORDER BY id", (today.isoformat(),)))
    comments = ["教練講解仔細，非常好理解，會對每個學生給與建議，超讚！", "很適合新手來體驗！",
                "十分用心教學的老師，推～喜歡上課的氛圍", "分級很清楚，打得很開心"]
    for i, (name, rating) in enumerate([("陳小明", 5), ("林怡君", 5), ("王大同", 4), ("張雅婷", 5)]):
        uid = conn.execute("INSERT INTO users (name, phone, password_hash, created_at) VALUES (?,?,?,?)",
                           (name, f"09880000{i:02d}", hash_password(secrets.token_hex(8)), stamp())).lastrowid
        c = past[i % len(past)]
        conn.execute("INSERT INTO reservations (course_id, user_id, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                     (c["id"], uid, "attended", stamp(), stamp()))
        conn.execute("INSERT INTO reviews (user_id, course_id, teacher_id, rating, comment, created_at)"
                     " VALUES (?,?,?,?,?,?)", (uid, c["id"], c["teacher_id"], rating, comments[i], stamp()))


# ---------------------------------------------------------------- course view logic

def course_counts(conn, course_id: int) -> tuple[int, int]:
    r = conn.execute(
        "SELECT SUM(status IN ('booked','attended','absent')) AS booked, SUM(status='waitlist') AS wait"
        " FROM reservations WHERE course_id=?", (course_id,)).fetchone()
    return r["booked"] or 0, r["wait"] or 0


FORMAT_NAMES = {"doubles": "雙打", "singles": "單打"}


def dupr_problem(c: dict, u: dict) -> str | None:
    """DUPR 場的報名資格，符合回傳 None，否則回傳原因。"""
    if not c["dupr_required"]:
        return None
    if not u.get("dupr_id"):
        return "這是 DUPR 場，請先到會員中心綁定 DUPR 帳號"
    if c["dupr_verified_only"] and not u.get("dupr_verified"):
        return "這場只收主辦驗證過的 DUPR 帳號，請聯絡主辦核對"
    rating = u.get(f"dupr_{c['dupr_format']}")
    fmt = FORMAT_NAMES.get(c["dupr_format"], "")
    if c["dupr_min"] is not None and (rating is None or rating < c["dupr_min"]):
        return f"這場需要 DUPR {fmt} {c['dupr_min']:.2f} 以上（您目前 {rating if rating is not None else '無分數'}）"
    if c["dupr_max"] is not None and rating is not None and rating > c["dupr_max"]:
        return f"這場限 DUPR {fmt} {c['dupr_max']:.2f} 以下（您目前 {rating}）"
    return None


def course_view(conn, c: dict, user: dict | None, settings: dict) -> dict:
    booked, waiting = course_counts(conn, c["id"])
    teacher = one(conn.execute("SELECT id, name, photo_url, title FROM teachers WHERE id=?", (c["teacher_id"],)))
    mine = None
    if user:
        mine = one(conn.execute(
            "SELECT * FROM reservations WHERE course_id=? AND user_id=? AND status != 'cancelled'"
            " ORDER BY id DESC LIMIT 1", (c["id"], user["id"])))
    start = course_start(c)
    t = now()
    remain = max(c["capacity"] - booked, 0)
    event = bool(c["dupr_required"]) and has_event(conn, c["id"])
    if c["status"] == "cancelled":
        button, state = "停課", "disabled"
    elif mine and mine["status"] in ("booked", "attended", "absent"):
        button, state = "已報名", "booked"
    elif mine and mine["status"] == "waitlist":
        button, state = "已候補", "waiting"
    elif t >= start:
        button, state = "已結束", "disabled"
    elif t >= start - timedelta(minutes=c["booking_deadline_min"]):
        button, state = "截止", "disabled"
    elif remain <= 0:
        button, state = ("候補", "waitlist") if settings["waitlist_enabled"] else ("額滿", "disabled")
    else:
        button, state = "報名", "book"
    position = None
    if mine and mine["status"] == "waitlist":
        position = conn.execute(
            "SELECT COUNT(*) FROM reservations WHERE course_id=? AND status='waitlist' AND id<=?",
            (c["id"], mine["id"])).fetchone()[0]
    d = date.fromisoformat(c["date"])
    return {
        **{k: c[k] for k in ("id", "name", "category", "date", "start_time", "end_time", "capacity", "cost",
                             "description", "location", "booking_deadline_min", "cancel_deadline_min", "status")},
        "beginner": bool(c["beginner"]),
        "substitute": bool(c["substitute"]),
        "plan_ids": json.loads(c["plan_ids"]),
        "teacher": teacher,
        "weekday": WEEKDAYS[d.weekday()],
        "booked_count": booked,
        "waitlist_count": waiting,
        "remain": remain,
        "button": button,
        "state": state,
        "my_reservation": mine,
        # 付費活動：名額已保留，但還沒回填後五碼（不算報名成功）
        "pending_payment": bool(mine and mine["status"] == "booked" and mine["fee"] and not mine["paid"] and not mine["pay_note"]),
        "waitlist_position": position,
        "can_cancel": bool(mine) and (mine["status"] == "waitlist" or
                                      (t < start - timedelta(minutes=c["cancel_deadline_min"]) and not event)),
        "has_event": event,
        "template_id": c["template_id"],
        "dupr_required": bool(c["dupr_required"]),
        "dupr_format": c["dupr_format"],
        "dupr_min": c["dupr_min"],
        "dupr_max": c["dupr_max"],
        "dupr_verified_only": bool(c["dupr_verified_only"]),
        "dupr_problem": dupr_problem(c, user) if user and not mine else None,
        "match_format": event_format(c),
        "games_to": c["games_to"],
        "listed": bool(c["listed"]),
        "show_attendees": bool(c["show_attendees"]),
        "share_code": c["share_code"],
        "fee": c["fee"],
        "pay_hours": c["pay_hours"],
        "cover_url": c["cover_url"],
        "slot_set": slot_ref(conn, c),
        "branch": one(conn.execute("SELECT id, name, address FROM branches WHERE id=?", (c.get("branch_id"),))) if c.get("branch_id") else None,
    }


def slot_ref(conn, c: dict) -> dict | None:
    """時段預約的單一時段：附上所屬活動（回選時段頁用）。"""
    if not c.get("slot_set_id"):
        return None
    return one(conn.execute("SELECT id, name, share_code, listed FROM slot_sets WHERE id=?", (c["slot_set_id"],)))


def eligible_cards(conn, user_id: int, c: dict) -> list[dict]:
    today = now().date().isoformat()
    allowed = json.loads(c["plan_ids"])
    out = []
    for card in rows(conn.execute(
            "SELECT cd.*, p.price plan_price, p.quantity plan_qty FROM cards cd LEFT JOIN plans p ON p.id=cd.plan_id"
            " WHERE cd.user_id=? AND cd.starts_on<=? AND cd.expires_on>=? ORDER BY cd.expires_on",
            (user_id, today, today))):
        if allowed and card["plan_id"] not in allowed:
            continue
        need = c["cost"] if card["type"] == "points" else 1
        if card["type"] != "unlimited" and card["remaining"] < need:
            continue
        if card["type"] == "unlimited" and card["expires_on"] < c["date"]:
            continue
        charge_n = 0 if card["type"] == "unlimited" else need
        # 這堂課用這張卡約折合多少錢（方案售價÷張數×扣除量），預設用最划算的卡
        unit = (card["plan_price"] or 0) / card["plan_qty"] if card["plan_qty"] else 0
        out.append({**card, "charge": charge_n, "value": round(unit * charge_n)})
    out.sort(key=lambda x: (x["value"], x["expires_on"]))
    return out


def charge(conn, user_id: int, c: dict, card_id: int | None) -> tuple[int | None, int]:
    """扣課卡，回傳 (card_id, 扣除量)。課程 cost=0 為免費課程。"""
    if c["cost"] == 0:
        return None, 0
    cards = eligible_cards(conn, user_id, c)
    if card_id:
        cards = [x for x in cards if x["id"] == card_id]
    if not cards:
        fail(400, "沒有可用的課卡，請先購買課卡方案")
    card = cards[0]
    if card["charge"]:
        conn.execute("UPDATE cards SET remaining = remaining - ? WHERE id=?", (card["charge"], card["id"]))
    return card["id"], card["charge"]


def refund(conn, r: dict):
    """退還課卡；退完把 charged 歸零，同一筆預約不會退兩次。"""
    if r["card_id"] and r["charged"]:
        conn.execute("UPDATE cards SET remaining = remaining + ? WHERE id=?", (r["charged"], r["card_id"]))
        conn.execute("UPDATE reservations SET charged=0 WHERE id=?", (r["id"],))


def promote_waitlist(conn, c: dict):
    """名額釋出時，依順序遞補候補名單中有可用課卡的人。"""
    booked, _ = course_counts(conn, c["id"])
    if booked >= c["capacity"] or now() >= course_start(c):
        return
    for w in rows(conn.execute(
            "SELECT * FROM reservations WHERE course_id=? AND status='waitlist' ORDER BY id", (c["id"],))):
        if booked >= c["capacity"]:
            break
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (w["user_id"],)))
        if u["suspended"]:
            continue
        if noshow_status(conn, u)["blocked"]:
            notify(conn, w["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 有名額釋出，但您目前暫停報名中，未能自動遞補。")
            continue
        if dupr_problem(c, u):
            notify(conn, w["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 有名額釋出，"
                                       "但您的 DUPR 分數不符合這場的條件，未能自動遞補。")
            continue
        try:
            card_id, charged = charge(conn, w["user_id"], c, None)
        except HTTPException:
            notify(conn, w["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 有名額釋出，"
                                       "但您沒有可用課卡，未能自動遞補。")
            continue
        conn.execute("UPDATE reservations SET status='booked', card_id=?, charged=?, pay_due=?, updated_at=? WHERE id=?",
                     (card_id, charged, pay_due(c), stamp(), w["id"]))
        notify(conn, w["user_id"], (f"候補成功！「{c['name']}」{c['date']} {c['start_time']} 有名額了，" + fee_notice(conn, c)) if c["fee"]
               else f"候補成功！您已報名「{c['name']}」{c['date']} {c['start_time']}。", course=c)
        admin_notify(conn, "promote", f"{u['name']} 由候補遞補 {course_label(c)}", f"/admin/courses/{c['id']}")
        booked += 1


def get_course(conn, course_id: int) -> dict:
    c = one(conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)))
    if not c:
        fail(404, "找不到課程")
    return c


# ---------------------------------------------------------------- public API

@app.get("/api/venue")
def venue():
    with db() as conn:
        s = get_settings(conn)
        r = conn.execute("SELECT AVG(rating) a, COUNT(*) n FROM reviews WHERE hidden=0").fetchone()
        return {**s, "payment_ready": payment_ready(s), "rating": round(r["a"], 1) if r["a"] else None, "review_count": r["n"],
                "platform": saas.venue_info()}


def attendees(conn, c: dict, limit: int = 200) -> list[dict]:
    """已預約學員（姓名遮罩＋頭像）；DUPR 場附上該場依據的 DUPR 分數。場主可設定不公開（例如場地租借）。"""
    out = []
    if not c.get("show_attendees", 1):
        return out
    for r in conn.execute(
            "SELECT u.name, u.avatar_url, u.dupr_id, u.dupr_doubles, u.dupr_singles, u.dupr_verified"
            " FROM reservations r JOIN users u ON u.id=r.user_id"
            " WHERE r.course_id=? AND r.status IN ('booked','attended','absent')"
            " AND (r.fee=0 OR r.paid=1 OR r.pay_note!='') ORDER BY r.id LIMIT ?",  # 付費活動：回填後五碼才算報名成功
            (c["id"], limit)):
        a = {"name": mask_name(r["name"]), "avatar_url": r["avatar_url"]}
        if c["dupr_required"]:
            a["dupr"] = r[f"dupr_{c['dupr_format']}"]
            a["dupr_verified"] = bool(r["dupr_verified"])
        out.append(a)
    return out


@app.get("/api/courses")
def list_courses(request: Request, user=Depends(current_user)):
    day = request.query_params.get("date") or now().date().isoformat()
    with db() as conn:
        s = get_settings(conn)
        cs = rows(conn.execute("SELECT * FROM courses WHERE date=? AND listed=1 AND slot_set_id IS NULL ORDER BY start_time, id", (day,)))
        d = date.fromisoformat(day)
        sets = rows(conn.execute("SELECT * FROM slot_sets WHERE listed=1 AND id IN (SELECT slot_set_id FROM courses"
                                 " WHERE date=? AND status='open' AND slot_set_id IS NOT NULL) ORDER BY id", (day,)))
        return {"date": day, "weekday": WEEKDAYS[d.weekday()],
                "show_reservation_count": s["show_reservation_count"],
                "courses": [{**course_view(conn, c, user, s), "attendees": attendees(conn, c, 6)} for c in cs],
                "slot_sets": [slot_day_summary(conn, x, day, user, s) for x in sets]}


def can_see(conn, c: dict, user: dict | None, code: str | None = None) -> bool:
    """不公開（只限連結）的課程：拿到分享代碼、場主、已報名／候補過的人才看得到。"""
    if c["listed"] or (code and secrets.compare_digest(code.strip().lower(), c["share_code"])):
        return True
    if code and one(conn.execute("SELECT code FROM share_aliases WHERE code=? AND kind='course' AND target_id=?", (code.strip().lower(), c["id"]))):
        return True
    if user and user["role"] == "owner":
        return True
    return bool(user and one(conn.execute("SELECT id FROM reservations WHERE course_id=? AND user_id=?", (c["id"], user["id"]))))


def detail_view(conn, c: dict, user: dict | None) -> dict:
    v = course_view(conn, c, user, get_settings(conn))
    allowed = v["plan_ids"]
    plans = rows(conn.execute("SELECT id, name, type FROM plans WHERE active=1 ORDER BY sort, id"))
    v["plans"] = [p for p in plans if not allowed or p["id"] in allowed]
    v["cards"] = eligible_cards(conn, user["id"], c) if user else []
    v["attendees"] = attendees(conn, c)
    return v


@app.get("/api/e/{code}")
def share_detail(code: str, request: Request, user=Depends(current_user)):
    """分享網址 /e/<代碼> 的一頁式活動頁資料。"""
    guard_code_guess(request, False)
    with db() as conn:
        kind, row = find_by_code(conn, code)
        if kind == "slots":
            return slot_set_view(conn, row, user)
        if not row:
            guard_code_guess(request, True)
            fail(404, "找不到這個活動，請確認連結是否正確")
        return detail_view(conn, row, user)


@app.get("/api/courses/{course_id}")
def course_detail(course_id: int, user=Depends(current_user)):
    with db() as conn:
        c = get_course(conn, course_id)
        if not can_see(conn, c, user):
            fail(404, "找不到課程")
        return detail_view(conn, c, user)



@app.get("/api/teachers")
def teachers():
    with db() as conn:
        out = []
        for t in rows(conn.execute("SELECT * FROM teachers WHERE active=1 ORDER BY sort, id")):
            r = conn.execute("SELECT AVG(rating) a, COUNT(*) n FROM reviews WHERE teacher_id=? AND hidden=0",
                             (t["id"],)).fetchone()
            out.append({**t, "rating": round(r["a"], 1) if r["a"] else None, "review_count": r["n"]})
        return out


@app.get("/api/teachers/{teacher_id}")
def teacher_detail(teacher_id: int, user=Depends(current_user)):
    with db() as conn:
        t = one(conn.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)))
        if not t:
            fail(404, "找不到老師")
        s = get_settings(conn)
        today = now().date().isoformat()
        cs = rows(conn.execute("SELECT * FROM courses WHERE teacher_id=? AND date>=? AND status='open' AND listed=1"
                               " ORDER BY date, start_time LIMIT 20", (teacher_id, today)))
        return {**t, "courses": [course_view(conn, c, user, s) for c in cs],
                "reviews": review_list(conn, "WHERE r.teacher_id=? AND r.hidden=0", (teacher_id,))}


@app.get("/api/plans")
def plans():
    with db() as conn:
        return rows(conn.execute("SELECT * FROM plans WHERE active=1 ORDER BY sort, id"))


def review_list(conn, where: str, args: tuple) -> list[dict]:
    out = []
    for r in rows(conn.execute(
            "SELECT r.*, u.name user_name, c.name course_name, t.name teacher_name FROM reviews r"
            " JOIN users u ON u.id=r.user_id LEFT JOIN courses c ON c.id=r.course_id"
            f" LEFT JOIN teachers t ON t.id=r.teacher_id {where} ORDER BY r.id DESC LIMIT 200", args)):
        r["user_name"] = mask_name(r["user_name"])
        out.append(r)
    return out


@app.get("/api/reviews")
def reviews():
    with db() as conn:
        return review_list(conn, "WHERE r.hidden=0 AND (c.id IS NULL OR c.listed=1)", ())


# ---------------------------------------------------------------- auth API

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_email(v) -> str | None:
    v = str(v or "").strip().lower()
    if not v:
        return None
    if not EMAIL_RE.match(v) or len(v) > 120:
        fail(400, "信箱格式不正確")
    return v


def clean_phone(v) -> str | None:
    """只保留數字與 +（去掉空白、橫線，以及終端機誤輸入的方向鍵等控制字元）。"""
    v = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", str(v or ""))
    v = re.sub(r"[^\d+]", "", v)
    return v[:20] or None


def create_user(conn, name: str, **fields) -> dict:
    row = {"name": name[:40], "created_at": stamp(), **fields}
    cur = conn.execute(f"INSERT INTO users ({','.join(row)}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
    u = one(conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)))
    admin_notify(conn, "member", f"新會員 {u['name']} 註冊" + ("（LINE）" if u["line_user_id"] else ""), "/admin/members")
    return u


@app.post("/api/auth/register")
def register(body: dict = Depends(json_body)):
    """信箱註冊（手機選填）。舊版只帶手機的請求也接受。"""
    b = body
    name, password = str(b.get("name", "")).strip(), str(b.get("password", ""))
    email, phone = clean_email(b.get("email")), clean_phone(b.get("phone"))
    if not name or not (email or phone) or len(password) < 6:
        fail(400, "請填寫姓名與信箱，密碼至少 6 碼")
    with db() as conn:
        if email and one(conn.execute("SELECT id FROM users WHERE email=?", (email,))):
            fail(400, "此信箱已註冊，請直接登入")
        if phone and one(conn.execute("SELECT id FROM users WHERE phone=?", (phone,))):
            fail(400, "此手機號碼已註冊，請直接登入")
        u = create_user(conn, name, email=email, phone=phone, password_hash=hash_password(password))
        return {"token": issue_token(conn, u["id"]), "user": public_user(u)}


LOGIN_FAILS: dict[str, list[float]] = {}


@app.post("/api/auth/login")
def login(body: dict = Depends(json_body)):
    """用信箱或手機＋密碼登入。同一帳號 10 分鐘內錯 8 次就暫停登入。"""
    b = body
    key = str(b.get("login") or b.get("email") or b.get("phone") or "").strip()
    t = datetime.now().timestamp()
    recent = [x for x in LOGIN_FAILS.get(f"{tenancy.current().slug}:{key.lower()}", []) if t - x < 600]
    if len(recent) >= 8:
        fail(429, "嘗試次數太多，請 10 分鐘後再試")
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE email=? OR phone=?", (key.lower(), clean_phone(key))))
        if u and not u["password_hash"]:
            fail(400, "這個帳號是用 LINE 註冊的，請按「使用 LINE 登入」")
        if not u or not check_password(str(b.get("password", "")), u["password_hash"]):
            LOGIN_FAILS[f"{tenancy.current().slug}:{key.lower()}"] = recent + [t]
            fail(400, "帳號或密碼錯誤")
        LOGIN_FAILS.pop(f"{tenancy.current().slug}:{key.lower()}", None)
        return {"token": issue_token(conn, u["id"]), "user": public_user(u)}


# ---------------------------------------------------------------- LINE 登入

def public_base(request: Request) -> str:
    """目前場館的對外網址（結尾有斜線）。有網域時一律用設定的網址，LINE callback 才會和 LINE 後台設定的一致。"""
    base = tenancy.current().public_url
    if base:
        return base + "/"
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.headers.get('host', request.url.netloc)}/"


def safe_next(v) -> str:
    v = str(v or "/")
    return v if v.startswith("/") and not v.startswith("//") else "/"


def line_user(conn, profile: dict, link_user_id: int | None = None) -> dict:
    """依 LINE 身分找到或建立會員；同步 LINE 頭像（使用者自己上傳過就不覆蓋）。"""
    u = one(conn.execute("SELECT * FROM users WHERE line_user_id=?", (profile["sub"],)))
    if link_user_id:
        if u and u["id"] != link_user_id:
            fail(400, "這個 LINE 帳號已綁定其他會員")
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (link_user_id,)))
    # 不用信箱自動併入既有帳號：本站註冊的信箱沒有驗證，別人可以先用你的信箱註冊來搶帳號。
    # 已有信箱帳號的人請登入後到「會員中心 → 帳號」綁定 LINE。
    if not u:
        email = profile["email"] or None
        if email and one(conn.execute("SELECT id FROM users WHERE email=?", (email,))):
            email = None
        u = create_user(conn, profile["name"], line_user_id=profile["sub"], email=email,
                        avatar_url=profile["picture"], avatar_source="line" if profile["picture"] else "")
    updates = {"line_user_id": profile["sub"]}
    if profile["picture"] and u["avatar_source"] != "upload":
        updates.update(avatar_url=profile["picture"], avatar_source="line")
    if profile["email"] and not u["email"] and not one(conn.execute("SELECT id FROM users WHERE email=?", (profile["email"],))):
        updates["email"] = profile["email"]
    conn.execute(f"UPDATE users SET {','.join(k + '=?' for k in updates)} WHERE id=?", (*updates.values(), u["id"]))
    return one(conn.execute("SELECT * FROM users WHERE id=?", (u["id"],)))


LINE_STATE_COOKIE = "line_state"


def with_state_cookie(response, state: str):
    """把這次授權的 state 綁在發起的瀏覽器上；callback 時比對，別人丟來的授權連結（CSRF）會被擋下。"""
    # 網站可能掛在子路徑（例如 https://digital-court.cc/active/），cookie 路徑要跟著
    prefix = urllib.parse.urlparse(tenancy.current().public_url or "/").path.rstrip("/")
    response.set_cookie(LINE_STATE_COOKIE, state, max_age=1800, httponly=True, samesite="lax",
                        secure=public_base_is_https(), path=f"{prefix}/api/auth/line")
    return response


def public_base_is_https() -> bool:
    return tenancy.current().public_url.startswith("https://")


def line_redirect(conn, request: Request, next_path: str, link_user_id: int | None = None) -> tuple[str, str]:
    if not line_login.enabled():
        fail(400, "場館尚未開通 LINE 登入")
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(16)
    conn.execute("DELETE FROM oauth_states WHERE created_at < ?", ((now() - timedelta(minutes=30)).isoformat(),))
    conn.execute("INSERT INTO oauth_states (state, nonce, next, link_user_id, created_at) VALUES (?,?,?,?,?)",
                 (state, nonce, safe_next(next_path), link_user_id, stamp()))
    return line_login.authorize_url(public_base(request) + "api/auth/line/callback", state, nonce), state


@app.get("/api/auth/config")
def auth_config():
    return {"line_enabled": line_login.enabled(), "liff_id": line_login.liff_id()}


@app.get("/api/auth/line/start")
def line_start(request: Request):
    with db() as conn:
        url, state = line_redirect(conn, request, request.query_params.get("next", "/"))
        return with_state_cookie(RedirectResponse(url, status_code=302), state)


@app.post("/api/auth/line/link")
def line_link(request: Request, user=Depends(require_user)):
    """已登入的會員綁定 LINE：回傳授權網址，前端導過去。"""
    with db() as conn:
        url, state = line_redirect(conn, request, "/me?tab=account", user["id"])
        return with_state_cookie(JSONResponse({"url": url}), state)


@app.get("/api/auth/line/callback")
def line_callback(request: Request):
    base = public_base(request)
    q = request.query_params

    def back(**params):
        return RedirectResponse(base + "#/auth/line?" + urllib.parse.urlencode(params), status_code=302)

    with db() as conn:
        st = one(conn.execute("SELECT * FROM oauth_states WHERE state=?", (q.get("state", ""),)))
        mine = st and secrets.compare_digest(request.cookies.get(LINE_STATE_COOKIE, ""), st["state"])
        fresh = mine and st["created_at"] >= (now() - timedelta(minutes=30)).isoformat()
        if q.get("error") == "invalid_scope" and fresh and not st["no_email"]:
            # channel 尚未取得 email 權限：同一個 state 改成不要求 email 再授權一次（只退一次，不會無限重導）
            conn.execute("UPDATE oauth_states SET no_email=1 WHERE state=?", (st["state"],))
            return RedirectResponse(line_login.authorize_url(base + "api/auth/line/callback", st["state"], st["nonce"],
                                                             email=False), status_code=302)
        if q.get("error"):
            return back(error="已取消 LINE 登入" if q["error"] == "access_denied" else "LINE 登入失敗，請聯絡場館")
        if not fresh:
            return back(error="登入逾時，請再試一次")
        conn.execute("DELETE FROM oauth_states WHERE state=?", (st["state"],))
        try:
            profile = line_login.exchange_code(q.get("code", ""), base + "api/auth/line/callback", st["nonce"])
            u = line_user(conn, profile, st["link_user_id"])
        except line_login.LineError as e:
            return back(error=str(e))
        except HTTPException as e:
            return back(error=str(e.detail))
        return back(token=issue_token(conn, u["id"]), next=st["next"], linked="1" if st["link_user_id"] else "")


@app.post("/api/auth/line/idtoken")
def line_idtoken(body: dict = Depends(json_body)):
    """LIFF（在 LINE 裡開啟）：前端取得 ID token 後換成本站登入。"""
    if not line_login.enabled():
        fail(400, "場館尚未開通 LINE 登入")
    b = body
    try:
        profile = line_login.verify_id_token(str(b.get("id_token", "")))
    except line_login.LineError as e:
        fail(400, str(e))
    with db() as conn:
        u = line_user(conn, profile)
        return {"token": issue_token(conn, u["id"]), "user": public_user(u)}


@app.get("/api/me/line-friend")
def line_friend(user=Depends(require_user)):
    """會員中心用：沒加官方帳號好友的話，提醒加好友，否則收不到報名、候補、開課提醒的 LINE 通知。"""
    url = line_push.add_friend_url()
    friend = line_push.is_friend(user["line_user_id"]) if user["line_user_id"] and url else None
    return {"friend": friend, "add_url": url}


@app.delete("/api/me/line")
def line_unlink(user=Depends(require_user)):
    if not user["password_hash"]:
        fail(400, "請先設定信箱與密碼，才能解除 LINE 綁定（否則會無法登入）")
    with db() as conn:
        conn.execute("UPDATE users SET line_user_id=NULL WHERE id=?", (user["id"],))
        if user["avatar_source"] == "line":
            conn.execute("UPDATE users SET avatar_url='', avatar_source='' WHERE id=?", (user["id"],))
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        with db() as conn:
            conn.execute("DELETE FROM tokens WHERE token=?", (authorization[7:],))
    return {"ok": True}


# ---------------------------------------------------------------- member API

@app.get("/api/me")
def me(user=Depends(require_user)):
    with db() as conn:
        unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0",
                              (user["id"],)).fetchone()[0]
        out = {**public_user(user), "unread": unread, "noshow": noshow_status(conn, user)}
        if user["role"] == "owner":
            out["admin_unread"] = conn.execute("SELECT COUNT(*) FROM admin_notifications WHERE id>?",
                                               (user["admin_seen_id"],)).fetchone()[0]
        return out


@app.put("/api/me")
def update_me(body: dict = Depends(json_body), user=Depends(require_user), authorization: str | None = Header(default=None)):
    b = body
    with db() as conn:
        name = str(b.get("name", user["name"])).strip()[:40] or user["name"]
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, user["id"]))
        if "email" in b:
            email = clean_email(b["email"])
            if not email and not user["line_user_id"]:
                fail(400, "請填寫信箱")
            if email and one(conn.execute("SELECT id FROM users WHERE email=? AND id!=?", (email, user["id"]))):
                fail(400, "此信箱已被其他帳號使用")
            conn.execute("UPDATE users SET email=? WHERE id=?", (email, user["id"]))
        if "phone" in b:
            phone = clean_phone(b["phone"])
            if phone and one(conn.execute("SELECT id FROM users WHERE phone=? AND id!=?", (phone, user["id"]))):
                fail(400, "此手機號碼已被其他帳號使用")
            conn.execute("UPDATE users SET phone=? WHERE id=?", (phone, user["id"]))
        if b.get("new_password"):
            # LINE 註冊的帳號第一次設定密碼不需要原密碼
            if user["password_hash"] and not check_password(str(b.get("password", "")), user["password_hash"]):
                fail(400, "原密碼錯誤")
            if len(b["new_password"]) < 6:
                fail(400, "新密碼至少 6 碼")
            conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (hash_password(b["new_password"]), user["id"]))
            revoke_tokens(conn, user["id"], keep=(authorization or "")[7:])  # 其他裝置需重新登入
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


@app.get("/api/me/reservations")
def my_reservations(user=Depends(require_user)):
    with db() as conn:
        s = get_settings(conn)
        out = []
        for r in rows(conn.execute(
                "SELECT r.*, c.date, c.start_time FROM reservations r JOIN courses c ON c.id=r.course_id"
                " WHERE r.user_id=? AND r.status!='cancelled' ORDER BY c.date DESC, c.start_time DESC LIMIT 200",
                (user["id"],))):
            c = get_course(conn, r["course_id"])
            v = course_view(conn, c, user, s)
            reviewed = one(conn.execute("SELECT id FROM reviews WHERE user_id=? AND course_id=?",
                                        (user["id"], c["id"])))
            out.append({"reservation": r, "course": v, "ended": now() >= course_start(c),
                        "reviewed": bool(reviewed)})
        return out


@app.get("/api/me/attendance")
def my_attendance(user=Depends(require_user)):
    """會員中心：出席紀錄與缺席規則。"""
    with db() as conn:
        return {"status": noshow_status(conn, user), "absences": noshow_list(conn, user["id"])}


def noshow_list(conn, user_id: int) -> list[dict]:
    return rows(conn.execute(
        "SELECT r.id, r.noshow_cleared, c.id course_id, c.name, c.date, c.start_time FROM reservations r JOIN courses c ON c.id=r.course_id"
        " WHERE r.user_id=? AND r.status='absent' ORDER BY c.date DESC, c.start_time DESC LIMIT 50", (user_id,)))


@app.get("/api/me/cards")
def my_cards(user=Depends(require_user)):
    with db() as conn:
        today = now().date().isoformat()
        cards = rows(conn.execute("SELECT * FROM cards WHERE user_id=? ORDER BY expires_on DESC", (user["id"],)))
        for c in cards:
            c["valid"] = c["expires_on"] >= today and (c["type"] == "unlimited" or c["remaining"] > 0)
        orders = rows(conn.execute(
            "SELECT o.*, p.name plan_name FROM orders o JOIN plans p ON p.id=o.plan_id WHERE o.user_id=?"
            " ORDER BY o.id DESC", (user["id"],)))
        return {"cards": cards, "orders": orders}


@app.get("/api/me/notifications")
def my_notifications(user=Depends(require_user)):
    with db() as conn:
        items = rows(conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100",
                                  (user["id"],)))
        conn.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user["id"],))
        return items


# ---------------------------------------------------------------- 缺席（no-show）管理

FOREVER = "9999-12-31"


def noshow_status(conn, u: dict, s: dict | None = None) -> dict:
    """目前累計的缺席次數（最近 N 天、未免記、未因暫停歸零）與暫停報名狀態。"""
    s = s or get_settings(conn)
    since = (now().date() - timedelta(days=int(s["noshow_days"]))).isoformat() if int(s["noshow_days"] or 0) > 0 else ""
    count = conn.execute(
        "SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id WHERE r.user_id=? AND r.status='absent'"
        " AND r.noshow_cleared=0 AND c.date>=?", (u["id"], since)).fetchone()[0]
    until = u.get("blocked_until") or ""
    blocked = bool(until) and until >= now().date().isoformat()
    return {"enabled": bool(s["noshow_enabled"]) and saas.has("noshow"), "count": count, "limit": int(s["noshow_limit"]), "days": int(s["noshow_days"] or 0),
            "block_days": int(s["noshow_block_days"] or 0), "blocked": blocked,
            "blocked_until": until if blocked else "", "forever": blocked and until == FOREVER,
            "reason": u.get("block_reason", "") if blocked else ""}


def block_text(ns: dict) -> str:
    return "直到主辦解除" if ns["forever"] else f"到 {ns['blocked_until'][5:].replace('-', '/')}"


def ensure_not_blocked(conn, user: dict):
    ns = noshow_status(conn, user)
    if ns["blocked"]:
        fail(400, f"因{ns['reason'] or '缺席次數過多'}，報名暫停{block_text(ns)}；有疑問請聯絡主辦")


def check_noshow(conn, user_id: int, c: dict):
    """點名標記缺席後：快到上限先提醒，到上限自動暫停報名（計數歸零重算）並通知雙方。"""
    s = get_settings(conn)
    u = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
    if not s["noshow_enabled"] or not saas.has("noshow") or not u or u["role"] == "owner":
        return None
    ns = noshow_status(conn, u, s)
    if ns["blocked"]:
        return ns
    period = f"最近 {ns['days']} 天" if ns["days"] else "累計"
    if ns["count"] >= ns["limit"] > 0:
        until = FOREVER if not ns["block_days"] else (now().date() + timedelta(days=ns["block_days"] - 1)).isoformat()
        reason = f"{period}缺席 {ns['count']} 次"
        conn.execute("UPDATE users SET blocked_until=?, block_reason=? WHERE id=?", (until, reason, user_id))
        since = (now().date() - timedelta(days=ns["days"])).isoformat() if ns["days"] else ""
        conn.execute("UPDATE reservations SET noshow_cleared=2 WHERE user_id=? AND status='absent' AND noshow_cleared=0"
                     " AND course_id IN (SELECT id FROM courses WHERE date>=?)", (user_id, since))
        ns = noshow_status(conn, {**u, "blocked_until": until, "block_reason": reason}, s)
        notify(conn, user_id, f"您{reason}（最近一次：「{c['name']}」{c['date']}），依場館規定暫停報名{block_text(ns)}。"
                              "已報名的活動不受影響；如有誤會請聯絡主辦。")
        admin_notify(conn, "noshow", f"{u['name']} {reason}，已自動暫停報名{block_text(ns)}", "/admin/members")
    elif ns["limit"] and ns["count"] == ns["limit"] - 1:
        length = f" {ns['block_days']} 天" if ns["block_days"] else "，直到主辦解除"
        notify(conn, user_id, f"提醒：您{period}已缺席 {ns['count']} 次（最近一次：「{c['name']}」{c['date']}），"
                              f"再缺席 1 次將暫停報名{length}。不能來請提早取消。")
    return ns


def ensure_active(user: dict):
    if user["suspended"]:
        fail(403, "SUSPENDED")


@app.post("/api/courses/{course_id}/reserve")
def reserve(course_id: int, body: dict = Depends(json_body), user=Depends(require_user)):
    ensure_active(user)
    if tenancy.current().status in ("suspended", "cancelled"):
        fail(403, "這個場館暫停服務中，暫時不能報名，請聯絡主辦")
    b = body
    with db() as conn:
        c = get_course(conn, course_id)
        if not can_see(conn, c, user, str(b.get("code") or "")):
            fail(404, "找不到課程")
        ensure_not_blocked(conn, user)
        settings = get_settings(conn)
        v = course_view(conn, c, user, settings)
        if v["state"] not in ("book", "waitlist"):
            fail(400, f"此課程目前無法預約（{v['button']}）")
        if settings.get("open_days") and date.fromisoformat(c["date"]) > now().date() + timedelta(days=int(settings["open_days"])):
            fail(400, f"這堂課還沒開放報名（開課前 {settings['open_days']} 天開放）")
        if v["dupr_problem"]:
            fail(400, v["dupr_problem"])
        if v["state"] == "waitlist":
            if c["cost"] and not eligible_cards(conn, user["id"], c):
                fail(400, "沒有可用的課卡，請先購買課卡方案")
            conn.execute("INSERT INTO reservations (course_id, user_id, status, fee, created_at, updated_at)"
                         " VALUES (?,?,?,?,?,?)", (course_id, user["id"], "waitlist", c["fee"], stamp(), stamp()))
            notify(conn, user["id"], f"已加入「{c['name']}」{c['date']} {c['start_time']} 候補名單。")
            admin_notify(conn, "waitlist", f"{user['name']} 候補 {course_label(c)}", f"/admin/courses/{c['id']}")
            return {"result": "waitlist"}
        card_id, charged = charge(conn, user["id"], c, b.get("card_id"))
        conn.execute("INSERT INTO reservations (course_id, user_id, status, card_id, charged, fee, pay_due, created_at, updated_at)"
                     " VALUES (?,?,?,?,?,?,?,?,?)", (course_id, user["id"], "booked", card_id, charged, c["fee"], pay_due(c),
                                                    stamp(), stamp()))
        if c["fee"]:
            notify(conn, user["id"], f"「{c['name']}」{c['date']} {c['start_time']}：" + fee_notice(conn, c), course=c)
        else:
            notify(conn, user["id"], f"報名成功：「{c['name']}」{c['date']} {c['start_time']}。", course=c)
        admin_notify(conn, "booking", f"{user['name']} 報名 {course_label(c)}" + (f"（報名費 NT$ {c['fee']:,}，等對方匯款回填後五碼）" if c["fee"] else ""),
                     f"/admin/courses/{c['id']}")
        return {"result": "booked"}


@app.post("/api/courses/{course_id}/cancel")
def cancel(course_id: int, user=Depends(require_user)):
    with db() as conn:
        c = get_course(conn, course_id)
        v = course_view(conn, c, user, get_settings(conn))
        r = v["my_reservation"]
        if not r:
            fail(400, "您沒有預約這堂課")
        if not v["can_cancel"]:
            if r["status"] != "waitlist" and has_event(conn, course_id):
                fail(400, "團主已生成賽事，無法自行取消，請聯絡團主")
            fail(400, "已超過可自行取消的時間，請聯絡主辦")
        conn.execute("UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?", (stamp(), r["id"]))
        refund(conn, r)
        notify(conn, user["id"], f"已取消「{c['name']}」{c['date']} {c['start_time']}。"
                                 + (f"已付的報名費 NT$ {r['fee']:,} 將由場館與您聯繫退費。" if r["paid"] else ""))
        if r["paid"]:
            admin_notify(conn, "refund", f"{user['name']} 取消了已付款的 {course_label(c)}，請處理退費 NT$ {r['fee']:,}",
                         f"/admin/courses/{c['id']}")
        admin_notify(conn, "cancel", f"{user['name']} 取消{'候補' if r['status'] == 'waitlist' else '預約'} {course_label(c)}",
                     f"/admin/courses/{c['id']}")
        if r["status"] == "booked":
            promote_waitlist(conn, c)
        return {"ok": True}


@app.post("/api/plans/{plan_id}/order")
def order_plan(plan_id: int, user=Depends(require_user)):
    ensure_active(user)
    with db() as conn:
        p = one(conn.execute("SELECT * FROM plans WHERE id=? AND active=1", (plan_id,)))
        if not p:
            fail(404, "找不到方案")
        cur = conn.execute("INSERT INTO orders (user_id, plan_id, amount, created_at, updated_at) VALUES (?,?,?,?,?)",
                           (user["id"], plan_id, p["price"], stamp(), stamp()))
        notify(conn, user["id"], f"已送出「{p['name']}」購買申請，場館確認付款後即會開通課卡。")
        admin_notify(conn, "order", f"{user['name']} 申請購買「{p['name']}」NT$ {p['price']:,}，待確認收款", "/admin/orders")
        return {"order_id": cur.lastrowid}


@app.post("/api/reviews")
def create_review(body: dict = Depends(json_body), user=Depends(require_user)):
    b = body
    rating = int(b.get("rating", 0))
    if not 1 <= rating <= 5:
        fail(400, "請選擇 1–5 顆星")
    with db() as conn:
        c = get_course(conn, int(b.get("course_id", 0)))
        attended = one(conn.execute(
            "SELECT id FROM reservations WHERE course_id=? AND user_id=? AND status IN ('booked','attended')",
            (c["id"], user["id"])))
        if not attended or now() < course_start(c):
            fail(400, "上完課後才能評價")
        if one(conn.execute("SELECT id FROM reviews WHERE user_id=? AND course_id=?", (user["id"], c["id"]))):
            fail(400, "這堂課已評價過")
        conn.execute("INSERT INTO reviews (user_id, course_id, teacher_id, rating, comment, created_at)"
                     " VALUES (?,?,?,?,?,?)",
                     (user["id"], c["id"], c["teacher_id"], rating, str(b.get("comment", ""))[:500], stamp()))
        admin_notify(conn, "review", f"{user['name']} 給了 {rating} 星評價：{course_label(c)}", "/admin/reviews")
        return {"ok": True}


# ---------------------------------------------------------------- DUPR

def set_dupr(conn, user_id: int, b: dict, source: str):
    """綁定或更新 DUPR。有 DUPR 金鑰時分數一律向 DUPR 取得；沒有時使用填寫的分數（待場主核對）。"""
    if not b.get("dupr_id"):
        conn.execute("UPDATE users SET dupr_id='', dupr_name='', dupr_doubles=NULL, dupr_singles=NULL,"
                     " dupr_source='', dupr_verified=0, dupr_synced_at='' WHERE id=?", (user_id,))
        return
    try:
        dupr_id = dupr.normalize_id(str(b["dupr_id"]))
        taken = one(conn.execute("SELECT id FROM users WHERE dupr_id=? AND id!=?", (dupr_id, user_id)))
        if taken:
            fail(400, "這個 DUPR ID 已被其他帳號綁定，如有疑問請聯絡場館")
        if dupr.enabled():
            info = dupr.fetch_player(dupr_id)
            data = (dupr_id, info["name"], info["doubles"], info["singles"], "api")
        else:
            def rating(k):
                v = b.get(k)
                if v in (None, ""):
                    return None
                v = float(v)
                if not 1 <= v <= 8:
                    fail(400, "DUPR 分數需介於 1.000 與 8.000 之間")
                return round(v, 3)
            data = (dupr_id, str(b.get("name", ""))[:60], rating("doubles"), rating("singles"),
                    "owner" if source == "owner" else "manual")
    except dupr.DuprError as e:
        fail(400, str(e))
    # 場主設定即視為已驗證；同一個 ID 且分數沒被本人改動才保留驗證狀態
    old = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
    unchanged = old["dupr_id"] == dupr_id and (data[4] == "api" or
                                               (old["dupr_doubles"], old["dupr_singles"]) == (data[2], data[3]))
    verified = 1 if source == "owner" or (unchanged and old["dupr_verified"]) else 0
    conn.execute("UPDATE users SET dupr_id=?, dupr_name=?, dupr_doubles=?, dupr_singles=?, dupr_source=?,"
                 " dupr_verified=?, dupr_synced_at=? WHERE id=?", (*data, verified, stamp(), user_id))


@app.get("/api/dupr/config")
def dupr_config():
    return {"api_enabled": dupr.enabled()}


@app.put("/api/me/dupr")
def link_dupr(body: dict = Depends(json_body), user=Depends(require_user)):
    b = body
    with db() as conn:
        set_dupr(conn, user["id"], b, source="self")
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


@app.post("/api/me/dupr/refresh")
def refresh_dupr(user=Depends(require_user)):
    if not user["dupr_id"]:
        fail(400, "尚未綁定 DUPR")
    if not dupr.enabled():
        fail(400, "場館尚未開通 DUPR 自動同步，請直接修改分數")
    with db() as conn:
        set_dupr(conn, user["id"], {"dupr_id": user["dupr_id"]}, source="self")
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


# ---------------------------------------------------------------- 單次報名費

def pay_due(c: dict) -> str:
    """回填後五碼的期限（報名或遞補起算 pay_hours 小時；0＝開始前 1 小時）。沒回填就不算報名成功，逾時名額讓給候補。"""
    if not c["fee"]:
        return ""
    due = course_start(c) - timedelta(hours=1)
    if c["pay_hours"]:
        due = min(now() + timedelta(hours=c["pay_hours"]), due)
    return max(due, now() + timedelta(minutes=30)).isoformat(timespec="minutes")


def payment_ready(settings: dict) -> bool:
    return bool(settings["payment_info"].strip()) and settings["payment_info"] != DEFAULT_SETTINGS["payment_info"]


def fee_notice(conn, c: dict) -> str:
    if not c["fee"]:
        return ""
    s = get_settings(conn)
    due = pay_due(c)
    return (f"名額先為您保留，還沒完成報名：請匯款報名費 NT$ {c['fee']:,}（"
            + (f"付款方式：{s['payment_info'].strip()}" if payment_ready(s) else "付款方式請洽主辦")
            + "），匯款後到活動頁回填「匯款帳號後五碼」才算報名成功"
            + (f"，請在 {due[5:10].replace('-', '/')} {due[11:16]} 前完成，逾時名額會讓給下一位" if due else "") + "。")


def release_overdue(conn) -> int:
    """逾期未付款（也沒回報付款）的名額自動取消，讓給候補。"""
    n = 0
    for r in rows(conn.execute(
            "SELECT r.*, u.name user_name FROM reservations r JOIN users u ON u.id=r.user_id WHERE r.status='booked'"
            " AND r.fee>0 AND r.paid=0 AND r.pay_note='' AND r.pay_due!='' AND r.pay_due<?", (now().isoformat(timespec="minutes"),))):
        c = get_course(conn, r["course_id"])
        if has_event(conn, c["id"]) or now() >= course_start(c):
            continue
        conn.execute("UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?", (stamp(), r["id"]))
        notify(conn, r["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 超過付款期限，名額已釋出。如仍想參加請重新報名。", course=c)
        admin_notify(conn, "overdue", f"{r['user_name']} 逾期未付款，已自動取消 {course_label(c)}", f"/admin/courses/{c['id']}")
        promote_waitlist(conn, c)
        n += 1
    return n


def send_reminders(conn) -> int:
    """開課前一天（設定的時間之後）提醒已報名的學員；每筆報名只提醒一次，場主收到一則明日總覽。"""
    s = get_settings(conn)
    if not s.get("reminder_enabled", True) or not saas.has("reminder"):
        return 0
    t = now()
    at = datetime.combine(t.date(), datetime.min.time()) + timedelta(hours=min(max(int(s.get("reminder_hour", 20)), 0), 23))
    if t < at:
        return 0
    tomorrow = (t.date() + timedelta(days=1)).isoformat()
    sent = 0
    courses = rows(conn.execute("SELECT * FROM courses WHERE date=? AND status='open' ORDER BY start_time", (tomorrow,)))
    for c in courses:
        groups = {}
        ev = one(conn.execute("SELECT id FROM events WHERE course_id=?", (c["id"],)))
        if ev:
            for g in rows(conn.execute("SELECT name, entries FROM event_groups WHERE event_id=?", (ev["id"],))):
                for e in json.loads(g["entries"]):
                    for p in e:
                        groups[p] = g["name"]
        for r in rows(conn.execute("SELECT * FROM reservations WHERE course_id=? AND status='booked' AND reminded=0", (c["id"],))):
            conn.execute("UPDATE reservations SET reminded=1 WHERE id=?", (r["id"],))
            if r["created_at"] >= at.isoformat(timespec="seconds"):
                continue  # 提醒時間之後才報名的，報名成功通知就是提醒
            text = f"明天見！「{c['name']}」{tomorrow[5:].replace('-', '/')} {c['start_time']}–{c['end_time']}"
            text += f"，地點：{c['location']}。" if c["location"] else "。"
            if r["user_id"] in groups:
                text += f"賽程已排好，您在 {groups[r['user_id']]}。"
            if r["fee"] and not r["paid"]:
                text += f"報名費 NT$ {r['fee']:,} 還沒完成付款，請記得付款並回報。"
            notify(conn, r["user_id"], text, course=c, reminder=True)
            sent += 1
    key = f"digest:{tomorrow}"
    if courses and not one(conn.execute("SELECT key FROM kv WHERE key=?", (key,))):
        conn.execute("INSERT INTO kv VALUES (?, ?)", (key, stamp()))
        total = sum(course_counts(conn, c["id"])[0] for c in courses)
        unpaid = conn.execute(f"SELECT COUNT(*) FROM reservations WHERE status='booked' AND fee>0 AND paid=0 AND course_id IN "
                              f"({','.join('?' * len(courses))})", tuple(c["id"] for c in courses)).fetchone()[0]
        text = f"明天 {tomorrow[5:].replace('-', '/')} 有 {len(courses)} 堂、共 {total} 人：" + "、".join(
            f"{c['start_time']} {c['name']}" for c in courses[:5]) + ("…" if len(courses) > 5 else "")
        if unpaid:
            text += f"。還有 {unpaid} 筆報名費沒收到"
        admin_notify(conn, "digest", text, "/admin/calendar")
    return sent


def sweeper():
    import time as _t
    while True:
        _t.sleep(300)
        try:
            saas.sweep()
        except Exception:  # noqa: BLE001
            pass
        for t in tenancy.all_with_data():  # 逐館處理；停用的場館不再提醒、釋出名額
            if t.status not in ("trial", "active", "past_due"):
                continue
            jobs = (release_overdue, send_reminders) + ((demo.top_up,) if demo.kind_of(t.slug) else ())
            for job in jobs:
                try:
                    with tenancy.use(t), db() as conn:
                        job(conn)
                except Exception:  # noqa: BLE001 — 背景工作不能讓服務掛掉
                    pass


@app.post("/api/admin/sweep")
def run_sweep(owner=Depends(require_owner)):
    """立即執行一次逾期檢查與開課提醒（背景每 5 分鐘也會自動跑）。"""
    if tenancy.current().slug == tenancy.DEFAULT_SLUG:
        saas.sweep()  # 平台的每日檢查（扣款寬限期、釋出沒付款的網址）只由主場館觸發
    with db() as conn:
        released = release_overdue(conn)
    with db() as conn:
        return {"released": released, "reminded": send_reminders(conn)}


@app.put("/api/courses/{course_id}/payment")
def payment_note(course_id: int, body: dict = Depends(json_body), user=Depends(require_user)):
    """學員填寫付款資訊（匯款末五碼、付款方式等），供場主核對。"""
    note = str(body.get("note", "")).strip()[:100]
    with db() as conn:
        c = get_course(conn, course_id)
        r = one(conn.execute("SELECT * FROM reservations WHERE course_id=? AND user_id=? AND status IN ('booked','attended','absent')"
                             " ORDER BY id DESC LIMIT 1", (course_id, user["id"])))
        if not r or not r["fee"]:
            fail(400, "這場不需要付報名費")
        if r["paid"]:
            fail(400, "場館已確認收款")
        conn.execute("UPDATE reservations SET pay_note=?, updated_at=? WHERE id=?", (note, stamp(), r["id"]))
        if note and not r["pay_note"]:
            notify(conn, user["id"], f"報名成功：「{c['name']}」{c['date']} {c['start_time']}，已收到您回填的後五碼 {note}，主辦對帳後會再通知您。", course=c)
        if note:
            admin_notify(conn, "payment", f"{user['name']} 回報已付款（{note}）：{course_label(c)}，請核對", f"/admin/courses/{c['id']}")
        return {"ok": True}


@app.post("/api/admin/reservations/{res_id}/payment")
def mark_paid(res_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """場主確認收款／取消收款（退費後可改回未付款）。"""
    paid = bool(body.get("paid"))
    with db() as conn:
        r = one(conn.execute("SELECT * FROM reservations WHERE id=?", (res_id,)))
        if not r:
            fail(404, "找不到預約")
        if not r["fee"]:
            fail(400, "這筆預約沒有報名費")
        c = get_course(conn, r["course_id"])
        conn.execute("UPDATE reservations SET paid=?, paid_at=?, updated_at=? WHERE id=?",
                     (1 if paid else 0, stamp() if paid else "", stamp(), res_id))
        if paid and not r["paid"]:
            notify(conn, r["user_id"], f"主辦已確認收到「{c['name']}」{c['date']} {c['start_time']} 的報名費 NT$ {r['fee']:,}。", course=c)
        return {"ok": True}


@app.get("/api/admin/fees")
def admin_fees(owner=Depends(require_owner)):
    """所有活動的報名費：待收（含學員回報）與最近 30 天已收。"""
    since = (now() - timedelta(days=30)).isoformat()
    with db() as conn:
        return rows(conn.execute(
            "SELECT r.id, r.course_id, r.fee, r.paid, r.pay_note, r.pay_due, r.paid_at, r.created_at, u.name user_name, u.phone,"
            " c.name course_name, c.date, c.start_time FROM reservations r JOIN users u ON u.id=r.user_id"
            " JOIN courses c ON c.id=r.course_id WHERE r.fee>0 AND r.status IN ('booked','attended','absent') AND c.status='open'"
            " AND (r.paid=0 OR r.paid_at>=?) ORDER BY r.paid, r.pay_note='' , c.date, c.start_time LIMIT 500", (since,)))


def xlsx_response(name: str, header: list, body: list) -> Response:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in body:
        ws.append(r)
    for i in range(len(header)):
        ws.column_dimensions[chr(65 + i)].width = 16
    buf = __import__("io").BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(name)}"})


@app.get("/api/admin/courses/{course_id}/roster/export")
def roster_export(course_id: int, owner=Depends(require_owner)):
    """名單下載（簽到、保險、聯絡用）。"""
    status = {"booked": "已報名", "attended": "出席", "absent": "缺席", "waitlist": "候補"}
    with db() as conn:
        c = get_course(conn, course_id)
        body = []
        for i, r in enumerate(rows(conn.execute(
                "SELECT r.*, u.name, u.phone, u.email, u.dupr_id, u.dupr_doubles, u.dupr_singles, u.note FROM reservations r"
                " JOIN users u ON u.id=r.user_id WHERE r.course_id=? AND r.status!='cancelled' ORDER BY r.status='waitlist', r.id",
                (course_id,))), 1):
            body.append([i, r["name"], r["phone"] or "", r["email"] or "", status.get(r["status"], r["status"]),
                         r["fee"] or "", ("已付款" if r["paid"] else "待付款") if r["fee"] else "", r["pay_note"],
                         r["dupr_id"], r[f"dupr_{c['dupr_format']}"] if c["dupr_required"] else "", "", r["note"]])
    return xlsx_response(f"名單_{c['date']}_{c['name']}.xlsx",
                         ["#", "姓名", "手機", "信箱", "狀態", "報名費", "付款", "付款回報", "DUPR ID", "DUPR 分數", "簽名", "備註"], body)


@app.get("/api/admin/courses/{course_id}/event/export")
def event_export(course_id: int, owner=Depends(require_owner)):
    """比分下載（CSV，可整理後上傳 DUPR）。"""
    with db() as conn:
        c = get_course(conn, course_id)
        ev = event_view(conn, c, owner)
        if not ev:
            fail(404, "這場還沒有賽事")
        ids = {p["id"] for g in ev["groups"] for gm in g["games"] for p in gm["a"] + gm["b"]}
        dupr_ids = {r["id"]: r["dupr_id"] for r in conn.execute(
            f"SELECT id, dupr_id FROM users WHERE id IN ({','.join('?' * len(ids))})", tuple(ids))} if ids else {}
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["date", "event", "group", "round", "format", "team_a_player1", "team_a_player1_dupr_id", "team_a_player2",
                "team_a_player2_dupr_id", "team_b_player1", "team_b_player1_dupr_id", "team_b_player2", "team_b_player2_dupr_id",
                "score_a", "score_b", "status"])
    for g in ev["groups"]:
        for gm in g["games"]:
            def side(ps):
                cells = []
                for p in (ps + [None, None])[:2]:
                    cells += [p["name"], dupr_ids.get(p["id"], "")] if p else ["", ""]
                return cells
            w.writerow([c["date"], c["name"], g["name"], gm["round"], ev["format_name"], *side(gm["a"]), *side(gm["b"]),
                        gm["score_a"] if gm["score_a"] is not None else "", gm["score_b"] if gm["score_b"] is not None else "",
                        {"confirmed": "已確認", "reported": "待確認", "pending": "未打"}[gm["status"]]])
    fname = urllib.parse.quote(f"比分_{c['date']}_{c['name']}.csv")
    return Response("\ufeff" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"})


# ---------------------------------------------------------------- DUPR 賽事（分組、賽程、比分）

def event_format(c: dict) -> str:
    """單打場一律單打循環賽；雙打場依團主選的輪換／固定搭檔。"""
    if c["dupr_format"] == "singles":
        return "singles"
    return c["match_format"] if c["match_format"] in ("rotating", "fixed") else "rotating"


def has_event(conn, course_id: int) -> bool:
    return bool(conn.execute("SELECT 1 FROM events WHERE course_id=?", (course_id,)).fetchone())


def course_players(conn, c: dict) -> list[dict]:
    """已報名（含已點名）的球員，依該場依據的 DUPR 分數由高到低。"""
    col = f"dupr_{c['dupr_format']}"
    return rows(conn.execute(
        f"SELECT u.id, u.name, u.avatar_url, u.{col} rating, u.dupr_verified, r.partner_id FROM reservations r"
        " JOIN users u ON u.id=r.user_id WHERE r.course_id=? AND r.status IN ('booked','attended','absent')"
        f" ORDER BY u.{col} IS NULL, u.{col} DESC, r.id", (c["id"],)))


def game_row(g: dict) -> dict:
    return {**g, "a": json.loads(g["side_a"]), "b": json.loads(g["side_b"]), "bye": json.loads(g["bye"])}


def event_view(conn, c: dict, viewer: dict | None) -> dict | None:
    ev = one(conn.execute("SELECT * FROM events WHERE course_id=?", (c["id"],)))
    if not ev:
        return None
    groups = rows(conn.execute("SELECT * FROM event_groups WHERE event_id=? ORDER BY sort", (ev["id"],)))
    games = [game_row(g) for g in rows(conn.execute(
        "SELECT * FROM event_games WHERE event_id=? ORDER BY group_id, round", (ev["id"],)))]
    ids = {p for g in groups for e in json.loads(g["entries"]) for p in e}
    col = f"dupr_{c['dupr_format']}"
    people = {u["id"]: u for u in rows(conn.execute(
        f"SELECT id, name, avatar_url, {col} rating FROM users WHERE id IN ({','.join('?' * len(ids))})", tuple(ids)))} if ids else {}
    is_owner = bool(viewer and viewer["role"] == "owner")
    full = is_owner or bool(viewer and viewer["id"] in ids)  # 參賽者和團主看全名，其他人看遮罩姓名

    def person(uid):
        u = people.get(uid)
        if not u:
            return {"id": uid, "name": "（已刪除）", "avatar_url": "", "rating": None}
        return {"id": uid, "name": u["name"] if full else mask_name(u["name"]), "avatar_url": u["avatar_url"],
                "rating": u["rating"]}

    me = viewer["id"] if viewer else None
    out_groups = []
    for grp in groups:
        entries = json.loads(grp["entries"])
        gg = [g for g in games if g["group_id"] == grp["id"]]
        view_games = []
        for g in gg:
            mine = "a" if me in g["a"] else "b" if me in g["b"] else None
            reporter_side = "a" if g["reported_by"] in g["a"] else "b" if g["reported_by"] in g["b"] else None
            view_games.append({
                "id": g["id"], "round": g["round"], "status": g["status"], "score_a": g["score_a"], "score_b": g["score_b"],
                "a": [person(p) for p in g["a"]], "b": [person(p) for p in g["b"]], "bye": [person(p) for p in g["bye"]],
                "mine": mine,
                "reported_by": person(g["reported_by"])["name"] if g["reported_by"] else None,
                "can_report": bool(mine) and g["status"] != "confirmed",
                "can_confirm": bool(mine) and g["status"] == "reported" and reporter_side not in (None, mine),
            })
        table = matches.standings(ev["format"], entries, gg)
        for r in table:
            r["players"] = [person(p) for p in r["players"]]
        out_groups.append({"id": grp["id"], "name": grp["name"], "entries": [[person(p) for p in e] for e in entries],
                           "games": view_games, "standings": table})
    done = sum(1 for g in games if g["status"] == "confirmed")
    return {"id": ev["id"], "format": ev["format"], "format_name": matches.FORMATS[ev["format"]],
            "games_to": ev["games_to"], "created_at": ev["created_at"], "groups": out_groups,
            "progress": {"confirmed": done, "total": len(games)}, "is_player": bool(me in ids)}


def get_game(conn, game_id: int) -> tuple[dict, dict, dict]:
    g = one(conn.execute("SELECT * FROM event_games WHERE id=?", (game_id,)))
    if not g:
        fail(404, "找不到這場比賽")
    ev = one(conn.execute("SELECT * FROM events WHERE id=?", (g["event_id"],)))
    return game_row(g), ev, get_course(conn, ev["course_id"])


def game_label(c: dict, g: dict) -> str:
    return f"{course_label(c)} 第 {g['round']} 局"


@app.get("/api/courses/{course_id}/event")
def course_event(course_id: int, request: Request, user=Depends(current_user)):
    with db() as conn:
        c = get_course(conn, course_id)
        if not can_see(conn, c, user, request.query_params.get("code")):
            fail(404, "找不到課程")
        return {"event": event_view(conn, c, user)}


@app.put("/api/courses/{course_id}/partner")
def set_partner(course_id: int, body: dict = Depends(json_body), user=Depends(require_user)):
    """固定搭檔場：已報名的學員用對方的手機或信箱指定隊友（對方也要已報名）。"""
    b = body
    contact = str(b.get("contact", "")).strip()
    with db() as conn:
        c = get_course(conn, course_id)
        if event_format(c) != "fixed":
            fail(400, "這場不是固定搭檔賽制")
        if has_event(conn, course_id):
            fail(400, "團主已生成賽事，無法更改隊友")
        mine = one(conn.execute("SELECT * FROM reservations WHERE course_id=? AND user_id=? AND status IN ('booked','attended','absent')",
                                (course_id, user["id"])))
        if not mine:
            fail(400, "報名這場之後才能指定隊友")
        partner = None
        if contact:
            partner = one(conn.execute("SELECT id, name FROM users WHERE email=? OR phone=?",
                                       (contact.lower(), clean_phone(contact))))
            if not partner or partner["id"] == user["id"]:
                fail(400, "找不到這位球員，請確認手機或信箱")
            if not one(conn.execute("SELECT id FROM reservations WHERE course_id=? AND user_id=? AND status IN ('booked','attended','absent')",
                                    (course_id, partner["id"]))):
                fail(400, "對方還沒有報名這場，請對方先報名再指定")
            notify(conn, partner["id"], f"{user['name']} 在{course_label(c)}指定您為隊友。")
        conn.execute("UPDATE reservations SET partner_id=? WHERE id=?", (partner["id"] if partner else None, mine["id"]))
        return {"partner": partner}


@app.get("/api/courses/{course_id}/partner")
def get_partner(course_id: int, user=Depends(require_user)):
    with db() as conn:
        r = one(conn.execute("SELECT partner_id FROM reservations WHERE course_id=? AND user_id=? AND status IN ('booked','attended','absent')",
                             (course_id, user["id"])))
        pid = r["partner_id"] if r else None
        partner = one(conn.execute("SELECT id, name FROM users WHERE id=?", (pid,))) if pid else None
        chosen_by = rows(conn.execute(
            "SELECT u.id, u.name FROM reservations r JOIN users u ON u.id=r.user_id WHERE r.course_id=? AND r.partner_id=?"
            " AND r.status IN ('booked','attended','absent')", (course_id, user["id"])))
        return {"partner": partner, "chosen_by": chosen_by}


def check_score_side(g: dict, user: dict) -> str:
    side = "a" if user["id"] in g["a"] else "b" if user["id"] in g["b"] else None
    if not side:
        fail(403, "只有這場的球員可以回報比分")
    return side


@app.post("/api/event-games/{game_id}/report")
def report_score(game_id: int, body: dict = Depends(json_body), user=Depends(require_user)):
    """球員回報比分；由對手確認後才算數。回報後改分也要重新確認。"""
    b = body
    with db() as conn:
        g, ev, c = get_game(conn, game_id)
        side = check_score_side(g, user)
        if g["status"] == "confirmed":
            fail(400, "這場比分已確認，如需修改請聯絡團主")
        problem = matches.score_problem(b.get("score_a"), b.get("score_b"), ev["games_to"], strict=True)
        if problem:
            fail(400, problem)
        conn.execute("UPDATE event_games SET score_a=?, score_b=?, status='reported', reported_by=?, confirmed_by=NULL,"
                     " updated_at=? WHERE id=?", (int(b["score_a"]), int(b["score_b"]), user["id"], stamp(), game_id))
        other = g["b"] if side == "a" else g["a"]
        for uid in other:
            notify(conn, uid, f"{user['name']} 回報了{game_label(c, g)}的比分 {b['score_a']}:{b['score_b']}，請確認。", course=c)
        return {"ok": True}


@app.post("/api/event-games/{game_id}/confirm")
def confirm_score(game_id: int, body: dict = Depends(json_body), user=Depends(require_user)):
    with db() as conn:
        g, ev, c = get_game(conn, game_id)
        if "score_a" in body and (body.get("score_a"), body.get("score_b")) != (g["score_a"], g["score_b"]):
            fail(409, f"對方剛改了比分（現在是 {g['score_a']}:{g['score_b']}），請確認後再按一次")
        side = check_score_side(g, user)
        if g["status"] != "reported":
            fail(400, "這場還沒有人回報比分" if g["status"] == "pending" else "這場比分已確認")
        if g["reported_by"] in (g["a"] if side == "a" else g["b"]):
            fail(400, "需由對手確認比分")
        conn.execute("UPDATE event_games SET status='confirmed', confirmed_by=?, updated_at=? WHERE id=?",
                     (user["id"], stamp(), game_id))
        return {"ok": True}


def event_admin_view(conn, c: dict, owner: dict) -> dict:
    fmt = event_format(c)
    players = course_players(conn, c)
    return {"course": {k: c[k] for k in ("id", "name", "date", "start_time", "end_time", "dupr_format", "games_to")},
            "format": fmt, "format_name": matches.FORMATS[fmt],
            "players": [{k: p[k] for k in ("id", "name", "avatar_url", "rating", "dupr_verified", "partner_id")} for p in players],
            "event": event_view(conn, c, owner)}


@app.get("/api/admin/courses/{course_id}/event")
def admin_event(course_id: int, owner=Depends(require_owner)):
    """賽事現況；還沒生成時附上建議分組（依 DUPR 分數），團主可調整後再生成。"""
    with db() as conn:
        c = get_course(conn, course_id)
        out = event_admin_view(conn, c, owner)
        out["plan"], out["plan_error"] = None, None
        if not out["event"]:
            players = course_players(conn, c)
            rating = {p["id"]: p["rating"] for p in players}
            ids = [p["id"] for p in players]
            try:
                if out["format"] == "fixed":
                    entries = matches.pair_teams(ids, rating, {p["id"]: p["partner_id"] for p in players})
                else:
                    entries = [[i] for i in ids]
                out["plan"] = matches.plan_groups(out["format"], entries, rating)
            except ValueError as e:
                out["plan_error"] = str(e)
        return out


@app.post("/api/admin/courses/{course_id}/event")
def create_event(course_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """依團主確認的分組生成賽程。groups：[[參賽單位, …], …]，參賽單位是 [球員] 或 [球員, 隊友]。"""
    b = body
    with db() as conn:
        c = get_course(conn, course_id)
        if not c["dupr_required"]:
            fail(400, "只有 DUPR 場可以生成賽事")
        if has_event(conn, course_id):
            fail(400, "這場已經有賽事，要重新生成請先刪除")
        fmt = event_format(c)
        size = matches.entry_size(fmt)
        try:
            groups = [[[int(p) for p in e] for e in grp] for grp in b.get("groups") or [] if grp]
        except (TypeError, ValueError):
            fail(400, "分組資料格式錯誤")
        if not groups:
            fail(400, "請先分組")
        booked = {p["id"]: p for p in course_players(conn, c)}
        seen = [p for grp in groups for e in grp for p in e]
        if len(seen) != len(set(seen)):
            fail(400, "同一位球員不能出現兩次")
        if set(seen) != set(booked):
            missing = [booked[i]["name"] for i in booked if i not in seen]
            fail(400, f"還有人沒有分組：{'、'.join(missing)}" if missing else "分組中有人沒有報名這場")
        for i, grp in enumerate(groups):
            if any(len(e) != size for e in grp):
                fail(400, "固定搭檔每隊需要 2 人" if size == 2 else "分組資料格式錯誤")
            if len(grp) < matches.min_group(fmt):
                fail(400, f"{matches.GROUP_NAMES[i]} 組人數不足（{matches.FORMATS[fmt]}每組至少 {matches.min_group(fmt)} {'隊' if size == 2 else '人'}）")
            if fmt == "rotating" and len(grp) > 7:
                fail(400, f"{matches.GROUP_NAMES[i]} 組超過 7 人，請再分一組")
        cur = conn.execute("INSERT INTO events (course_id, format, games_to, created_at) VALUES (?,?,?,?)",
                           (course_id, fmt, c["games_to"] or 11, stamp()))
        ev_id = cur.lastrowid
        for i, grp in enumerate(groups):
            gid = conn.execute("INSERT INTO event_groups (event_id, name, sort, entries) VALUES (?,?,?,?)",
                               (ev_id, f"{matches.GROUP_NAMES[i]} 組", i, json.dumps(grp))).lastrowid
            try:
                sched = matches.schedule(fmt, grp)
            except ValueError as e:
                fail(400, str(e))
            for n, g in enumerate(sched, 1):
                conn.execute("INSERT INTO event_games (event_id, group_id, round, side_a, side_b, bye, updated_at)"
                             " VALUES (?,?,?,?,?,?,?)", (ev_id, gid, n, json.dumps(g["a"]), json.dumps(g["b"]),
                                                         json.dumps(g["bye"]), stamp()))
            for e in grp:
                for p in e:
                    notify(conn, p, f"{course_label(c)}賽程排好了，您在 {matches.GROUP_NAMES[i]} 組，"
                                    f"共 {sum(1 for g in sched if p in g['a'] + g['b'])} 局。", course=c)
        return event_admin_view(conn, c, owner)


@app.delete("/api/admin/courses/{course_id}/event")
def delete_event(course_id: int, owner=Depends(require_owner)):
    with db() as conn:
        ev = one(conn.execute("SELECT id FROM events WHERE course_id=?", (course_id,)))
        if not ev:
            fail(404, "這場還沒有賽事")
        conn.execute("DELETE FROM event_games WHERE event_id=?", (ev["id"],))
        conn.execute("DELETE FROM event_groups WHERE event_id=?", (ev["id"],))
        conn.execute("DELETE FROM events WHERE id=?", (ev["id"],))
        return {"ok": True}


@app.put("/api/admin/event-games/{game_id}")
def admin_score(game_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """團主登錄或修改比分，直接算確認；clear=true 清除比分。"""
    b = body
    with db() as conn:
        g, ev, c = get_game(conn, game_id)
        if b.get("clear"):
            conn.execute("UPDATE event_games SET score_a=NULL, score_b=NULL, status='pending', reported_by=NULL,"
                         " confirmed_by=NULL, updated_at=? WHERE id=?", (stamp(), game_id))
            return {"ok": True}
        problem = matches.score_problem(b.get("score_a"), b.get("score_b"), ev["games_to"], strict=False)
        if problem:
            fail(400, problem)
        conn.execute("UPDATE event_games SET score_a=?, score_b=?, status='confirmed', confirmed_by=?, updated_at=?"
                     " WHERE id=?", (int(b["score_a"]), int(b["score_b"]), owner["id"], stamp(), game_id))
        return {"ok": True}


# ---------------------------------------------------------------- owner API

@app.get("/api/admin/dashboard")
def dashboard(owner=Depends(require_owner)):
    with db() as conn:
        s = get_settings(conn)
        today = now().date().isoformat()
        setup = {
            "venue": s["name"] != DEFAULT_SETTINGS["name"],
            "payment": payment_ready(s),
            "course": bool(one(conn.execute("SELECT id FROM courses LIMIT 1"))),
            "booking": bool(one(conn.execute("SELECT r.id FROM reservations r JOIN users u ON u.id=r.user_id WHERE u.role='student' LIMIT 1"))),
            "line_push": line_push.enabled(),
        }
        cs = rows(conn.execute("SELECT * FROM courses WHERE date=? ORDER BY start_time", (today,)))
        week_end = (now().date() + timedelta(days=7)).isoformat()
        return {
            "today": [course_view(conn, c, None, s) for c in cs],
            "setup": setup,
            "pending_orders": conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
            "unpaid_fees": conn.execute("SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id WHERE r.fee>0 AND r.paid=0"
                                        " AND r.status IN ('booked','attended','absent') AND c.status='open'").fetchone()[0],
            "members": conn.execute("SELECT COUNT(*) FROM users WHERE role='student' AND deleted=0").fetchone()[0],
            "blocked_members": conn.execute("SELECT COUNT(*) FROM users WHERE deleted=0 AND blocked_until>=?", (today,)).fetchone()[0],
            "week_bookings": conn.execute(
                "SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id"
                " WHERE r.status='booked' AND c.date BETWEEN ? AND ?", (today, week_end)).fetchone()[0],
            "month_revenue": conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='paid' AND substr(updated_at,1,7)=?",
                (today[:7],)).fetchone()[0] + conn.execute(
                "SELECT COALESCE(SUM(fee),0) FROM reservations WHERE paid=1 AND substr(paid_at,1,7)=?",
                (today[:7],)).fetchone()[0],
        }


@app.get("/api/admin/courses")
def admin_courses(request: Request, owner=Depends(require_owner)):
    start = request.query_params.get("from") or now().date().isoformat()
    end = request.query_params.get("to") or (date.fromisoformat(start) + timedelta(days=6)).isoformat()
    with db() as conn:
        s = get_settings(conn)
        cs = rows(conn.execute("SELECT * FROM courses WHERE date BETWEEN ? AND ? ORDER BY date, start_time",
                               (start, end)))
        return [course_view(conn, c, None, s) for c in cs]


COURSE_FIELDS = ("name", "category", "teacher_id", "substitute", "date", "start_time", "end_time", "capacity",
                 "cost", "beginner", "description", "location", "booking_deadline_min", "cancel_deadline_min",
                 "plan_ids", "dupr_required", "dupr_format", "dupr_min", "dupr_max", "dupr_verified_only", "template_id",
                 "match_format", "games_to", "listed", "fee", "pay_hours", "cover_url", "show_attendees", "branch_id")
# 範本只存課程內容與預設時間，不含日期
TEMPLATE_FIELDS = tuple(k for k in COURSE_FIELDS if k not in ("date", "template_id")) + ("active", "sort")
# 修改範本時同步到未開始課程的欄位（不含時間與日期）
SYNC_FIELDS = tuple(k for k in TEMPLATE_FIELDS if k not in ("start_time", "end_time", "active", "sort"))


TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def clean_course(b: dict) -> dict:
    out = {k: b[k] for k in COURSE_FIELDS if k in b}
    if "date" in out:
        try:
            out["date"] = date.fromisoformat(str(out["date"])).isoformat()
        except ValueError:
            fail(400, "日期格式不正確")
    for k in ("start_time", "end_time"):
        if k in out and not TIME_RE.match(str(out[k])):
            fail(400, "時間格式不正確（例如 19:00）")
    if "cover_url" in out:
        url = str(out["cover_url"] or "").strip()[:300]
        if url and not re.match(r"^(uploads/[0-9a-f]{32}\.(jpg|png|webp|gif)|https://\S+)$", url):
            fail(400, "封面圖片網址不正確")
        out["cover_url"] = url
    for k in ("dupr_min", "dupr_max"):
        if k in out:
            out[k] = round(float(out[k]), 3) if out[k] not in (None, "") else None
    if out.get("dupr_format") not in (None, "doubles", "singles"):
        out["dupr_format"] = "doubles"
    if out.get("match_format") not in (None, "rotating", "fixed"):
        out["match_format"] = "rotating"
    if "games_to" in out:
        out["games_to"] = min(max(int(out["games_to"] or 11), 5), 25)
    for k in ("substitute", "beginner", "dupr_required", "dupr_verified_only", "listed", "show_attendees"):
        if k in out:
            out[k] = 1 if out[k] else 0
    for k in ("capacity", "cost", "booking_deadline_min", "cancel_deadline_min", "fee", "pay_hours"):
        if k in out:
            out[k] = max(int(out[k] or 0), 0)
    if out.get("fee"):
        out["cost"] = 0  # 單次報名費的活動不扣課卡
    if out.get("branch_id"):
        saas.need("multisite")
    for k in ("teacher_id", "template_id", "branch_id"):
        if k in out:
            out[k] = int(out[k]) if out[k] else None
    if "plan_ids" in out:
        out["plan_ids"] = json.dumps([int(x) for x in out["plan_ids"] or []])
    # 方案功能：收費對帳、課卡、DUPR（依內容判斷；整組 API 的限制見 saas.FEATURE_RULES）
    if out.get("fee"):
        saas.need("fee")
    if out.get("cost"):
        saas.need("cards")
    if out.get("dupr_required"):
        saas.need("dupr")
    return out


@app.post("/api/admin/courses")
def create_course(body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    data = clean_course(b)
    if "cost" not in data and not saas.has("cards"):
        data["cost"] = 0  # 沒有課卡功能的方案：預設免費（資料庫預設是扣 1 堂）
    if not data.get("name") or not data.get("date") or not data.get("start_time") or not data.get("end_time"):
        fail(400, "請填寫課程名稱、日期與時間")
    repeat = min(max(int(b.get("repeat_weeks", 1) or 1), 1), 26)
    first = date.fromisoformat(data["date"])
    ids = []
    with db() as conn:
        for w in range(repeat):
            row = {**data, "date": (first + timedelta(weeks=w)).isoformat(), "created_at": stamp(),
                   "share_code": new_share_code(conn)}
            cols = ",".join(row)
            cur = conn.execute(f"INSERT INTO courses ({cols}) VALUES ({','.join('?' * len(row))})",
                               tuple(row.values()))
            ids.append(cur.lastrowid)
            if w == 0 and b.get("share_code"):  # 自訂網址只用在第一場（每週重複的其他場自動產生）
                set_share_code(conn, "course", get_course(conn, cur.lastrowid), b["share_code"])
    return {"ids": ids}


# ---------------------------------------------------------------- course templates（課程範本）

def clean_template(b: dict) -> dict:
    out = clean_course({k: v for k, v in b.items() if k in COURSE_FIELDS})
    out.pop("date", None)
    out.pop("template_id", None)
    for k in ("active", "sort"):
        if k in b:
            out[k] = int(b[k] or 0)
    return out


def template_view(conn, t: dict) -> dict:
    today = now().date().isoformat()
    upcoming = conn.execute("SELECT COUNT(*), MIN(date) FROM courses WHERE template_id=? AND date>=? AND status='open'",
                            (t["id"], today)).fetchone()
    teacher = one(conn.execute("SELECT id, name, photo_url FROM teachers WHERE id=?", (t["teacher_id"],)))
    return {**t, "plan_ids": json.loads(t["plan_ids"]), "beginner": bool(t["beginner"]),
            "substitute": bool(t["substitute"]), "dupr_required": bool(t["dupr_required"]),
            "dupr_verified_only": bool(t["dupr_verified_only"]), "active": bool(t["active"]),
            "teacher": teacher, "upcoming": upcoming[0], "next_date": upcoming[1]}


def get_template(conn, template_id: int) -> dict:
    t = one(conn.execute("SELECT * FROM course_templates WHERE id=?", (template_id,)))
    if not t:
        fail(404, "找不到課程範本")
    return t


@app.get("/api/admin/templates")
def list_templates(owner=Depends(require_owner)):
    with db() as conn:
        return [template_view(conn, t) for t in rows(conn.execute(
            "SELECT * FROM course_templates ORDER BY active DESC, sort, id"))]


@app.get("/api/admin/templates/{template_id}")
def template_detail(template_id: int, owner=Depends(require_owner)):
    with db() as conn:
        return template_view(conn, get_template(conn, template_id))


@app.post("/api/admin/templates")
def create_template(body: dict = Depends(json_body), owner=Depends(require_owner)):
    data = clean_template(body)
    if not data.get("name"):
        fail(400, "請填寫課程名稱")
    data["created_at"] = stamp()
    with db() as conn:
        cur = conn.execute(f"INSERT INTO course_templates ({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                           tuple(data.values()))
        return {"id": cur.lastrowid}


@app.put("/api/admin/templates/{template_id}")
def update_template(template_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """更新範本；apply_future=true 時同步更新這個範本之後尚未開始的課程。"""
    b = body
    data = clean_template(b)
    with db() as conn:
        get_template(conn, template_id)
        if data:
            conn.execute(f"UPDATE course_templates SET {','.join(k + '=?' for k in data)} WHERE id=?",
                         (*data.values(), template_id))
        updated = 0
        if b.get("apply_future"):
            sync = {k: v for k, v in data.items() if k in SYNC_FIELDS}
            t = now()
            for c in rows(conn.execute("SELECT * FROM courses WHERE template_id=? AND date>=? AND status='open'",
                                       (template_id, t.date().isoformat()))):
                if course_start(c) <= t:
                    continue
                row = dict(sync)
                if "capacity" in row:
                    row["capacity"] = max(row["capacity"], course_counts(conn, c["id"])[0])
                if row:
                    conn.execute(f"UPDATE courses SET {','.join(k + '=?' for k in row)} WHERE id=?",
                                 (*row.values(), c["id"]))
                promote_waitlist(conn, get_course(conn, c["id"]))
                updated += 1
        return {"ok": True, "updated": updated}


@app.post("/api/admin/templates/{template_id}/schedule")
def schedule_template(template_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """依範本在期間內的指定星期幾排課；同一天同時段已有這個範本的課就略過。"""
    b = body
    try:
        start, end = date.fromisoformat(b["from"]), date.fromisoformat(b["to"])
    except (KeyError, ValueError):
        fail(400, "請選擇開始與結束日期")
    weekdays = {int(x) for x in b.get("weekdays", [])}
    if not weekdays:
        fail(400, "請至少選一個星期")
    if end < start or (end - start).days > 366:
        fail(400, "日期範圍不正確（最多一年）")
    with db() as conn:
        t = get_template(conn, template_id)
        start_time = b.get("start_time") or t["start_time"]
        end_time = b.get("end_time") or t["end_time"]
        if end_time <= start_time:
            fail(400, "結束時間需晚於開始時間")
        base = {k: t[k] for k in SYNC_FIELDS}
        created, skipped, d = [], 0, start
        while d <= end:
            if d.weekday() in weekdays:
                if one(conn.execute("SELECT id FROM courses WHERE template_id=? AND date=? AND start_time=?",
                                    (template_id, d.isoformat(), start_time))):
                    skipped += 1
                else:
                    row = {**base, "date": d.isoformat(), "start_time": start_time, "end_time": end_time,
                           "template_id": template_id, "created_at": stamp(), "share_code": new_share_code(conn)}
                    cur = conn.execute(f"INSERT INTO courses ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
                                       tuple(row.values()))
                    created.append(cur.lastrowid)
                    if len(created) > 300:
                        fail(400, "一次最多排 300 堂課")
            d += timedelta(days=1)
        return {"created": len(created), "skipped": skipped}


@app.delete("/api/admin/templates/{template_id}")
def delete_template(template_id: int, owner=Depends(require_owner)):
    """刪除範本；已排的課程保留，只是不再連結範本。"""
    with db() as conn:
        get_template(conn, template_id)
        conn.execute("UPDATE courses SET template_id=NULL WHERE template_id=?", (template_id,))
        conn.execute("DELETE FROM course_templates WHERE id=?", (template_id,))
        return {"ok": True}


# ---------------------------------------------------------------- 時段預約（場主先設定日期、時段與名額，學員選時段預約）
# 每個時段就是一筆 courses（slot_set_id 指回活動），報名、候補、課卡、報名費、付款審核、提醒、名單、報表都共用原本的流程。

SLOT_FIELDS = ("name", "category", "teacher_id", "description", "location", "cover_url", "capacity", "cost", "fee",
               "pay_hours", "plan_ids", "booking_deadline_min", "cancel_deadline_min", "listed", "show_attendees", "branch_id")
# 修改活動時同步到尚未開始的時段（名額另外處理，不會少於已報名人數）
SLOT_SYNC = tuple(k for k in SLOT_FIELDS if k != "capacity")


def clean_slot_set(b: dict) -> dict:
    out = {k: v for k, v in clean_course(b).items() if k in SLOT_FIELDS}
    if "capacity" in out:
        out["capacity"] = max(out["capacity"], 1)
    return out


def get_slot_set(conn, set_id: int) -> dict:
    ss = one(conn.execute("SELECT * FROM slot_sets WHERE id=?", (set_id,)))
    if not ss:
        fail(404, "找不到這個時段預約活動")
    return ss


def slot_times(b: dict) -> list[tuple[str, str, str]]:
    """依日期區間、星期、營業時間與每段長度產生 (日期, 開始, 結束)。"""
    try:
        d1 = date.fromisoformat(str(b.get("from") or ""))
        d2 = date.fromisoformat(str(b.get("to") or b.get("from") or ""))
    except ValueError:
        fail(400, "請選擇開始與結束日期")
    if d2 < d1:
        fail(400, "結束日期不能早於開始日期")
    if (d2 - d1).days > 180:
        fail(400, "一次最多設定 180 天")
    days = {int(x) for x in (b.get("weekdays") or range(7)) if str(x).isdigit() and 0 <= int(x) <= 6}
    if not days:
        fail(400, "請至少選一個星期")
    open_t, close_t = str(b.get("open") or ""), str(b.get("close") or "")
    if not TIME_RE.match(open_t) or not TIME_RE.match(close_t):
        fail(400, "時間格式不正確（例如 09:00）")
    minutes = int(b.get("minutes") or 60)
    if not 15 <= minutes <= 480:
        fail(400, "每個時段需在 15 分鐘到 8 小時之間")
    to_min = lambda t: int(t[:2]) * 60 + int(t[3:])  # noqa: E731
    start, end = to_min(open_t), to_min(close_t)
    if end - start < minutes:
        fail(400, "結束時間要比開始時間晚至少一個時段")
    fmt = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # noqa: E731
    out = []
    d = d1
    while d <= d2:
        if d.weekday() in days:
            m = start
            while m + minutes <= end:
                out.append((d.isoformat(), fmt(m), fmt(m + minutes)))
                m += minutes
        d += timedelta(days=1)
    if not out:
        fail(400, "這個設定產生不出任何時段，請檢查日期與星期")
    if len(out) > 1500:
        fail(400, f"一次會產生 {len(out)} 個時段，太多了，請縮短日期區間（最多 1500 個）")
    return out


def add_slots(conn, ss: dict, times: list[tuple[str, str, str]], capacity: int | None = None) -> int:
    have = {(r["date"], r["start_time"]) for r in conn.execute(
        "SELECT date, start_time FROM courses WHERE slot_set_id=?", (ss["id"],))}
    n = 0
    for day, st, et in times:
        if (day, st) in have:
            continue
        row = {**{k: ss[k] for k in SLOT_FIELDS}, "capacity": capacity or ss["capacity"], "slot_set_id": ss["id"],
               "date": day, "start_time": st, "end_time": et, "share_code": new_share_code(conn), "created_at": stamp()}
        conn.execute(f"INSERT INTO courses ({','.join(row)}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
        n += 1
    return n


def slot_row(conn, c: dict, user: dict | None, s: dict) -> dict:
    v = course_view(conn, c, user, s)
    mine = v["my_reservation"]
    return {k: v[k] for k in ("id", "date", "weekday", "start_time", "end_time", "capacity", "booked_count", "waitlist_count",
                              "remain", "state", "button", "share_code", "status")} | {
        "mine": {k: mine[k] for k in ("status", "fee", "paid", "pay_note")} if mine else None}


def slot_set_base(conn, ss: dict) -> dict:
    teacher = one(conn.execute("SELECT id, name, photo_url, title FROM teachers WHERE id=?", (ss["teacher_id"],)))
    return {**{k: ss[k] for k in ("id", "name", "category", "description", "location", "cover_url", "capacity", "cost", "fee",
                                  "pay_hours", "booking_deadline_min", "cancel_deadline_min", "share_code")},
            "kind": "slots", "listed": bool(ss["listed"]), "show_attendees": bool(ss["show_attendees"]), "branch_id": ss["branch_id"], "teacher": teacher, "plan_ids": json.loads(ss["plan_ids"])}


def slot_day_summary(conn, ss: dict, day: str, user: dict | None, s: dict) -> dict:
    """課表上的一張卡：這天共有幾個時段、還剩多少名額。"""
    slots = [slot_row(conn, c, user, s) for c in rows(conn.execute(
        "SELECT * FROM courses WHERE slot_set_id=? AND date=? AND status='open' ORDER BY start_time", (ss["id"], day)))]
    open_slots = [x for x in slots if x["state"] in ("book", "waitlist")]
    return {**slot_set_base(conn, ss), "date": day, "slot_count": len(slots), "open_count": sum(x["state"] == "book" for x in slots),
            "start_time": slots[0]["start_time"] if slots else "", "end_time": slots[-1]["end_time"] if slots else "",
            "mine_count": sum(1 for x in slots if x["mine"]), "bookable": bool(open_slots)}


def slot_set_view(conn, ss: dict, user: dict | None) -> dict:
    s = get_settings(conn)
    today = now().date().isoformat()
    cs = rows(conn.execute("SELECT * FROM courses WHERE slot_set_id=? AND date>=? ORDER BY date, start_time", (ss["id"], today)))
    days: dict[str, dict] = {}
    for c in cs:
        if c["status"] != "open":
            continue
        r = slot_row(conn, c, user, s)
        days.setdefault(c["date"], {"date": c["date"], "weekday": r["weekday"], "slots": []})["slots"].append(r)
    mine = []
    if user:
        mine = rows(conn.execute(
            "SELECT r.status, r.fee, r.paid, r.pay_note, r.pay_due, c.id course_id, c.date, c.start_time, c.end_time, c.share_code"
            " FROM reservations r JOIN courses c ON c.id=r.course_id WHERE c.slot_set_id=? AND r.user_id=?"
            " AND r.status IN ('booked','waitlist') AND c.date>=? ORDER BY c.date, c.start_time", (ss["id"], user["id"], today)))
    first = next((c for c in cs if c["status"] == "open"), None)
    return {**slot_set_base(conn, ss), "days": list(days.values()), "mine": mine,
            "cards": eligible_cards(conn, user["id"], first) if user and first and ss["cost"] else []}


@app.get("/api/slots/{set_id}")
def slot_set_detail(set_id: int, user=Depends(current_user)):
    with db() as conn:
        ss = get_slot_set(conn, set_id)
        mine = user and one(conn.execute("SELECT r.id FROM reservations r JOIN courses c ON c.id=r.course_id"
                                         " WHERE c.slot_set_id=? AND r.user_id=? LIMIT 1", (set_id, user["id"])))
        if not ss["listed"] and not mine and not (user and user["role"] == "owner"):
            fail(404, "找不到這個時段預約活動")
        return slot_set_view(conn, ss, user)


def slot_admin_summary(conn, ss: dict) -> dict:
    today = now().date().isoformat()
    r = conn.execute(
        "SELECT COUNT(*), MIN(date), MAX(date), COALESCE(SUM(capacity),0) FROM courses WHERE slot_set_id=? AND date>=? AND status='open'",
        (ss["id"], today)).fetchone()
    booked = conn.execute(
        "SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id WHERE c.slot_set_id=? AND c.date>=?"
        " AND r.status='booked'", (ss["id"], today)).fetchone()[0]
    unpaid = conn.execute(
        "SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id WHERE c.slot_set_id=? AND r.fee>0 AND r.paid=0"
        " AND r.status IN ('booked','attended','absent') AND c.status='open'", (ss["id"],)).fetchone()[0]
    return {**slot_set_base(conn, ss), "slot_count": r[0], "first_date": r[1], "last_date": r[2], "total_capacity": r[3],
            "booked": booked, "unpaid": unpaid}


@app.get("/api/admin/slot-sets")
def admin_slot_sets(owner=Depends(require_owner)):
    with db() as conn:
        return [slot_admin_summary(conn, ss) for ss in rows(conn.execute("SELECT * FROM slot_sets ORDER BY id DESC"))]


@app.get("/api/admin/slot-sets/{set_id}")
def admin_slot_set(set_id: int, request: Request, owner=Depends(require_owner)):
    since = request.query_params.get("from") or now().date().isoformat()
    with db() as conn:
        ss = get_slot_set(conn, set_id)
        s = get_settings(conn)
        days: dict[str, dict] = {}
        for c in rows(conn.execute("SELECT * FROM courses WHERE slot_set_id=? AND date>=? ORDER BY date, start_time", (set_id, since))):
            v = course_view(conn, c, None, s)
            unpaid = conn.execute("SELECT COUNT(*) FROM reservations WHERE course_id=? AND fee>0 AND paid=0"
                                  " AND status IN ('booked','attended','absent')", (c["id"],)).fetchone()[0]
            days.setdefault(c["date"], {"date": c["date"], "weekday": v["weekday"], "slots": []})["slots"].append(
                {k: v[k] for k in ("id", "start_time", "end_time", "capacity", "booked_count", "waitlist_count", "status", "state")}
                | {"unpaid": unpaid})
        return {**slot_admin_summary(conn, ss), "days": list(days.values())}


@app.post("/api/admin/slot-sets")
def create_slot_set(body: dict = Depends(json_body), owner=Depends(require_owner)):
    data = clean_slot_set(body)
    if not data.get("name"):
        fail(400, "請填寫活動名稱")
    times = slot_times(body)
    with db() as conn:
        row = {**{k: DEFAULT_SLOT[k] for k in DEFAULT_SLOT}, **data, "share_code": new_share_code(conn), "created_at": stamp()}
        set_id = conn.execute(f"INSERT INTO slot_sets ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
                              tuple(row.values())).lastrowid
        if body.get("share_code"):
            set_share_code(conn, "slots", get_slot_set(conn, set_id), body["share_code"])
        n = add_slots(conn, get_slot_set(conn, set_id), times)
        return {"id": set_id, "created": n}


DEFAULT_SLOT = {"branch_id": None, "category": "", "teacher_id": None, "description": "", "location": "", "cover_url": "", "capacity": 1,
                "cost": 0, "fee": 0, "pay_hours": 48, "plan_ids": "[]", "booking_deadline_min": 60,
                "cancel_deadline_min": 1440, "listed": 1, "show_attendees": 0}


@app.post("/api/admin/slot-sets/{set_id}/slots")
def add_slot_times(set_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    times = slot_times(body)
    cap = max(int(body.get("capacity") or 0), 0) or None
    with db() as conn:
        ss = get_slot_set(conn, set_id)
        return {"created": add_slots(conn, ss, times, cap)}


@app.put("/api/admin/slot-sets/{set_id}")
def update_slot_set(set_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    data = clean_slot_set(body)
    with db() as conn:
        ss0 = get_slot_set(conn, set_id)
        if body.get("share_code") not in (None, ""):
            set_share_code(conn, "slots", ss0, body["share_code"])
        if data:
            conn.execute(f"UPDATE slot_sets SET {','.join(k + '=?' for k in data)} WHERE id=?", (*data.values(), set_id))
        ss = get_slot_set(conn, set_id)
        sync = {k: ss[k] for k in SLOT_SYNC if k in data}
        updated = 0
        for c in rows(conn.execute("SELECT * FROM courses WHERE slot_set_id=? AND date>=?", (set_id, now().date().isoformat()))):
            if now() >= course_start(c):
                continue
            fields = dict(sync)
            if "capacity" in data:
                fields["capacity"] = max(ss["capacity"], course_counts(conn, c["id"])[0])
            if fields:
                conn.execute(f"UPDATE courses SET {','.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), c["id"]))
                updated += 1
                promote_waitlist(conn, get_course(conn, c["id"]))
        return {"ok": True, "updated": updated}


@app.delete("/api/admin/slot-sets/{set_id}")
def delete_slot_set(set_id: int, owner=Depends(require_owner)):
    with db() as conn:
        get_slot_set(conn, set_id)
        n = conn.execute("SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id WHERE c.slot_set_id=?"
                         " AND r.status!='cancelled'", (set_id,)).fetchone()[0]
        if n:
            fail(400, f"已有 {n} 筆預約，無法刪除整個活動；可以取消勾選「公開在課表」，或逐一停掉時段")
        ids = [r[0] for r in conn.execute("SELECT id FROM courses WHERE slot_set_id=?", (set_id,))]
        conn.executemany("DELETE FROM reservations WHERE course_id=?", [(i,) for i in ids])
        conn.execute("DELETE FROM courses WHERE slot_set_id=?", (set_id,))
        conn.execute("DELETE FROM slot_sets WHERE id=?", (set_id,))
        return {"ok": True}


@app.put("/api/admin/courses/{course_id}")
def update_course(course_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    data = clean_course(body)
    with db() as conn:
        c = get_course(conn, course_id)
        if body.get("share_code") not in (None, ""):
            set_share_code(conn, "course", c, body["share_code"])
        if data:
            conn.execute(f"UPDATE courses SET {','.join(k + '=?' for k in data)} WHERE id=?",
                         (*data.values(), course_id))
        c = get_course(conn, course_id)
        promote_waitlist(conn, c)
        return {"ok": True}


@app.post("/api/admin/courses/{course_id}/status")
def course_status(course_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """停課時退還所有人的課卡並通知。"""
    status = body.get("status")
    if status not in ("open", "cancelled"):
        fail(400, "狀態錯誤")
    with db() as conn:
        c = get_course(conn, course_id)
        conn.execute("UPDATE courses SET status=? WHERE id=?", (status, course_id))
        if status == "cancelled":
            for r in rows(conn.execute("SELECT * FROM reservations WHERE course_id=? AND status IN ('booked','waitlist')",
                                       (course_id,))):
                refund(conn, r)
                conn.execute("UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?", (stamp(), r["id"]))
                notify(conn, r["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 已停課。"
                                           + (f"已付的報名費 NT$ {r['fee']:,} 將由主辦與您聯繫退費。" if r["paid"] else "課卡已退還。" if r["charged"] else ""),
                       course=c)
        return {"ok": True}


@app.delete("/api/admin/courses/{course_id}")
def delete_course(course_id: int, owner=Depends(require_owner)):
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM reservations WHERE course_id=? AND status!='cancelled'",
                         (course_id,)).fetchone()[0]
        if n:
            fail(400, "這堂課已有人預約，請改用「停課」以退還課卡")
        conn.execute("DELETE FROM reservations WHERE course_id=?", (course_id,))
        conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
        return {"ok": True}


@app.get("/api/admin/notifications")
def admin_notifications(owner=Depends(require_owner)):
    with db() as conn:
        items = rows(conn.execute("SELECT * FROM admin_notifications ORDER BY id DESC LIMIT 100"))
        for n in items:
            n["read"] = n["id"] <= owner["admin_seen_id"]
        if items:
            conn.execute("UPDATE users SET admin_seen_id=? WHERE id=?", (items[0]["id"], owner["id"]))
        return items


def with_noshow(conn, roster: list[dict], s: dict | None = None) -> list[dict]:
    """名單上附每個人目前計入的缺席次數與是否暫停報名。"""
    s = s or get_settings(conn)
    for r in roster:
        ns = noshow_status(conn, {"id": r["user_id"], "blocked_until": r["blocked_until"], "block_reason": ""}, s)
        r["noshow"] = {"count": ns["count"], "limit": ns["limit"], "blocked": ns["blocked"], "enabled": ns["enabled"]}
    return roster


def roster_rows(conn, course_id: int) -> list[dict]:
    return rows(conn.execute(
        "SELECT r.*, u.name, u.phone, u.dupr_id, u.dupr_doubles, u.dupr_singles, u.dupr_verified, u.blocked_until,"
        " cd.name card_name FROM reservations r JOIN users u ON u.id=r.user_id"
        " LEFT JOIN cards cd ON cd.id=r.card_id WHERE r.course_id=? AND r.status!='cancelled' ORDER BY r.id",
        (course_id,)))


@app.get("/api/admin/attendance")
def attendance(request: Request, owner=Depends(require_staff)):
    """某一天所有課程與名單，集中點名用（教練只看到自己的課）。"""
    day = request.query_params.get("date") or now().date().isoformat()
    mine = owner["teacher_id"] if owner["role"] == "coach" else None
    with db() as conn:
        s = get_settings(conn)
        out = []
        for c in rows(conn.execute("SELECT * FROM courses WHERE date=? AND status='open' AND (? IS NULL OR teacher_id=?) ORDER BY start_time, id",
                                   (day, mine, mine))):
            v = course_view(conn, c, None, s)
            v["roster"] = with_noshow(conn, [r for r in roster_rows(conn, c["id"]) if r["status"] != "waitlist"], s)
            v["started"] = now() >= course_start(c)
            out.append(v)
        return out


@app.post("/api/admin/courses/{course_id}/attendance")
def mark_all(course_id: int, owner=Depends(require_staff)):
    """把尚未點名的學員全部標記為出席。"""
    with db() as conn:
        c = get_course(conn, course_id)
        coach_course(owner, c)
        if now().date().isoformat() < c["date"]:
            fail(400, "開課當天才能點名")
        n = conn.execute("UPDATE reservations SET status='attended', updated_at=? WHERE course_id=? AND status='booked'",
                         (stamp(), course_id)).rowcount
        return {"updated": n}


@app.get("/api/admin/attendance/stats")
def attendance_stats(request: Request, owner=Depends(require_owner)):
    """期間內每位學員的預約、出席、缺席、未點名統計（只算已開始的課）。"""
    end = request.query_params.get("to") or now().date().isoformat()
    start = request.query_params.get("from") or (date.fromisoformat(end) - timedelta(days=29)).isoformat()
    with db() as conn:
        items = rows(conn.execute(
            "SELECT u.id, u.name, u.phone,"
            " SUM(r.status IN ('booked','attended','absent')) total,"
            " SUM(r.status='attended') attended, SUM(r.status='absent') absent, SUM(r.status='booked') unmarked"
            " FROM reservations r JOIN users u ON u.id=r.user_id JOIN courses c ON c.id=r.course_id"
            " WHERE c.date BETWEEN ? AND ? AND c.status='open' AND (c.date || 'T' || c.start_time) <= ?"
            " GROUP BY u.id HAVING total > 0 ORDER BY absent DESC, total DESC",
            (start, end, now().isoformat(timespec="minutes"))))
        for i in items:
            marked = i["attended"] + i["absent"]
            i["rate"] = round(i["attended"] / marked * 100) if marked else None
        return {"from": start, "to": end, "members": items}


@app.get("/api/admin/courses/{course_id}/roster")
def roster(course_id: int, owner=Depends(require_staff)):
    with db() as conn:
        c = get_course(conn, course_id)
        coach_course(owner, c)
        v = course_view(conn, c, None, get_settings(conn))
        v["roster"] = with_noshow(conn, roster_rows(conn, course_id))
        return v


@app.post("/api/admin/reservations/{res_id}")
def update_reservation(res_id: int, body: dict = Depends(json_body), owner=Depends(require_staff)):
    """點名（attended/absent/booked）或場主取消（cancelled，退卡）；教練只能點自己課的名。"""
    b = body
    status = b.get("status")
    if status not in ("attended", "absent", "booked", "cancelled"):
        fail(400, "狀態錯誤")
    with db() as conn:
        r = one(conn.execute("SELECT * FROM reservations WHERE id=?", (res_id,)))
        if not r:
            fail(404, "找不到預約")
        c = get_course(conn, r["course_id"])
        coach_course(owner, c)
        if owner["role"] == "coach" and (status == "cancelled" or r["status"] == "waitlist"):
            fail(403, "教練只能點名，取消或候補請找場主")
        if r["status"] == "cancelled":
            fail(400, "這筆預約已取消；要恢復請用「代為預約」重新加入（會重新扣卡）")
        if status == "cancelled" and r["status"] != "waitlist" and has_event(conn, c["id"]):
            fail(400, "這場已生成賽事，請先到「賽事」刪除賽事再取消預約")
        if r["status"] == "waitlist" and status == "booked":
            card_id, charged = charge(conn, r["user_id"], c, None)
            conn.execute("UPDATE reservations SET card_id=?, charged=?, pay_due=? WHERE id=?", (card_id, charged, pay_due(c), res_id))
            notify(conn, r["user_id"], f"場館已將您從候補改為正式預約：「{c['name']}」{c['date']} {c['start_time']}。")
        conn.execute("UPDATE reservations SET status=?, updated_at=? WHERE id=?", (status, stamp(), res_id))
        if status == "cancelled":
            if b.get("refund", True):
                refund(conn, r)
            notify(conn, r["user_id"], f"場館已取消您的預約：「{c['name']}」{c['date']} {c['start_time']}。")
            if r["status"] == "booked":
                promote_waitlist(conn, c)
        ns = None
        if status == "absent" and r["status"] != "absent":
            conn.execute("UPDATE reservations SET noshow_cleared=0 WHERE id=?", (res_id,))
            ns = check_noshow(conn, r["user_id"], c)
        return {"ok": True, "noshow": ns}


@app.post("/api/admin/courses/{course_id}/add")
def add_to_course(course_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """場主替會員加入課程（現場報名），可選擇是否扣卡。沒有帳號的人可以只填姓名（guest_name），系統建一筆臨時名單。"""
    b = body
    with db() as conn:
        c = get_course(conn, course_id)
        guest = str(b.get("guest_name", "")).strip()[:40]
        if guest:
            phone = clean_phone(b.get("guest_phone"))
            u = one(conn.execute("SELECT * FROM users WHERE phone=? AND deleted=0", (phone,))) if phone else None
            if not u:
                u = create_user(conn, guest, phone=phone, note="現場名單（沒有帳號）")
            b = {**b, "charge": False}
        else:
            u = one(conn.execute("SELECT * FROM users WHERE id=? AND deleted=0", (int(b.get("user_id", 0)),)))
        if not u:
            fail(404, "找不到會員")
        if one(conn.execute("SELECT id FROM reservations WHERE course_id=? AND user_id=? AND status!='cancelled'",
                            (course_id, u["id"]))):
            fail(400, "此會員已在名單中")
        card_id, charged = charge(conn, u["id"], c, None) if b.get("charge", True) else (None, 0)
        paid = 1 if c["fee"] and b.get("paid") else 0
        conn.execute("INSERT INTO reservations (course_id, user_id, status, card_id, charged, fee, paid, paid_at, created_at, updated_at)"
                     " VALUES (?,?,?,?,?,?,?,?,?,?)", (course_id, u["id"], "booked", card_id, charged, c["fee"], paid,
                                                      stamp() if paid else "", stamp(), stamp()))
        notify(conn, u["id"], f"主辦已為您報名「{c['name']}」{c['date']} {c['start_time']}。", course=c)
        return {"ok": True, "user_id": u["id"]}


def crud(table: str, fields: tuple, ints: tuple = ()):
    def clean(b: dict) -> dict:
        out = {k: b[k] for k in fields if k in b}
        for k in ints:
            if k in out:
                out[k] = int(out[k] or 0)
        return out

    @app.get(f"/api/admin/{table}", name=f"list_{table}")
    def list_(owner=Depends(require_owner)):
        with db() as conn:
            return rows(conn.execute(f"SELECT * FROM {table} ORDER BY sort, id"))

    @app.post(f"/api/admin/{table}", name=f"create_{table}")
    def create(body: dict = Depends(json_body), owner=Depends(require_owner)):
        data = clean(body)
        if not data.get("name"):
            fail(400, "請填寫名稱")
        with db() as conn:
            cur = conn.execute(f"INSERT INTO {table} ({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                               tuple(data.values()))
            return {"id": cur.lastrowid}

    @app.put(f"/api/admin/{table}/{{item_id}}", name=f"update_{table}")
    def update(item_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
        data = clean(body)
        with db() as conn:
            if data:
                conn.execute(f"UPDATE {table} SET {','.join(k + '=?' for k in data)} WHERE id=?",
                             (*data.values(), item_id))
            return {"ok": True}


crud("teachers", ("name", "title", "bio", "photo_url", "active", "sort", "hourly_rate"), ("active", "sort", "hourly_rate"))
crud("branches", ("name", "address", "active", "sort"), ("active", "sort"))


@app.get("/api/admin/coach-hours")
def coach_hours(request: Request, user=Depends(require_staff)):
    """教練時數與鐘點費：期間內每位老師已開始、未停課的課（堂數、時數、出席人次、鐘點費）。教練只看自己。"""
    saas.need("staff")
    end = request.query_params.get("to") or now().date().isoformat()
    start = request.query_params.get("from") or end[:8] + "01"
    mine = user["teacher_id"] if user["role"] == "coach" else None
    with db() as conn:
        out = []
        for t in rows(conn.execute("SELECT * FROM teachers WHERE (? IS NULL OR id=?) ORDER BY sort, id", (mine, mine))):
            cs = rows(conn.execute("SELECT * FROM courses WHERE teacher_id=? AND status='open' AND date BETWEEN ? AND ?"
                                   " AND (date || 'T' || start_time) <= ? ORDER BY date, start_time",
                                   (t["id"], start, end, now().isoformat(timespec="minutes"))))
            minutes = sum(reports._minutes(c) for c in cs)
            attended = sum(conn.execute("SELECT COUNT(*) FROM reservations WHERE course_id=? AND status='attended'", (c["id"],)).fetchone()[0] for c in cs)
            if not cs and mine is None and not t["active"]:
                continue
            out.append({"teacher_id": t["id"], "name": t["name"], "sessions": len(cs), "hours": round(minutes / 60, 1), "attended": attended,
                        "rate": t["hourly_rate"], "amount": round(minutes / 60 * t["hourly_rate"]),
                        "courses": [{"id": c["id"], "date": c["date"], "start_time": c["start_time"], "end_time": c["end_time"], "name": c["name"]} for c in cs]})
        return {"from": start, "to": end, "teachers": out}


@app.get("/api/branches")
def public_branches():
    """分館（多館管理）：前台課表依分館篩選。"""
    with db() as conn:
        return rows(conn.execute("SELECT id, name, address FROM branches WHERE active=1 ORDER BY sort, id"))
crud("plans", ("name", "type", "quantity", "valid_days", "price", "description", "active", "sort"),
     ("quantity", "valid_days", "price", "active", "sort"))


def grant_card(conn, user_id: int, plan: dict, source: str) -> int:
    today = now().date()
    cur = conn.execute(
        "INSERT INTO cards (user_id, plan_id, name, type, total, remaining, starts_on, expires_on, source, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, plan["id"], plan["name"], plan["type"], plan["quantity"], plan["quantity"], today.isoformat(),
         (today + timedelta(days=max(plan["valid_days"], 1) - 1)).isoformat(), source, stamp()))
    notify(conn, user_id, f"課卡「{plan['name']}」已開通，可以開始預約課程了！")
    return cur.lastrowid


@app.get("/api/admin/reports")
def report(request: Request, owner=Depends(require_owner)):
    try:
        start, end = reports.parse_range(request.query_params, now().date())
    except ValueError as e:
        fail(400, str(e))
    with db() as conn:
        return reports.public(reports.summary(conn, start, end, now().date().isoformat()))


@app.get("/api/admin/reports/export")
def report_export(request: Request, owner=Depends(require_owner)):
    try:
        start, end = reports.parse_range(request.query_params, now().date())
    except ValueError as e:
        fail(400, str(e))
    with db() as conn:
        data = reports.summary(conn, start, end, now().date().isoformat())
        content = reports.to_xlsx(data, get_settings(conn)["name"])
    name = f"report-{start}-{end}.xlsx"
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/admin/orders")
def admin_orders(owner=Depends(require_owner)):
    with db() as conn:
        return rows(conn.execute(
            "SELECT o.*, p.name plan_name, u.name user_name, u.phone FROM orders o JOIN plans p ON p.id=o.plan_id"
            " JOIN users u ON u.id=o.user_id ORDER BY o.status='pending' DESC, o.id DESC LIMIT 300"))


@app.post("/api/admin/orders/{order_id}")
def update_order(order_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    status = body.get("status")
    if status not in ("paid", "cancelled"):
        fail(400, "狀態錯誤")
    with db() as conn:
        o = one(conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)))
        if not o or o["status"] != "pending":
            fail(400, "此訂單已處理")
        conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, stamp(), order_id))
        if status == "paid":
            plan = one(conn.execute("SELECT * FROM plans WHERE id=?", (o["plan_id"],)))
            grant_card(conn, o["user_id"], plan, "order")
        else:
            notify(conn, o["user_id"], "您的課卡購買申請已被取消，如有疑問請聯絡場館。")
        return {"ok": True}


@app.get("/api/admin/members")
def members(owner=Depends(require_owner)):
    with db() as conn:
        today = now().date().isoformat()
        s = get_settings(conn)
        out = []
        for u in rows(conn.execute("SELECT * FROM users WHERE deleted=0 ORDER BY role='owner' DESC, id DESC")):
            m = public_user(u)
            m["note"] = u["note"]
            m["cards"] = rows(conn.execute(
                "SELECT * FROM cards WHERE user_id=? AND expires_on>=? ORDER BY expires_on", (u["id"], today)))
            m["bookings"] = conn.execute(
                "SELECT COUNT(*) FROM reservations WHERE user_id=? AND status IN ('booked','attended')",
                (u["id"],)).fetchone()[0]
            m["absences"] = conn.execute(
                "SELECT COUNT(*) FROM reservations WHERE user_id=? AND status='absent'", (u["id"],)).fetchone()[0]
            m["noshow"] = noshow_status(conn, u, s)
            out.append(m)
        return out


@app.get("/api/admin/members/{user_id}/absences")
def member_absences(user_id: int, owner=Depends(require_owner)):
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not u:
            fail(404, "找不到會員")
        return {"status": noshow_status(conn, u), "absences": noshow_list(conn, user_id)}


@app.post("/api/admin/reservations/{res_id}/excuse")
def excuse_absence(res_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    """缺席免記（例如生病有先講）；取消免記會重新計入。"""
    with db() as conn:
        r = one(conn.execute("SELECT * FROM reservations WHERE id=? AND status='absent'", (res_id,)))
        if not r:
            fail(404, "找不到這筆缺席紀錄")
        if r["noshow_cleared"] == 2:
            fail(400, "這次缺席已計入之前的暫停報名，要取消請直接解除暫停")
        conn.execute("UPDATE reservations SET noshow_cleared=? WHERE id=?", (1 if body.get("excused", True) else 0, res_id))
        ns = None if body.get("excused", True) else check_noshow(conn, r["user_id"], get_course(conn, r["course_id"]))
        return {"ok": True, "noshow": ns}


@app.put("/api/admin/members/{user_id}")
def update_member(user_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not u:
            fail(404, "找不到會員")
        if "suspended" in b:
            if u["id"] == owner["id"]:
                fail(400, "不能停權自己")
            conn.execute("UPDATE users SET suspended=?, suspend_reason=? WHERE id=?",
                         (1 if b["suspended"] else 0, str(b.get("suspend_reason", ""))[:200], user_id))
            if b["suspended"]:
                revoke_tokens(conn, user_id)
        if "dupr_verified" in b:
            conn.execute("UPDATE users SET dupr_verified=? WHERE id=?", (1 if b["dupr_verified"] else 0, user_id))
        if "dupr" in b:
            set_dupr(conn, user_id, b["dupr"], source="owner")
        if "avatar_url" in b:
            conn.execute("UPDATE users SET avatar_url=? WHERE id=?", (str(b["avatar_url"] or "")[:300], user_id))
        if "note" in b:
            conn.execute("UPDATE users SET note=? WHERE id=?", (str(b["note"])[:500], user_id))
        if b.get("unblock"):
            conn.execute("UPDATE users SET blocked_until='', block_reason='' WHERE id=?", (user_id,))
            notify(conn, user_id, "主辦已解除您的報名限制，可以正常報名了。")
        if isinstance(b.get("block"), dict):
            days = max(int(b["block"].get("days") or 0), 0)
            until = FOREVER if not days else (now().date() + timedelta(days=days - 1)).isoformat()
            reason = str(b["block"].get("reason") or "主辦暫停報名")[:100]
            conn.execute("UPDATE users SET blocked_until=?, block_reason=? WHERE id=?", (until, reason, user_id))
            ns = noshow_status(conn, {**u, "blocked_until": until, "block_reason": reason})
            notify(conn, user_id, f"主辦已暫停您的報名{block_text(ns)}（{reason}）。已報名的活動不受影響。")
        if b.get("role") in ("student", "owner", "coach") and u["id"] != owner["id"]:
            if b["role"] == "owner" and u["role"] != "owner" and not saas.has("staff") and \
                    conn.execute("SELECT COUNT(*) FROM users WHERE role='owner' AND deleted=0").fetchone()[0] >= 1:
                saas.need("staff")  # 沒有「多位管理員」的方案只能有一位場主
            teacher = None
            if b["role"] == "coach":
                saas.need("staff")
                teacher = int(b.get("teacher_id") or 0) or None
                if not teacher or not one(conn.execute("SELECT id FROM teachers WHERE id=?", (teacher,))):
                    fail(400, "請選擇這位教練對應的老師")
            conn.execute("UPDATE users SET role=?, teacher_id=? WHERE id=?", (b["role"], teacher, user_id))
            if b["role"] != "owner":
                revoke_tokens(conn, user_id)  # 權限降低：其他裝置重新登入
        return {"ok": True}


@app.delete("/api/admin/members/{user_id}")
def delete_member(user_id: int, owner=Depends(require_owner)):
    """刪除會員與其所有資料；他佔用的名額會釋出並遞補候補。"""
    if user_id == owner["id"]:
        fail(400, "不能刪除自己的帳號")
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not u:
            fail(404, "找不到會員")
        freed = [r["course_id"] for r in conn.execute(
            "SELECT course_id FROM reservations WHERE user_id=? AND status='booked'", (user_id,))]
        conn.execute("UPDATE reservations SET partner_id=NULL WHERE partner_id=?", (user_id,))
        # 未開始的預約取消（名額釋出），已上過的課與收款紀錄保留，報表才不會少
        conn.execute("UPDATE reservations SET status='cancelled', updated_at=? WHERE user_id=? AND status IN ('booked','waitlist')",
                     (stamp(), user_id))
        conn.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE user_id=? AND status='pending'", (stamp(), user_id))
        for table in ("tokens", "cards", "reviews", "notifications"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        conn.execute("UPDATE users SET name='（已刪除的會員）', phone=NULL, email=NULL, line_user_id=NULL, password_hash='',"
                     " role='student', suspended=1, note='', avatar_url='', avatar_source='', dupr_id='', dupr_name='',"
                     " dupr_doubles=NULL, dupr_singles=NULL, deleted=1 WHERE id=?", (user_id,))
        for course_id in freed:
            promote_waitlist(conn, get_course(conn, course_id))
        return {"ok": True}


@app.post("/api/admin/members/{user_id}/cards")
def give_card(user_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    with db() as conn:
        plan = one(conn.execute("SELECT * FROM plans WHERE id=?", (int(b.get("plan_id", 0)),)))
        if not plan:
            fail(404, "找不到方案")
        grant_card(conn, user_id, plan, "manual")
        return {"ok": True}


@app.put("/api/admin/cards/{card_id}")
def adjust_card(card_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    with db() as conn:
        if "remaining" in b:
            conn.execute("UPDATE cards SET remaining=? WHERE id=?", (max(int(b["remaining"]), 0), card_id))
        if b.get("expires_on"):
            conn.execute("UPDATE cards SET expires_on=? WHERE id=?", (date.fromisoformat(b["expires_on"]).isoformat(),
                                                                       card_id))
        return {"ok": True}


@app.get("/api/admin/reviews")
def admin_reviews(owner=Depends(require_owner)):
    with db() as conn:
        return rows(conn.execute(
            "SELECT r.*, u.name user_name, c.name course_name, c.date course_date, t.name teacher_name"
            " FROM reviews r JOIN users u ON u.id=r.user_id LEFT JOIN courses c ON c.id=r.course_id"
            " LEFT JOIN teachers t ON t.id=r.teacher_id ORDER BY r.id DESC LIMIT 300"))


@app.put("/api/admin/reviews/{review_id}")
def hide_review(review_id: int, body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    with db() as conn:
        conn.execute("UPDATE reviews SET hidden=? WHERE id=?", (1 if b.get("hidden") else 0, review_id))
        return {"ok": True}


@app.put("/api/admin/venue-slug")
def update_venue_slug(body: dict = Depends(json_body), owner=Depends(require_owner)):
    """改場館網址（digital-court.cc/<代碼>）。舊網址會自動轉到新網址。"""
    return saas.rename_tenant(str(body.get("slug") or ""))


@app.put("/api/admin/settings")
def update_settings(body: dict = Depends(json_body), owner=Depends(require_owner)):
    b = body
    with db() as conn:
        for k in DEFAULT_SETTINGS:
            if k in b:
                conn.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (k, json.dumps(b[k], ensure_ascii=False)))
        return get_settings(conn)


ALLOWED_IMAGES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


@app.post("/api/admin/upload")
async def upload(file: UploadFile = File(...), owner=Depends(require_owner)):
    return {"url": await save_image(file, 5)}


IMAGE_MAGIC = {".jpg": (b"\xff\xd8\xff",), ".png": (b"\x89PNG\r\n\x1a\n",), ".gif": (b"GIF87a", b"GIF89a"), ".webp": (b"RIFF",)}


async def save_image(file: UploadFile, max_mb: int) -> str:
    """分段讀取（超過上限立即停止）並檢查檔頭，確定真的是圖片才存。"""
    ext = ALLOWED_IMAGES.get(file.content_type)
    if not ext:
        fail(400, "只接受 JPG、PNG、WebP、GIF")
    limit, chunks, size = max_mb * 1024 * 1024, [], 0
    while chunk := await file.read(256 * 1024):
        size += len(chunk)
        if size > limit:
            fail(400, f"圖片需小於 {max_mb}MB")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content.startswith(IMAGE_MAGIC[ext]) or (ext == ".webp" and content[8:12] != b"WEBP"):
        fail(400, "這個檔案不是有效的圖片")
    name = uuid.uuid4().hex + ext
    (tenancy.current().upload_dir / name).write_bytes(content)
    return f"uploads/{name}"


@app.post("/api/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(require_user)):
    url = await save_image(file, 2)
    old = user["avatar_url"]
    if user["avatar_source"] == "upload" and old.startswith("uploads/"):
        (tenancy.current().upload_dir / Path(old).name).unlink(missing_ok=True)
    with db() as conn:
        conn.execute("UPDATE users SET avatar_url=?, avatar_source='upload' WHERE id=?", (url, user["id"]))
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


# ---------------------------------------------------------------- static

@app.exception_handler(HTTPException)
def http_error(_request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.get("/uploads/{name}")
def uploaded(name: str):
    path = tenancy.current().upload_dir / Path(name).name
    if not path.is_file():
        fail(404, "not found")
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=604800"})


@app.get("/e/{code}", include_in_schema=False)
def old_share_url(code: str, request: Request):
    """舊的分享網址 /e/<代碼>：永久轉到 <網站>/<目前的代碼>（改過的代碼、升級前的 8 碼都能找到）。"""
    with db() as conn:
        kind, row = find_by_code(conn, code)
    if not row:
        guard_code_guess(request, True)
        return RedirectResponse(public_base(request), status_code=302)
    return RedirectResponse(public_base(request) + row["share_code"], status_code=301)


# ---------------------------------------------------------------- 給搜尋引擎與 AI 的頁面（SEO／GEO）
# 前端是單頁 App：這裡回同一份 index.html，但先在 <head> 放好標題、描述、分享預覽與結構化資料，
# <div id="root"> 裡放活動的文字內容（不執行 JavaScript 的爬蟲也讀得到）；瀏覽器載入後 App 會接手畫面。

def iso_local(day: str, hhmm: str) -> str:
    off = datetime.now(TZ).strftime("%z")
    return f"{day}T{hhmm}:00{off[:3]}:{off[3:]}" if hhmm else day


def render_index(head: str, body: str, title: str) -> Response:
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    page = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", page, count=1, flags=re.S)
    page = page.replace("</head>", head + "</head>", 1)
    page = page.replace('<div id="root"></div>', f'<div id="root">{body}</div>', 1)
    return Response(page, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})


def head_tags(base: str, url: str, title: str, desc: str, image: str, site: str, ld: list, index: bool = True, og_type: str = "website") -> str:
    """title 給分享預覽用（LINE／FB 另外會顯示網站名稱，所以只放活動名稱）。"""
    e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
    if image and not re.match(r"^https?:", image):
        image = base + image.lstrip("/")
    index = index and not demo.is_demo()  # 示範場館的活動都是假的，不給搜尋引擎收錄
    tags = [f'<meta name="description" content="{e(desc)}">', f'<link rel="canonical" href="{e(url)}">',
            f'<meta name="robots" content="{"index,follow,max-image-preview:large" if index else "noindex,nofollow"}">']
    for k, v in (("og:type", og_type), ("og:site_name", site), ("og:title", title), ("og:description", desc), ("og:url", url),
                 ("og:image", image), ("og:locale", "zh_TW")):
        if v:
            tags.append(f'<meta property="{k}" content="{e(v)}">')
    tags.append('<meta name="twitter:card" content="summary_large_image">')
    for item in ld:
        tags.append('<script type="application/ld+json">' + json.dumps(item, ensure_ascii=False).replace("<", "\\u003c") + "</script>")
    return "".join(tags)


def share_page(code: str, request: Request):
    """活動網址 <網站>/<代碼>：LINE／FB 預覽、搜尋引擎與 AI 都讀得到活動資訊；不公開的活動不讓搜尋引擎收錄。"""
    base = public_base(request)
    with db() as conn:
        kind, row = find_by_code(conn, code)
        if not row:
            guard_code_guess(request, True)
            return RedirectResponse(base, status_code=302)
        if row["share_code"] != code.strip():  # 改過的代碼、大寫 → 轉到正式網址
            return RedirectResponse(base + row["share_code"], status_code=301)
        s = get_settings(conn)
        e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
        url = base + row["share_code"]
        org = {"@type": "Organization", "name": s["name"], "url": base}
        place = {"@type": "Place", "name": row["location"] or s["name"], "address": s["address"] or s["name"]}
        if kind == "slots":
            ss = row
            slots = rows(conn.execute("SELECT * FROM courses WHERE slot_set_id=? AND date>=? AND status='open' ORDER BY date, start_time",
                                      (ss["id"], now().date().isoformat())))
            price = f"每個時段 NT${ss['fee']:,}" if ss["fee"] else "使用課卡" if ss["cost"] else "免費"
            span = f"{slots[0]['date'][5:].replace('-', '/')}–{slots[-1]['date'][5:].replace('-', '/')}" if slots else ""
            desc = "｜".join(x for x in (f"線上選時段預約 {span}".strip(), row["location"] or s["name"], price, f"每段 {ss['capacity']} 位") if x)
            ld = [{"@context": "https://schema.org", "@type": "Service", "name": ss["name"], "description": desc, "provider": org,
                   "areaServed": place, "url": url, **({"image": base + ss["cover_url"]} if ss["cover_url"] else {})}]
            days = {}
            for c in slots[:300]:
                days.setdefault(c["date"], []).append(c)
            items = "".join(f"<li>{e(d[5:].replace('-', '/'))}（{WEEKDAYS[date.fromisoformat(d).weekday()]}）："
                            + "、".join(f"{x['start_time']}–{x['end_time']}" for x in cs) + "</li>" for d, cs in list(days.items())[:14])
            body = (f'<main class="seo"><p><a href="{e(base)}">{e(s["name"])}</a></p><h1>{e(ss["name"])}</h1><p>{e(desc)}</p>'
                    + (f'<p>{e(ss["description"])}</p>' if ss["description"] else "")
                    + f'<h2>可預約的時段</h2><ul>{items}</ul><p><a href="{e(url)}">線上選時段預約</a></p></main>')
            return render_index(head_tags(base, url, ss["name"], desc, ss["cover_url"] or s["cover_url"], s["name"], ld, bool(ss["listed"])),
                                body, f"{ss['name']}｜{s['name']}")
        c = row
        booked, _ = course_counts(conn, c["id"])
        teacher = one(conn.execute("SELECT name FROM teachers WHERE id=?", (c["teacher_id"],)))
    d = date.fromisoformat(c["date"])
    when = f"{d.year}/{d.month}/{d.day}（{WEEKDAYS[d.weekday()]}）{c['start_time']}–{c['end_time']}"
    price = f"報名費 NT${c['fee']:,}" if c["fee"] else "使用課卡" if c["cost"] else "免費"
    parts = [when, c["location"] or s["name"], price]
    dupr = ""
    if c["dupr_required"]:
        lo, hi = c["dupr_min"], c["dupr_max"]
        dupr = "DUPR " + (f"{lo:.1f}–{hi:.1f}" if lo is not None and hi is not None else f"{lo:.1f}+" if lo is not None else f"≤{hi:.1f}" if hi is not None else "不限分數")
        parts.append(dupr)
    if c["status"] == "cancelled":
        parts.append("已停課")
    elif s["show_reservation_count"]:
        parts.append(f"已報名 {booked}/{c['capacity']}")
    desc = "｜".join(parts)
    remain = max(c["capacity"] - booked, 0)
    ev = {"@context": "https://schema.org", "@type": "SportsEvent", "name": c["name"], "sport": "Pickleball", "url": url,
          "startDate": iso_local(c["date"], c["start_time"]), "endDate": iso_local(c["date"], c["end_time"]),
          "eventStatus": "https://schema.org/EventCancelled" if c["status"] == "cancelled" else "https://schema.org/EventScheduled",
          "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "location": place, "organizer": org,
          "description": (c["description"] or desc)[:500], "maximumAttendeeCapacity": c["capacity"], "remainingAttendeeCapacity": remain}
    if c["cover_url"] or s["cover_url"]:
        ev["image"] = [base + (c["cover_url"] or s["cover_url"]).lstrip("/")]
    if c["fee"] or not c["cost"]:
        ev["offers"] = {"@type": "Offer", "price": c["fee"], "priceCurrency": "TWD", "url": url,
                        "availability": "https://schema.org/InStock" if remain > 0 else "https://schema.org/SoldOut"}
    if teacher:
        ev["performer"] = {"@type": "Person", "name": teacher["name"]}
    rowsinfo = [("日期時間", when), ("地點", c["location"] or s["address"] or s["name"]), ("費用", price),
                ("名額", f"{c['capacity']} 位" + (f"（已報名 {booked} 位）" if s["show_reservation_count"] else ""))]
    if teacher:
        rowsinfo.append(("老師／團主", teacher["name"]))
    if c["dupr_required"]:
        rowsinfo.append(("DUPR 條件", dupr))
    body = (f'<main class="seo"><p><a href="{e(base)}">{e(s["name"])}</a> 主辦</p><h1>{e(c["name"])}</h1>'
            + "<dl>" + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rowsinfo) + "</dl>"
            + (f'<p>{e(c["description"])}</p>' if c["description"] else "") + f'<p><a href="{e(url)}">線上報名</a></p></main>')
    return render_index(head_tags(base, url, c["name"], desc, c["cover_url"] or s["cover_url"], s["name"], [ev], bool(c["listed"])),
                        body, f"{c['name']}｜{s['name']}")


def venue_page(request: Request):
    """場館首頁：場館資訊（結構化資料）＋近期公開活動的連結，讓搜尋引擎與 AI 找得到每一場活動。"""
    base = public_base(request)
    e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
    with db() as conn:
        s = get_settings(conn)
        today = now().date()
        cs = rows(conn.execute("SELECT * FROM courses WHERE listed=1 AND status='open' AND slot_set_id IS NULL AND date BETWEEN ? AND ?"
                               " ORDER BY date, start_time LIMIT 60", (today.isoformat(), (today + timedelta(days=int(s["open_days"] or 14))).isoformat())))
        sets = rows(conn.execute("SELECT * FROM slot_sets WHERE listed=1 ORDER BY id"))
    desc = (s["about"] or f"{s['name']}的匹克球課程、球敘與 DUPR 活動線上報名。").replace("\n", " ")[:150]
    ld = [{"@context": "https://schema.org", "@type": "SportsActivityLocation", "name": s["name"], "url": base, "description": desc,
           **({"address": s["address"]} if s["address"] else {}), **({"telephone": s["phone"]} if s["phone"] else {}),
           **({"image": base + s["cover_url"].lstrip("/")} if s["cover_url"] else {}),
           **({"sameAs": [s["line_url"]]} if s["line_url"] else {})}]
    items = "".join(f'<li><a href="{e(base + c["share_code"])}">{e(c["date"][5:].replace("-", "/"))}（{WEEKDAYS[date.fromisoformat(c["date"]).weekday()]}）'
                    f'{e(c["start_time"])} {e(c["name"])}</a></li>' for c in cs)
    items += "".join(f'<li><a href="{e(base + x["share_code"])}">{e(x["name"])}（線上選時段預約）</a></li>' for x in sets)
    body = (f'<main class="seo"><h1>{e(s["name"])}</h1><p>{e(desc)}</p>' + (f"<p>地址：{e(s['address'])}</p>" if s["address"] else "")
            + f"<h2>近期活動</h2><ul>{items}</ul></main>")
    title = f"{s['name']}｜匹克球課程、球敘與 DUPR 活動報名"
    return render_index(head_tags(base, base, title, desc, s["cover_url"], s["name"], ld), body, title)


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    """場館首頁＋公開、還沒結束的活動與時段預約。"""
    base = public_base(request)
    with db() as conn:
        today = now().date().isoformat()
        urls = [(base, today)]
        urls += [(base + c["share_code"], c["created_at"][:10]) for c in rows(conn.execute(
            "SELECT share_code, created_at FROM courses WHERE listed=1 AND status='open' AND slot_set_id IS NULL AND date>=? ORDER BY date LIMIT 5000", (today,)))]
        urls += [(base + x["share_code"], x["created_at"][:10]) for x in rows(conn.execute("SELECT share_code, created_at FROM slot_sets WHERE listed=1"))]
    xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(f"<url><loc>{html.escape(u)}</loc><lastmod>{m}</lastmod></url>" for u, m in urls) + "</urlset>")
    return Response(xml, media_type="application/xml")


# 首頁的「申請開通」表單、自助註冊、訂閱付款：見 saas.py（/platform/api/…）


import saas  # noqa: E402 — 平台路由要在 SPA 的萬用路由之前註冊

saas.register(app)

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request):
        if path.startswith("api/"):
            fail(404, "not found")
        if SHARE_CODE_RE.match(path.lower()) and path.lower() not in SHARE_RESERVED:  # 活動網址 <網站>/<代碼>
            return share_page(path, request)
        if path in ("", "index.html"):
            return venue_page(request)
        target = STATIC_DIR / path
        if path and target.is_file() and STATIC_DIR in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")
