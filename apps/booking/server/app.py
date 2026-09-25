"""約課系統後端：FastAPI + SQLite，單一場館。

學生：瀏覽課程、預約／候補／取消、購買課卡、評價。
場主：排課、名單點名、老師、課卡方案、訂單、會員、場館設定。
"""
import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import dupr
import reports

DATA_DIR = Path(os.getenv("BOOKING_DATA_DIR", Path(__file__).parent / "data"))
DB_PATH = DATA_DIR / "booking.db"
UPLOAD_DIR = DATA_DIR / "uploads"
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
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
  suspended INTEGER NOT NULL DEFAULT 0, suspend_reason TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
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
        "avatar_url": "TEXT NOT NULL DEFAULT ''",
    },
    "courses": {
        "dupr_required": "INTEGER NOT NULL DEFAULT 0",
        "dupr_format": "TEXT NOT NULL DEFAULT 'doubles'",
        "dupr_min": "REAL",
        "dupr_max": "REAL",
        "dupr_verified_only": "INTEGER NOT NULL DEFAULT 0",
        "template_id": "INTEGER",
    },
}

app = FastAPI(title="約課系統 API", docs_url="/api/docs", openapi_url="/api/openapi.json")


# ---------------------------------------------------------------- helpers

def now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def stamp() -> str:
    return now().isoformat(timespec="seconds")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(hash_password(password, salt), stored)


def get_settings(conn) -> dict:
    out = dict(DEFAULT_SETTINGS)
    for r in conn.execute("SELECT key, value FROM settings"):
        out[r["key"]] = json.loads(r["value"])
    return out


def admin_notify(conn, kind: str, text: str, link: str = ""):
    """場主後台通知（所有場主共用，各自記錄已讀位置）。"""
    conn.execute("INSERT INTO admin_notifications (kind, text, link, created_at) VALUES (?,?,?,?)",
                 (kind, text, link, stamp()))


def course_label(c: dict) -> str:
    return f"「{c['name']}」{c['date'][5:].replace('-', '/')} {c['start_time']}"


def notify(conn, user_id: int, text: str):
    conn.execute("INSERT INTO notifications (user_id, text, created_at) VALUES (?,?,?)",
                 (user_id, text, stamp()))


def course_start(c: dict) -> datetime:
    return datetime.fromisoformat(f"{c['date']}T{c['start_time']}")


USER_FIELDS = ("id", "name", "phone", "role", "suspended", "suspend_reason", "created_at", "dupr_id", "dupr_name",
               "dupr_doubles", "dupr_singles", "dupr_source", "dupr_verified", "dupr_synced_at", "avatar_url")


def public_user(u: dict) -> dict:
    return {k: u[k] for k in USER_FIELDS}


def mask_name(name: str) -> str:
    return (name[:1] + "**") if name else "**"


# ---------------------------------------------------------------- auth

def current_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    with db() as conn:
        return one(conn.execute(
            "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
            (authorization[7:],)))


def require_user(user=Depends(current_user)) -> dict:
    if not user:
        fail(401, "請先登入")
    return user


def require_owner(user=Depends(require_user)) -> dict:
    if user["role"] != "owner":
        fail(403, "僅限場主使用")
    return user


def issue_token(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO tokens VALUES (?,?,?)", (token, user_id, stamp()))
    return token


# ---------------------------------------------------------------- startup

@app.on_event("startup")
def startup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        conn.execute("PRAGMA journal_mode = WAL")
        phone = os.getenv("BOOKING_OWNER_PHONE")
        password = os.getenv("BOOKING_OWNER_PASSWORD")
        if phone and password and not one(conn.execute("SELECT id FROM users WHERE phone=?", (phone,))):
            conn.execute(
                "INSERT INTO users (name, phone, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                (os.getenv("BOOKING_OWNER_NAME", "場主"), phone, hash_password(password), "owner", stamp()))
        if os.getenv("BOOKING_SEED_DEMO") == "1" and not one(conn.execute("SELECT id FROM courses LIMIT 1")):
            seed_demo(conn)


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
        return "這場限已驗證的 DUPR 帳號，請聯絡場館核對身分"
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
    if c["status"] == "cancelled":
        button, state = "停課", "disabled"
    elif mine and mine["status"] in ("booked", "attended", "absent"):
        button, state = "已預約", "booked"
    elif mine and mine["status"] == "waitlist":
        button, state = "已候補", "waiting"
    elif t >= start:
        button, state = "已結束", "disabled"
    elif t >= start - timedelta(minutes=c["booking_deadline_min"]):
        button, state = "截止", "disabled"
    elif remain <= 0:
        button, state = ("候補", "waitlist") if settings["waitlist_enabled"] else ("額滿", "disabled")
    else:
        button, state = "預約", "book"
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
        "waitlist_position": position,
        "can_cancel": bool(mine) and (mine["status"] == "waitlist" or
                                      t < start - timedelta(minutes=c["cancel_deadline_min"])),
        "template_id": c["template_id"],
        "dupr_required": bool(c["dupr_required"]),
        "dupr_format": c["dupr_format"],
        "dupr_min": c["dupr_min"],
        "dupr_max": c["dupr_max"],
        "dupr_verified_only": bool(c["dupr_verified_only"]),
        "dupr_problem": dupr_problem(c, user) if user and not mine else None,
    }


def eligible_cards(conn, user_id: int, c: dict) -> list[dict]:
    today = now().date().isoformat()
    allowed = json.loads(c["plan_ids"])
    out = []
    for card in rows(conn.execute(
            "SELECT * FROM cards WHERE user_id=? AND starts_on<=? AND expires_on>=? ORDER BY expires_on",
            (user_id, today, today))):
        if allowed and card["plan_id"] not in allowed:
            continue
        need = c["cost"] if card["type"] == "points" else 1
        if card["type"] != "unlimited" and card["remaining"] < need:
            continue
        if card["type"] == "unlimited" and card["expires_on"] < c["date"]:
            continue
        out.append({**card, "charge": 0 if card["type"] == "unlimited" else need})
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
    if r["card_id"] and r["charged"]:
        conn.execute("UPDATE cards SET remaining = remaining + ? WHERE id=?", (r["charged"], r["card_id"]))


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
        conn.execute("UPDATE reservations SET status='booked', card_id=?, charged=?, updated_at=? WHERE id=?",
                     (card_id, charged, stamp(), w["id"]))
        notify(conn, w["user_id"], f"候補成功！您已預約「{c['name']}」{c['date']} {c['start_time']}。")
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
        return {**s, "rating": round(r["a"], 1) if r["a"] else None, "review_count": r["n"]}


def attendees(conn, c: dict, limit: int = 200) -> list[dict]:
    """已預約學員（姓名遮罩＋頭像）；DUPR 場附上該場依據的 DUPR 分數。"""
    out = []
    for r in conn.execute(
            "SELECT u.name, u.avatar_url, u.dupr_id, u.dupr_doubles, u.dupr_singles, u.dupr_verified"
            " FROM reservations r JOIN users u ON u.id=r.user_id"
            " WHERE r.course_id=? AND r.status IN ('booked','attended','absent') ORDER BY r.id LIMIT ?",
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
        cs = rows(conn.execute("SELECT * FROM courses WHERE date=? ORDER BY start_time, id", (day,)))
        d = date.fromisoformat(day)
        return {"date": day, "weekday": WEEKDAYS[d.weekday()],
                "show_reservation_count": s["show_reservation_count"],
                "courses": [{**course_view(conn, c, user, s), "attendees": attendees(conn, c, 6)} for c in cs]}


@app.get("/api/courses/{course_id}")
def course_detail(course_id: int, user=Depends(current_user)):
    with db() as conn:
        c = get_course(conn, course_id)
        v = course_view(conn, c, user, get_settings(conn))
        allowed = v["plan_ids"]
        plans = rows(conn.execute("SELECT id, name, type FROM plans WHERE active=1 ORDER BY sort, id"))
        v["plans"] = [p for p in plans if not allowed or p["id"] in allowed]
        v["cards"] = eligible_cards(conn, user["id"], c) if user else []
        v["attendees"] = attendees(conn, c)
        return v


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
        cs = rows(conn.execute("SELECT * FROM courses WHERE teacher_id=? AND date>=? AND status='open'"
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
        return review_list(conn, "WHERE r.hidden=0", ())


# ---------------------------------------------------------------- auth API

@app.post("/api/auth/register")
async def register(request: Request):
    b = await request.json()
    name, phone, password = (str(b.get(k, "")).strip() for k in ("name", "phone", "password"))
    if not name or not phone or len(password) < 6:
        fail(400, "請填寫姓名、手機，密碼至少 6 碼")
    with db() as conn:
        if one(conn.execute("SELECT id FROM users WHERE phone=?", (phone,))):
            fail(400, "此手機號碼已註冊，請直接登入")
        cur = conn.execute("INSERT INTO users (name, phone, password_hash, created_at) VALUES (?,?,?,?)",
                           (name[:40], phone[:20], hash_password(password), stamp()))
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)))
        admin_notify(conn, "member", f"新會員 {u['name']} 註冊", "/admin/members")
        return {"token": issue_token(conn, u["id"]), "user": public_user(u)}


@app.post("/api/auth/login")
async def login(request: Request):
    b = await request.json()
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE phone=?", (str(b.get("phone", "")).strip(),)))
        if not u or not check_password(str(b.get("password", "")), u["password_hash"]):
            fail(400, "手機或密碼錯誤")
        return {"token": issue_token(conn, u["id"]), "user": public_user(u)}


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
        out = {**public_user(user), "unread": unread}
        if user["role"] == "owner":
            out["admin_unread"] = conn.execute("SELECT COUNT(*) FROM admin_notifications WHERE id>?",
                                               (user["admin_seen_id"],)).fetchone()[0]
        return out


@app.put("/api/me")
async def update_me(request: Request, user=Depends(require_user)):
    b = await request.json()
    with db() as conn:
        name = str(b.get("name", user["name"])).strip()[:40] or user["name"]
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, user["id"]))
        if b.get("new_password"):
            if not check_password(str(b.get("password", "")), user["password_hash"]):
                fail(400, "原密碼錯誤")
            if len(b["new_password"]) < 6:
                fail(400, "新密碼至少 6 碼")
            conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (hash_password(b["new_password"]), user["id"]))
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


@app.get("/api/me/reservations")
def my_reservations(user=Depends(require_user)):
    with db() as conn:
        s = get_settings(conn)
        out = []
        for r in rows(conn.execute(
                "SELECT r.*, c.date, c.start_time FROM reservations r JOIN courses c ON c.id=r.course_id"
                " WHERE r.user_id=? AND r.status!='cancelled' ORDER BY c.date DESC, c.start_time DESC",
                (user["id"],))):
            c = get_course(conn, r["course_id"])
            v = course_view(conn, c, user, s)
            reviewed = one(conn.execute("SELECT id FROM reviews WHERE user_id=? AND course_id=?",
                                        (user["id"], c["id"])))
            out.append({"reservation": r, "course": v, "ended": now() >= course_start(c),
                        "reviewed": bool(reviewed)})
        return out


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


def ensure_active(user: dict):
    if user["suspended"]:
        fail(403, "SUSPENDED")


@app.post("/api/courses/{course_id}/reserve")
async def reserve(course_id: int, request: Request, user=Depends(require_user)):
    ensure_active(user)
    b = await request.json() if await request.body() else {}
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        c = get_course(conn, course_id)
        v = course_view(conn, c, user, get_settings(conn))
        if v["state"] not in ("book", "waitlist"):
            fail(400, f"此課程目前無法預約（{v['button']}）")
        if v["dupr_problem"]:
            fail(400, v["dupr_problem"])
        if v["state"] == "waitlist":
            if c["cost"] and not eligible_cards(conn, user["id"], c):
                fail(400, "沒有可用的課卡，請先購買課卡方案")
            conn.execute("INSERT INTO reservations (course_id, user_id, status, created_at, updated_at)"
                         " VALUES (?,?,?,?,?)", (course_id, user["id"], "waitlist", stamp(), stamp()))
            notify(conn, user["id"], f"已加入「{c['name']}」{c['date']} {c['start_time']} 候補名單。")
            admin_notify(conn, "waitlist", f"{user['name']} 候補 {course_label(c)}", f"/admin/courses/{c['id']}")
            return {"result": "waitlist"}
        card_id, charged = charge(conn, user["id"], c, b.get("card_id"))
        conn.execute("INSERT INTO reservations (course_id, user_id, status, card_id, charged, created_at, updated_at)"
                     " VALUES (?,?,?,?,?,?,?)", (course_id, user["id"], "booked", card_id, charged, stamp(), stamp()))
        notify(conn, user["id"], f"預約成功：「{c['name']}」{c['date']} {c['start_time']}。")
        admin_notify(conn, "booking", f"{user['name']} 預約 {course_label(c)}", f"/admin/courses/{c['id']}")
        return {"result": "booked"}


@app.post("/api/courses/{course_id}/cancel")
def cancel(course_id: int, user=Depends(require_user)):
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        c = get_course(conn, course_id)
        v = course_view(conn, c, user, get_settings(conn))
        r = v["my_reservation"]
        if not r:
            fail(400, "您沒有預約這堂課")
        if not v["can_cancel"]:
            fail(400, "已超過可自行取消的時間，請聯絡場館")
        conn.execute("UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?", (stamp(), r["id"]))
        refund(conn, r)
        notify(conn, user["id"], f"已取消「{c['name']}」{c['date']} {c['start_time']}。")
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
async def create_review(request: Request, user=Depends(require_user)):
    b = await request.json()
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
async def link_dupr(request: Request, user=Depends(require_user)):
    b = await request.json()
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


# ---------------------------------------------------------------- owner API

@app.get("/api/admin/dashboard")
def dashboard(owner=Depends(require_owner)):
    with db() as conn:
        s = get_settings(conn)
        today = now().date().isoformat()
        cs = rows(conn.execute("SELECT * FROM courses WHERE date=? ORDER BY start_time", (today,)))
        week_end = (now().date() + timedelta(days=7)).isoformat()
        return {
            "today": [course_view(conn, c, None, s) for c in cs],
            "pending_orders": conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
            "members": conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            "week_bookings": conn.execute(
                "SELECT COUNT(*) FROM reservations r JOIN courses c ON c.id=r.course_id"
                " WHERE r.status='booked' AND c.date BETWEEN ? AND ?", (today, week_end)).fetchone()[0],
            "month_revenue": conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='paid' AND substr(updated_at,1,7)=?",
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
                 "plan_ids", "dupr_required", "dupr_format", "dupr_min", "dupr_max", "dupr_verified_only", "template_id")
# 範本只存課程內容與預設時間，不含日期
TEMPLATE_FIELDS = tuple(k for k in COURSE_FIELDS if k not in ("date", "template_id")) + ("active", "sort")
# 修改範本時同步到未開始課程的欄位（不含時間與日期）
SYNC_FIELDS = tuple(k for k in TEMPLATE_FIELDS if k not in ("start_time", "end_time", "active", "sort"))


def clean_course(b: dict) -> dict:
    out = {k: b[k] for k in COURSE_FIELDS if k in b}
    for k in ("dupr_min", "dupr_max"):
        if k in out:
            out[k] = round(float(out[k]), 3) if out[k] not in (None, "") else None
    if out.get("dupr_format") not in (None, "doubles", "singles"):
        out["dupr_format"] = "doubles"
    for k in ("substitute", "beginner", "dupr_required", "dupr_verified_only"):
        if k in out:
            out[k] = 1 if out[k] else 0
    for k in ("capacity", "cost", "booking_deadline_min", "cancel_deadline_min"):
        if k in out:
            out[k] = max(int(out[k] or 0), 0)
    for k in ("teacher_id", "template_id"):
        if k in out:
            out[k] = int(out[k]) if out[k] else None
    if "plan_ids" in out:
        out["plan_ids"] = json.dumps([int(x) for x in out["plan_ids"] or []])
    return out


@app.post("/api/admin/courses")
async def create_course(request: Request, owner=Depends(require_owner)):
    b = await request.json()
    data = clean_course(b)
    if not data.get("name") or not data.get("date") or not data.get("start_time") or not data.get("end_time"):
        fail(400, "請填寫課程名稱、日期與時間")
    repeat = min(max(int(b.get("repeat_weeks", 1) or 1), 1), 26)
    first = date.fromisoformat(data["date"])
    ids = []
    with db() as conn:
        for w in range(repeat):
            row = {**data, "date": (first + timedelta(weeks=w)).isoformat(), "created_at": stamp()}
            cols = ",".join(row)
            cur = conn.execute(f"INSERT INTO courses ({cols}) VALUES ({','.join('?' * len(row))})",
                               tuple(row.values()))
            ids.append(cur.lastrowid)
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
async def create_template(request: Request, owner=Depends(require_owner)):
    data = clean_template(await request.json())
    if not data.get("name"):
        fail(400, "請填寫課程名稱")
    data["created_at"] = stamp()
    with db() as conn:
        cur = conn.execute(f"INSERT INTO course_templates ({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                           tuple(data.values()))
        return {"id": cur.lastrowid}


@app.put("/api/admin/templates/{template_id}")
async def update_template(template_id: int, request: Request, owner=Depends(require_owner)):
    """更新範本；apply_future=true 時同步更新這個範本之後尚未開始的課程。"""
    b = await request.json()
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
async def schedule_template(template_id: int, request: Request, owner=Depends(require_owner)):
    """依範本在期間內的指定星期幾排課；同一天同時段已有這個範本的課就略過。"""
    b = await request.json()
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
                           "template_id": template_id, "created_at": stamp()}
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


@app.put("/api/admin/courses/{course_id}")
async def update_course(course_id: int, request: Request, owner=Depends(require_owner)):
    data = clean_course(await request.json())
    with db() as conn:
        c = get_course(conn, course_id)
        if data:
            conn.execute(f"UPDATE courses SET {','.join(k + '=?' for k in data)} WHERE id=?",
                         (*data.values(), course_id))
        c = get_course(conn, course_id)
        promote_waitlist(conn, c)
        return {"ok": True}


@app.post("/api/admin/courses/{course_id}/status")
async def course_status(course_id: int, request: Request, owner=Depends(require_owner)):
    """停課時退還所有人的課卡並通知。"""
    status = (await request.json()).get("status")
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
                notify(conn, r["user_id"], f"「{c['name']}」{c['date']} {c['start_time']} 已停課，課卡已退還。")
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


def roster_rows(conn, course_id: int) -> list[dict]:
    return rows(conn.execute(
        "SELECT r.*, u.name, u.phone, u.dupr_id, u.dupr_doubles, u.dupr_singles, u.dupr_verified,"
        " cd.name card_name FROM reservations r JOIN users u ON u.id=r.user_id"
        " LEFT JOIN cards cd ON cd.id=r.card_id WHERE r.course_id=? AND r.status!='cancelled' ORDER BY r.id",
        (course_id,)))


@app.get("/api/admin/attendance")
def attendance(request: Request, owner=Depends(require_owner)):
    """某一天所有課程與名單，集中點名用。"""
    day = request.query_params.get("date") or now().date().isoformat()
    with db() as conn:
        s = get_settings(conn)
        out = []
        for c in rows(conn.execute("SELECT * FROM courses WHERE date=? AND status='open' ORDER BY start_time, id",
                                   (day,))):
            v = course_view(conn, c, None, s)
            v["roster"] = [r for r in roster_rows(conn, c["id"]) if r["status"] != "waitlist"]
            v["started"] = now() >= course_start(c)
            out.append(v)
        return out


@app.post("/api/admin/courses/{course_id}/attendance")
def mark_all(course_id: int, owner=Depends(require_owner)):
    """把尚未點名的學員全部標記為出席。"""
    with db() as conn:
        c = get_course(conn, course_id)
        if now() < course_start(c) - timedelta(minutes=30):
            fail(400, "課程開始前 30 分鐘才能點名")
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
def roster(course_id: int, owner=Depends(require_owner)):
    with db() as conn:
        c = get_course(conn, course_id)
        v = course_view(conn, c, None, get_settings(conn))
        v["roster"] = roster_rows(conn, course_id)
        return v


@app.post("/api/admin/reservations/{res_id}")
async def update_reservation(res_id: int, request: Request, owner=Depends(require_owner)):
    """點名（attended/absent/booked）或場主取消（cancelled，退卡）。"""
    b = await request.json()
    status = b.get("status")
    if status not in ("attended", "absent", "booked", "cancelled"):
        fail(400, "狀態錯誤")
    with db() as conn:
        r = one(conn.execute("SELECT * FROM reservations WHERE id=?", (res_id,)))
        if not r:
            fail(404, "找不到預約")
        c = get_course(conn, r["course_id"])
        if r["status"] == "waitlist" and status == "booked":
            card_id, charged = charge(conn, r["user_id"], c, None)
            conn.execute("UPDATE reservations SET card_id=?, charged=? WHERE id=?", (card_id, charged, res_id))
            notify(conn, r["user_id"], f"場館已將您從候補改為正式預約：「{c['name']}」{c['date']} {c['start_time']}。")
        conn.execute("UPDATE reservations SET status=?, updated_at=? WHERE id=?", (status, stamp(), res_id))
        if status == "cancelled":
            if b.get("refund", True):
                refund(conn, r)
            notify(conn, r["user_id"], f"場館已取消您的預約：「{c['name']}」{c['date']} {c['start_time']}。")
            if r["status"] == "booked":
                promote_waitlist(conn, c)
        return {"ok": True}


@app.post("/api/admin/courses/{course_id}/add")
async def add_to_course(course_id: int, request: Request, owner=Depends(require_owner)):
    """場主替會員加入課程（現場報名），可選擇是否扣卡。"""
    b = await request.json()
    with db() as conn:
        c = get_course(conn, course_id)
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (int(b.get("user_id", 0)),)))
        if not u:
            fail(404, "找不到會員")
        if one(conn.execute("SELECT id FROM reservations WHERE course_id=? AND user_id=? AND status!='cancelled'",
                            (course_id, u["id"]))):
            fail(400, "此會員已在名單中")
        card_id, charged = charge(conn, u["id"], c, None) if b.get("charge", True) else (None, 0)
        conn.execute("INSERT INTO reservations (course_id, user_id, status, card_id, charged, created_at, updated_at)"
                     " VALUES (?,?,?,?,?,?,?)", (course_id, u["id"], "booked", card_id, charged, stamp(), stamp()))
        notify(conn, u["id"], f"場館已為您預約「{c['name']}」{c['date']} {c['start_time']}。")
        return {"ok": True}


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
    async def create(request: Request, owner=Depends(require_owner)):
        data = clean(await request.json())
        if not data.get("name"):
            fail(400, "請填寫名稱")
        with db() as conn:
            cur = conn.execute(f"INSERT INTO {table} ({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                               tuple(data.values()))
            return {"id": cur.lastrowid}

    @app.put(f"/api/admin/{table}/{{item_id}}", name=f"update_{table}")
    async def update(item_id: int, request: Request, owner=Depends(require_owner)):
        data = clean(await request.json())
        with db() as conn:
            if data:
                conn.execute(f"UPDATE {table} SET {','.join(k + '=?' for k in data)} WHERE id=?",
                             (*data.values(), item_id))
            return {"ok": True}


crud("teachers", ("name", "title", "bio", "photo_url", "active", "sort"), ("active", "sort"))
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
async def update_order(order_id: int, request: Request, owner=Depends(require_owner)):
    status = (await request.json()).get("status")
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
        out = []
        for u in rows(conn.execute("SELECT * FROM users ORDER BY role='owner' DESC, id DESC")):
            m = public_user(u)
            m["note"] = u["note"]
            m["cards"] = rows(conn.execute(
                "SELECT * FROM cards WHERE user_id=? AND expires_on>=? ORDER BY expires_on", (u["id"], today)))
            m["bookings"] = conn.execute(
                "SELECT COUNT(*) FROM reservations WHERE user_id=? AND status IN ('booked','attended')",
                (u["id"],)).fetchone()[0]
            m["absences"] = conn.execute(
                "SELECT COUNT(*) FROM reservations WHERE user_id=? AND status='absent'", (u["id"],)).fetchone()[0]
            out.append(m)
        return out


@app.put("/api/admin/members/{user_id}")
async def update_member(user_id: int, request: Request, owner=Depends(require_owner)):
    b = await request.json()
    with db() as conn:
        u = one(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not u:
            fail(404, "找不到會員")
        if "suspended" in b:
            if u["id"] == owner["id"]:
                fail(400, "不能停權自己")
            conn.execute("UPDATE users SET suspended=?, suspend_reason=? WHERE id=?",
                         (1 if b["suspended"] else 0, str(b.get("suspend_reason", ""))[:200], user_id))
        if "dupr_verified" in b:
            conn.execute("UPDATE users SET dupr_verified=? WHERE id=?", (1 if b["dupr_verified"] else 0, user_id))
        if "dupr" in b:
            set_dupr(conn, user_id, b["dupr"], source="owner")
        if "avatar_url" in b:
            conn.execute("UPDATE users SET avatar_url=? WHERE id=?", (str(b["avatar_url"] or "")[:300], user_id))
        if "note" in b:
            conn.execute("UPDATE users SET note=? WHERE id=?", (str(b["note"])[:500], user_id))
        if b.get("role") in ("student", "owner") and u["id"] != owner["id"]:
            conn.execute("UPDATE users SET role=? WHERE id=?", (b["role"], user_id))
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
        for table in ("tokens", "reservations", "cards", "orders", "reviews", "notifications"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        for course_id in freed:
            promote_waitlist(conn, get_course(conn, course_id))
        return {"ok": True}


@app.post("/api/admin/members/{user_id}/cards")
async def give_card(user_id: int, request: Request, owner=Depends(require_owner)):
    b = await request.json()
    with db() as conn:
        plan = one(conn.execute("SELECT * FROM plans WHERE id=?", (int(b.get("plan_id", 0)),)))
        if not plan:
            fail(404, "找不到方案")
        grant_card(conn, user_id, plan, "manual")
        return {"ok": True}


@app.put("/api/admin/cards/{card_id}")
async def adjust_card(card_id: int, request: Request, owner=Depends(require_owner)):
    b = await request.json()
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
async def hide_review(review_id: int, request: Request, owner=Depends(require_owner)):
    b = await request.json()
    with db() as conn:
        conn.execute("UPDATE reviews SET hidden=? WHERE id=?", (1 if b.get("hidden") else 0, review_id))
        return {"ok": True}


@app.put("/api/admin/settings")
async def update_settings(request: Request, owner=Depends(require_owner)):
    b = await request.json()
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


async def save_image(file: UploadFile, max_mb: int) -> str:
    ext = ALLOWED_IMAGES.get(file.content_type)
    if not ext:
        fail(400, "只接受 JPG、PNG、WebP、GIF")
    content = await file.read()
    if len(content) > max_mb * 1024 * 1024:
        fail(400, f"圖片需小於 {max_mb}MB")
    name = uuid.uuid4().hex + ext
    (UPLOAD_DIR / name).write_bytes(content)
    return f"uploads/{name}"


@app.post("/api/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(require_user)):
    url = await save_image(file, 2)
    with db() as conn:
        conn.execute("UPDATE users SET avatar_url=? WHERE id=?", (url, user["id"]))
        return public_user(one(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


# ---------------------------------------------------------------- static

@app.exception_handler(HTTPException)
def http_error(_request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.get("/uploads/{name}")
def uploaded(name: str):
    path = UPLOAD_DIR / Path(name).name
    if not path.is_file():
        fail(404, "not found")
    return FileResponse(path)


if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            fail(404, "not found")
        target = STATIC_DIR / path
        if path and target.is_file() and STATIC_DIR in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")
