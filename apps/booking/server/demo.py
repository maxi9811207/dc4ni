"""虛構的示範場館（首頁「看看示範」的四個場館）。

環境變數 BOOKING_DEMO_TENANTS 指定哪些場館是示範場館，以及各自示範哪一種用法：
    BOOKING_DEMO_TENANTS=demo-club:club,demo-coach:coach,demo-dupr:dupr,demo-court:court
    club  球團俱樂部：單次球敘、週末大球敘、固定團課
    coach 教練課：小班團體課、一對一私人課（依教練分時段）、課卡
    dupr  DUPR 賽事：依分數分級的積分賽、單打、新手體驗
    court 球館租借：A／B／C 場每小時租借、夜間零打

- 第一次：寫入虛構的場館資料、老師、課卡與球友（全部是假的，不對應任何真實場館或人）。
- 之後每次排程（每 5 分鐘）：補齊未來兩週的活動與報名，課表永遠有東西可以看。
- 示範場館的頁面一律 noindex，假活動不會被搜尋引擎收錄；也不發開課提醒。
"""
import json
import os
import random
import secrets
import shutil
from datetime import date, timedelta
from pathlib import Path

import tenancy

DAYS_AHEAD = 14
NOTE = "（虛構的示範場館）"
PAY = "示範場館不用真的匯款：報名付費活動後，回填任意 5 位數字，就能看到付款審核的流程。"
PLAYERS = ["小安", "阿凱", "Jenny", "大雄", "Momo", "阿翔", "Ivy", "小豪", "Kiki", "阿德", "Nana", "Leo",
           "小茜", "阿傑", "Ruby", "Tom", "小芳", "阿斌", "Coco", "Ken", "小魚", "阿泰", "Yuki", "阿寶"]

PROFILES = {
    "club": {
        "venue": {"name": "晴空匹克球俱樂部", "address": "晴空運動中心" + NOTE,
                  "about": "這是 Digital Court 的示範場館，示範「球團俱樂部」的用法：平日午間球敘、週末大球敘、每週固定團課。"
                           "活動、團主與球友都是虛構的，每天自動更新，可以自由點點看。",
                  "categories": ["球敘", "固定團課"]},
        "teachers": [("Mia", "球敘團主", "負責分級球敘與配對，讓每個程度的人都打得開心。"),
                     ("阿哲", "團課教練", "每週二、四的固定團課，8 週一期，循序漸進。")],
        "plans": [("球敘 10 次卡", "sessions", 10, 120, 1500, "每次 150 元", 0)],
        "reviews": ["分級很準，打起來剛剛好", "報名、候補都在 LINE 上完成，超方便", "團課有系統，進步很快", "氣氛很好的球團"],
    },
    "coach": {
        "venue": {"name": "阿哲匹克球教室", "address": "晴空運動中心 B 場" + NOTE,
                  "about": "這是 Digital Court 的示範場館，示範「教練課」的用法：小班團體課、依教練分時段的一對一私人課。"
                           "教練與學員都是虛構的，每天自動更新，可以自由點點看。",
                  "categories": ["團體課", "私人課"]},
        "teachers": [("阿哲教練", "PPR 認證教練", "專長新手入門與雙打站位，一堂課就能上場打。"),
                     ("Vivian 教練", "前網球選手", "專攻截擊與網前技術，適合想突破的中階球友。"),
                     ("Ben 教練", "青少年教練", "親子課、青少年課，耐心又有趣。")],
        "plans": [("單堂體驗", "sessions", 1, 30, 600, "團體課體驗一堂", 0),
                  ("團體課 10 堂", "sessions", 10, 120, 5000, "每堂 500 元", 1),
                  ("私人課 5 堂", "sessions", 5, 90, 5500, "一對一，每堂 1,100 元", 2)],
        "reviews": ["教練講解很清楚，第一次打就上手！", "私人課針對我的問題調整，超有感", "小班制每個人都有照顧到", "Vivian 教練的網前教學很實用"],
    },
    "dupr": {
        "venue": {"name": "星河 DUPR 積分賽", "address": "星河運動公園室內館" + NOTE,
                  "about": "這是 Digital Court 的示範場館，示範「DUPR 比賽／活動報名」的用法：依 DUPR 分數分級的積分賽、單打場、新手體驗。"
                           "賽事與選手都是虛構的，每天自動更新，可以自由點點看。",
                  "categories": ["DUPR 雙打", "DUPR 單打", "新手體驗"]},
        "teachers": [("老K", "DUPR 賽事主辦", "每週辦 DUPR 計分賽，分組、賽程、比分都在系統上。"),
                     ("小昱", "裁判長", "賽事規則與計分，有問題現場找我。")],
        "plans": [],
        "reviews": ["分組很公平，比分上傳 DUPR 很快", "賽程表一目了然", "第一次打積分賽就很順", "報名要綁 DUPR 很合理"],
    },
    "court": {
        "venue": {"name": "綠洲匹克球館", "address": "綠洲運動園區" + NOTE,
                  "about": "這是 Digital Court 的示範場館，示範「球館租借預約」的用法：A／B／C 三面場地每小時租借、夜間零打。"
                           "場地與預約都是虛構的，每天自動更新，可以自由點點看。",
                  "categories": ["場地租借", "零打"]},
        "teachers": [("櫃台小綠", "球館管理員", "場地、器材、零打配對都可以找我。")],
        "plans": [("零打 10 次卡", "sessions", 10, 90, 1200, "每次 120 元", 0)],
        "reviews": ["線上就能看空場、直接訂，超方便", "場地維護得很好", "夜間零打很好配到人", "訂場付款流程很清楚"],
    },
}


def demo_map() -> dict[str, str]:
    out = {}
    for part in os.getenv("BOOKING_DEMO_TENANTS", "").split(","):
        slug, _, kind = part.strip().lower().partition(":")
        if slug and kind in PROFILES:
            out[slug] = kind
    return out


def kind_of(slug: str) -> str:
    return demo_map().get(slug, "")


def is_demo() -> bool:
    t = tenancy.current_or_none()
    return t is not None and bool(kind_of(t.slug))


def _cols(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _insert(conn, table: str, row: dict) -> int:
    have = _cols(conn, table)
    row = {k: v for k, v in row.items() if k in have}
    return conn.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' * len(row))})", tuple(row.values())).lastrowid


def _kv(conn, key: str) -> bool:
    return conn.execute("SELECT 1 FROM kv WHERE key=?", (key,)).fetchone() is not None


def _slot_set(conn, core, **row) -> int:
    base = {**core.DEFAULT_SLOT, "share_code": core.new_share_code(conn), "created_at": core.stamp()}
    return _insert(conn, "slot_sets", {**base, **row})


def setup(conn, kind: str):
    """第一次：場館資料、老師、課卡、球友、時段預約活動。做過就跳過。"""
    import app as core
    if _kv(conn, "demo_v2"):
        return
    p = PROFILES[kind]
    settings = {**p["venue"], "payment_info": PAY, "reminder_enabled": False}
    for k, v in settings.items():
        conn.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (k, json.dumps(v, ensure_ascii=False)))
    for i, t in enumerate(p["teachers"]):
        _insert(conn, "teachers", {"name": t[0], "title": t[1], "bio": t[2], "sort": i, "hourly_rate": 800})
    if p["plans"]:
        conn.executemany("INSERT INTO plans (name, type, quantity, valid_days, price, description, sort) VALUES (?,?,?,?,?,?,?)", p["plans"])
    for i, name in enumerate(PLAYERS):
        _insert(conn, "users", {"name": name, "email": f"demo-player-{i:02d}@example.invalid",
                                "password_hash": core.hash_password(secrets.token_hex(12)), "created_at": core.stamp()})
    src = Path(__file__).resolve().parent.parent / "landing" / "mock-cover.webp"  # 首頁手機示意圖用的同一張
    t = tenancy.current()
    if src.exists():
        t.upload_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, t.upload_dir / "demo-cover.webp")
    if kind == "coach":
        _slot_set(conn, core, name="阿哲教練 一對一私人課", category="私人課", teacher_id=1, capacity=1, fee=1200, pay_hours=24,
                  location="晴空運動中心 B 場", description="一對一 60 分鐘，依你的程度安排內容。付款後才算預約成功。")
        _slot_set(conn, core, name="Vivian 教練 一對一私人課", category="私人課", teacher_id=2, capacity=1, fee=1500, pay_hours=24,
                  location="晴空運動中心 B 場", description="一對一 60 分鐘，專攻網前與截擊。付款後才算預約成功。")
    if kind == "court":
        for court in ("A", "B", "C"):
            _slot_set(conn, core, name=f"{court} 場 場地租借", category="場地租借", capacity=1, fee=400, pay_hours=12,
                      location=f"綠洲匹克球館 {court} 場", description="每小時一格，一格最多 4 人。付款後才算預約成功，開打前 24 小時可以取消。")
    conn.execute("INSERT INTO kv VALUES ('demo_v2', ?)", (core.stamp(),))


def _book(conn, core, course_id: int, users: list[int], fee: int, rnd: random.Random, waitlist: list[int] = ()):
    for u in users:
        _insert(conn, "reservations", {"course_id": course_id, "user_id": u, "status": "booked", "fee": fee,
                                       "paid": 1 if fee else 0, "paid_at": core.stamp() if fee else "",
                                       "pay_note": f"{rnd.randint(10000, 99999)}" if fee else "",
                                       "created_at": core.stamp(), "updated_at": core.stamp()})
    for u in waitlist:
        _insert(conn, "reservations", {"course_id": course_id, "user_id": u, "status": "waitlist",
                                       "created_at": core.stamp(), "updated_at": core.stamp()})


class _Day:
    """某一天要建立的活動：共用日期、亂數與建立／報名的小工具。"""

    def __init__(self, conn, core, day: date, players: list[int], cover: str):
        self.conn, self.core, self.day, self.players, self.cover = conn, core, day, players, cover
        self.rnd = random.Random(f"{day.isoformat()}")
        self.wd = day.weekday()  # 0=週一

    def pick(self, n: int) -> list[int]:
        return self.rnd.sample(self.players, min(max(n, 0), len(self.players)))

    def course(self, booked: int, fee: int = 0, waitlist: int = 0, **row) -> int:
        base = {"date": self.day.isoformat(), "created_at": self.core.stamp(), "booking_deadline_min": 60,
                "cancel_deadline_min": 720, "plan_ids": "[]", "cost": 0, "fee": fee, "pay_hours": 24 if fee else 0,
                "share_code": self.core.new_share_code(self.conn)}
        cid = _insert(self.conn, "courses", {**base, **row})
        who = self.pick(min(booked, row.get("capacity", 10)) + waitlist)
        n = min(booked, row.get("capacity", 10))
        _book(self.conn, self.core, cid, who[:n], fee, self.rnd, waitlist=who[n:])
        return cid

    def slots(self, set_id: int, hours: range, busy: float):
        ss = dict(self.conn.execute("SELECT * FROM slot_sets WHERE id=?", (set_id,)).fetchone())
        d = self.day.isoformat()
        self.core.add_slots(self.conn, ss, [(d, f"{h:02d}:00", f"{h + 1:02d}:00") for h in hours])
        for r in self.conn.execute("SELECT id FROM courses WHERE slot_set_id=? AND date=?", (set_id, d)).fetchall():
            if self.rnd.random() < busy:
                _book(self.conn, self.core, r[0], self.pick(1), ss["fee"], self.rnd)


def _day_club(x: _Day):
    x.course(x.rnd.randint(7, 15), fee=150, name="午間歡樂球敘", category="球敘", teacher_id=1, start_time="12:00", end_time="14:30",
             capacity=16, location="晴空運動中心 A 場", cover_url=x.cover,
             description="不分程度輪轉配對，報名費 NT$150，請先匯款回填後五碼。")
    if x.wd in (5, 6):
        x.course(x.rnd.randint(14, 24), fee=200, waitlist=x.rnd.choice([0, 3]), name="週末大球敘（分級）", category="球敘", teacher_id=1,
                 start_time="09:00", end_time="12:00", capacity=24, location="晴空運動中心 A／B 場",
                 description="依程度分初階、中階、高階三區輪轉，名額滿了可以候補。")
    if x.wd in (1, 3):
        x.course(8, waitlist=x.rnd.choice([1, 2]), name="固定團課：中階班（每週二、四）", category="固定團課", teacher_id=2,
                 start_time="19:30", end_time="21:00", capacity=8, location="晴空運動中心 B 場",
                 description="8 週一期的固定團課，同一批學員一起練，每堂都可以單獨報名補位。")


def _day_coach(x: _Day, sets: list[int]):
    if x.wd < 5:
        x.course(x.rnd.randint(3, 6), waitlist=x.rnd.choice([0, 0, 2]), name="新手入門團體課", category="團體課", teacher_id=1,
                 start_time="19:00", end_time="20:30", capacity=6, beginner=1, location="晴空運動中心 B 場",
                 description="6 人小班：握拍、發球、回球到雙打站位，一堂課就能上場打。球拍可以借。")
    if x.wd in (2, 5):
        x.course(x.rnd.randint(4, 6), name="進階技術課：網前截擊", category="團體課", teacher_id=2,
                 start_time="10:00" if x.wd == 5 else "20:30", end_time="11:30" if x.wd == 5 else "22:00",
                 capacity=6, location="晴空運動中心 B 場", cover_url=x.cover, description="適合 DUPR 3.0 以上，專練 dink 與截擊。")
    if x.wd == 6:
        x.course(x.rnd.randint(4, 8), name="親子匹克球", category="團體課", teacher_id=3, start_time="14:00", end_time="15:30",
                 capacity=8, location="晴空運動中心 B 場", description="大人小孩一起上，8 歲以上都可以。")
    for i, sid in enumerate(sets):
        x.slots(sid, range(9, 12) if i == 0 else range(14, 17), busy=0.5)


def _day_dupr(x: _Day):
    if x.wd in (0, 2, 4):
        x.course(x.rnd.randint(8, 16), fee=200, name="夜間 DUPR 雙打 3.0–3.5", category="DUPR 雙打", teacher_id=1,
                 start_time="19:30", end_time="22:00", capacity=16, dupr_required=1, dupr_format="doubles", dupr_min=3.0, dupr_max=3.5,
                 location="星河室內館 1–4 場", description="比分會上傳 DUPR，報名要先綁定 DUPR 帳號，雙打分數 3.000–3.500。")
    if x.wd == 5:
        x.course(x.rnd.randint(16, 24), fee=300, waitlist=x.rnd.choice([0, 4]), name="週六積分賽 3.5–4.5", category="DUPR 雙打",
                 teacher_id=1, start_time="09:00", end_time="13:00", capacity=24, dupr_required=1, dupr_format="doubles",
                 dupr_min=3.5, dupr_max=4.5, location="星河室內館 1–6 場", cover_url=x.cover,
                 description="分組循環賽，賽程與比分都在系統上，賽後上傳 DUPR。")
    if x.wd == 6:
        x.course(x.rnd.randint(6, 12), fee=250, name="週日 DUPR 單打公開賽", category="DUPR 單打", teacher_id=2,
                 start_time="14:00", end_time="17:00", capacity=12, dupr_required=1, dupr_format="singles",
                 location="星河室內館 1–3 場", description="單打不分級，比分上傳 DUPR。")
    if x.wd == 3:
        x.course(x.rnd.randint(4, 10), name="新手體驗場（不計 DUPR）", category="新手體驗", teacher_id=2, start_time="19:30",
                 end_time="21:00", capacity=12, beginner=1, location="星河室內館 5–6 場",
                 description="還沒有 DUPR 分數也可以來，先熟悉比賽規則與計分。")


def _day_court(x: _Day, sets: list[int]):
    for i, sid in enumerate(sets):
        x.slots(sid, range(7, 22), busy=[0.6, 0.45, 0.3][i % 3] + (0.2 if x.wd >= 5 else 0))
    x.course(x.rnd.randint(6, 16), fee=150, name="夜間零打（自由配對）", category="零打", teacher_id=1, start_time="20:00",
             end_time="22:00", capacity=16, location="綠洲匹克球館 D 場", cover_url=x.cover,
             description="一個人也能來打，現場輪轉配對。報名費 NT$150。")


def top_up(conn):
    """補齊今天起兩週的活動（每天做一次、做過的日子跳過）。報名人數用日期當亂數種子，同一天每次都一樣。"""
    import app as core
    kind = kind_of(tenancy.current().slug)
    if not kind:
        return 0
    setup(conn, kind)
    players = [r[0] for r in conn.execute("SELECT id FROM users WHERE email LIKE 'demo-player-%' ORDER BY id")]
    if not players:
        return 0
    cover = "uploads/demo-cover.webp" if (tenancy.current().upload_dir / "demo-cover.webp").exists() else ""
    sets = [r[0] for r in conn.execute("SELECT id FROM slot_sets ORDER BY id")]
    today = core.now().date()
    made = 0
    for d in range(DAYS_AHEAD):
        day = today + timedelta(days=d)
        key = f"demo_day:{day.isoformat()}"
        if _kv(conn, key):
            continue
        x = _Day(conn, core, day, players, cover)
        if kind == "club":
            _day_club(x)
        elif kind == "coach":
            _day_coach(x, sets)
        elif kind == "dupr":
            _day_dupr(x)
        elif kind == "court":
            _day_court(x, sets)
        conn.execute("INSERT INTO kv VALUES (?, ?)", (key, core.stamp()))
        made += 1
    if not conn.execute("SELECT 1 FROM reviews LIMIT 1").fetchone():
        for i, text in enumerate(PROFILES[kind]["reviews"]):
            _insert(conn, "reviews", {"user_id": players[i], "teacher_id": 1, "rating": 4 if i == 2 else 5,
                                      "comment": text, "created_at": core.stamp()})
    return made
