"""DUPR Partner API 用戶端（只用標準函式庫）。

需要場館向 DUPR 申請的合作夥伴金鑰：
  DUPR_CLIENT_KEY / DUPR_CLIENT_SECRET，DUPR_ENV=production 或 uat。

  POST {base}/auth/v1/token        header x-authorization: base64(key:secret) -> result.token
  GET  {base}/user/v1/{duprId}     Bearer token -> 姓名、單打／雙打分數
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

BASES = {"production": "https://api.dupr.com/api", "uat": "https://uat.mydupr.com/api"}
DUPR_ID_RE = re.compile(r"^[A-Z0-9]{4,12}$")

_token = {"value": None, "expires": 0.0}


class DuprError(Exception):
    pass


def enabled() -> bool:
    return bool(os.getenv("DUPR_CLIENT_KEY") and os.getenv("DUPR_CLIENT_SECRET"))


def _base() -> str:
    if os.getenv("DUPR_BASE_URL"):
        return os.environ["DUPR_BASE_URL"].rstrip("/")
    return BASES.get(os.getenv("DUPR_ENV", "production"), BASES["production"])


def _request(method: str, path: str, headers: dict, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_base() + path, data=data, method=method,
                                 headers={"Accept": "application/json", "Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise DuprError("找不到這個 DUPR ID，請確認後再試")
        raise DuprError(f"DUPR 服務回應錯誤（{e.code}），請稍後再試")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise DuprError("暫時無法連線到 DUPR，請稍後再試")


def _access_token() -> str:
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    creds = f"{os.environ['DUPR_CLIENT_KEY']}:{os.environ['DUPR_CLIENT_SECRET']}"
    data = _request("POST", "/auth/v1/token", {"x-authorization": base64.b64encode(creds.encode()).decode()})
    result = data.get("result") or {}
    token = result.get("token") if isinstance(result, dict) else None
    if not token:
        raise DuprError("DUPR 金鑰驗證失敗，請聯絡場館")
    _token["value"] = token
    expiry = result.get("expiry")
    _token["expires"] = _parse_expiry(expiry)
    return token


def _parse_expiry(expiry) -> float:
    if isinstance(expiry, (int, float)):
        return expiry / 1000 if expiry > 1e12 else float(expiry)
    return time.time() + 50 * 60


def _num(v):
    try:
        f = float(v)
        return round(f, 3) if 1 <= f <= 8 else None
    except (TypeError, ValueError):
        return None  # "NR"（尚無分數）或其他格式


def _find(obj, keys: tuple, depth: int = 0):
    """在巢狀回應中找第一個符合的欄位（DUPR 各版本回應結構略有不同）。"""
    if depth > 4:
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, "", {}):
                return obj[k]
        for v in obj.values():
            found = _find(v, keys, depth + 1)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find(v, keys, depth + 1)
            if found is not None:
                return found
    return None


def parse_player(data: dict) -> dict:
    result = data.get("result", data)
    if isinstance(result, list):
        result = result[0] if result else {}
    doubles = _find(result, ("doublesRating", "doubles"))
    singles = _find(result, ("singlesRating", "singles"))
    if isinstance(doubles, dict):
        doubles = _find(doubles, ("rating", "value"))
    if isinstance(singles, dict):
        singles = _find(singles, ("rating", "value"))
    return {
        "name": _find(result, ("fullName", "name", "displayName")) or "",
        "doubles": _num(doubles),
        "singles": _num(singles),
    }


def normalize_id(dupr_id: str) -> str:
    dupr_id = (dupr_id or "").strip().upper()
    if not DUPR_ID_RE.match(dupr_id):
        raise DuprError("DUPR ID 格式不正確（例如 GB0NV05E，可在 DUPR App 個人頁面找到）")
    return dupr_id


def fetch_player(dupr_id: str) -> dict:
    token = _access_token()
    data = _request("GET", f"/user/v1/{dupr_id}", {"Authorization": f"Bearer {token}"})
    if data.get("status") == "FAILURE":
        raise DuprError(data.get("message") or "找不到這個 DUPR ID")
    return parse_player(data)


# ---------------------------------------------------------------- 比賽上傳（Partner API：create／batch／update／delete）

BATCH_LIMIT = 100  # DUPR 一次最多 100 場


def _error_text(data) -> str:
    """把 DUPR 的錯誤回應整理成一行（errors 可能是 {欄位: [訊息]}、[訊息] 或字串）。"""
    if not isinstance(data, dict):
        return str(data or "")[:300]
    errs = data.get("errors") or data.get("error")
    parts = []
    if isinstance(errs, dict):
        for v in errs.values():
            parts += v if isinstance(v, list) else [v]
    elif isinstance(errs, list):
        parts = errs
    elif errs:
        parts = [errs]
    text = "；".join(str(p) for p in parts if p) or data.get("message") or "DUPR 拒絕了這筆資料"
    return text[:300]


def _partner_call(method: str, path: str, body) -> dict:
    """Partner token 呼叫；HTTP 4xx 時把 DUPR 的錯誤說明帶出來（比賽資料的錯誤要讓場主看得懂哪裡不對）。"""
    data = json.dumps(body).encode()
    req = urllib.request.Request(_base() + path, data=data, method=method,
                                 headers={"Accept": "application/json", "Content-Type": "application/json",
                                          "Authorization": f"Bearer {_access_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _token["value"] = None  # 下次重新取 token
        try:
            detail = json.loads(e.read() or b"{}")
        except ValueError:
            detail = {}
        if 400 <= e.code < 500:
            raise DuprError(_error_text(detail) if detail else f"DUPR 拒絕了這筆資料（{e.code}）")
        raise DuprError(f"DUPR 服務回應錯誤（{e.code}），請稍後再試")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise DuprError("暫時無法連線到 DUPR，請稍後再試")


def create_matches(matches: list[dict]) -> tuple[dict, dict]:
    """批次上傳。回傳 ({identifier: matchCode}, {identifier: 錯誤說明})；單筆失敗不影響其他筆。"""
    ok, bad = {}, {}
    for i in range(0, len(matches), BATCH_LIMIT):
        chunk = matches[i:i + BATCH_LIMIT]
        try:
            data = _partner_call("POST", "/match/v1.0/batch", chunk)
        except DuprError as e:
            bad.update({m["identifier"]: str(e) for m in chunk})
            continue
        result = data.get("result") or {}
        for r in result.get("matchCodes") or []:
            ok[r.get("identifier")] = str(r.get("matchCode") or "")
        for r in result.get("errors") or []:
            bad[r.get("identifier")] = str(r.get("error") or r.get("message") or "DUPR 拒絕了這場")[:300]
        for m in chunk:  # 回應沒提到的也當失敗，避免誤以為已上傳
            if m["identifier"] not in ok and m["identifier"] not in bad:
                bad[m["identifier"]] = "DUPR 沒有回應這場的結果，請再上傳一次"
    return ok, bad


def update_match(match_code: str, match: dict) -> None:
    """修改已上傳的比賽（DUPR 會重算分數）。matchId 就是建立時回傳的 matchCode。"""
    data = _partner_call("POST", "/match/v1.0/update", {**match, "matchId": int(match_code)})
    if data.get("status") not in ("SUCCESS", None):
        raise DuprError(_error_text(data))


def delete_match(match_code: str, identifier: str) -> None:
    """撤回已上傳的比賽（DUPR 會把對分數的影響還原）。"""
    data = _partner_call("DELETE", "/match/v1.0/delete", {"matchCode": match_code, "identifier": identifier})
    if data.get("status") not in ("SUCCESS", None):
        raise DuprError(_error_text(data))


# ---------------------------------------------------------------- 球員 SSO（DUPR 官方登入，取得唯讀 user token）
# 規定：球員只能透過 SSO 連結 DUPR，不能手動填 DUPR ID（https://dupr.gitbook.io/dupr-raas/integration-checklist/sso-login）

SSO_BASES = {"production": "https://dashboard.dupr.com", "uat": "https://uat.dupr.gg"}
PUBLIC_BASES = {"production": "https://api.dupr.gg", "uat": "https://api.uat.dupr.gg"}
ENTITLEMENT_TTL = 24 * 3600  # 資格最多快取 24 小時


def _env() -> str:
    return os.getenv("DUPR_ENV", "production") if os.getenv("DUPR_ENV") in SSO_BASES else "production"


def sso_enabled() -> bool:
    return enabled() and os.getenv("DUPR_SSO", "1") != "0"


def sso_url() -> str:
    """嵌進 iframe 的登入網址；網址裡是 base64 的 clientKey（不是 secret）。"""
    base = os.getenv("DUPR_SSO_BASE") or SSO_BASES[_env()]
    key = base64.b64encode(os.environ["DUPR_CLIENT_KEY"].encode()).decode()
    return f"{base.rstrip('/')}/login-external-app/{key}"


def sso_origin() -> str:
    return (os.getenv("DUPR_SSO_BASE") or SSO_BASES[_env()]).rstrip("/")


def _public_call(method: str, path: str, token: str | None = None, headers: dict | None = None) -> dict:
    base = (os.getenv("DUPR_PUBLIC_BASE") or PUBLIC_BASES[_env()]).rstrip("/")
    h = {"Accept": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=b"" if method == "POST" else None, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise DuprAuthError("DUPR 登入已失效，請重新用 DUPR 帳號登入")
        raise DuprError(f"DUPR 服務回應錯誤（{e.code}），請稍後再試")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise DuprError("暫時無法連線到 DUPR，請稍後再試")


class DuprAuthError(DuprError):
    """使用者的 token 失效（過期或在 DUPR 取消授權），要重新 SSO。"""


def sso_identity(user_token: str) -> dict:
    """用 SSO 拿到的 user token 向 DUPR 確認身分（DUPR ID 以這裡為準，不信任前端傳來的）。"""
    data = _public_call("GET", "/public/user/info", user_token)
    results = data.get("results") or []
    if data.get("status") == "FAILURE" or not results or not results[0].get("duprId"):
        raise DuprError("無法向 DUPR 確認您的身分，請再登入一次")
    r = results[0]
    return {"dupr_id": normalize_id(str(r["duprId"])), "name": r.get("fullName") or ""}


def refresh_tokens(refresh_token: str) -> tuple[str, str]:
    """access token 過期時換新；refresh token 每次都會換，兩個都要存。"""
    data = _public_call("GET", "/auth/v2.0/refresh", headers={"x-refresh-token": refresh_token})
    r = data.get("result") or {}
    if not r.get("accessToken"):
        raise DuprAuthError("DUPR 登入已失效，請重新用 DUPR 帳號登入")
    return r["accessToken"], r.get("refreshToken") or refresh_token


def entitlements(user_token: str) -> list[str]:
    """球員在 tournaments（有計分的比賽）資源上的資格，例如 ['BASIC_L1', 'PREMIUM_L1']。
    沒有 BASIC_L1＝被限制或停權，不能參加 DUPR 比賽。"""
    data = _public_call("POST", "/subscription/active", user_token)
    out = set()
    body = data.get("result") if isinstance(data.get("result"), dict) else data
    for s in (body.get("subscriptions") or []) + [body]:  # 文件範例兩種形狀都出現過
        for e in ((s.get("entitlements") or {}).get("tournaments") or []):
            out.add(e if isinstance(e, str) else str(e.get("name") or e.get("value") or e))
    return sorted(out)


# ---------------------------------------------------------------- 評分 webhook（DUPR 主動通知分數變動）
# 規定：分數要靠 webhook 保持最新（https://dupr.gitbook.io/dupr-raas/integration-checklist/ratings-and-webhooks）

RATING_TOPIC = "RATING"
RATING_EVENTS = ("RATING", "RATING_SEED")  # SEED 是訂閱當下 DUPR 立刻回送的現況
SUBSCRIBE_PATH = "/user/v1.0/subscribe/webhook-event"
SUBSCRIBE_LIMIT = 100


def client_id() -> str:
    return os.getenv("DUPR_CLIENT_ID", "").strip()


def webhook_secret() -> str:
    return os.getenv("DUPR_WEBHOOK_SECRET", "").strip()


def webhook_client_ok(value) -> bool:
    """通知是不是我們的。DUPR 在 envelope 的 clientId 放的是 clientKey（UAT 實測 2026-10-06），
    不是 onboarding 信上的數字 Client ID，所以兩者都接受。沒有任何可比對的值就一律不收。"""
    got = str(value or "").strip()
    known = {os.getenv("DUPR_CLIENT_KEY", "").strip(), client_id()} - {""}
    return bool(got) and got in known


def register_webhook(url: str) -> dict:
    """告訴 DUPR 把分數通知送到這個網址（必須是 HTTPS、且能立刻回 200）。"""
    return _partner_call("POST", "/v1.0/webhook", {"webhookUrl": url, "topics": [RATING_TOPIC]})


def subscribe_ratings(dupr_ids: list[str]) -> None:
    """訂閱這些球員的分數變動；每筆成功的訂閱 DUPR 會立刻回送一次現況（RATING_SEED）。"""
    ids = [i for i in dict.fromkeys(dupr_ids) if i]
    for i in range(0, len(ids), SUBSCRIBE_LIMIT):
        _partner_call("POST", SUBSCRIBE_PATH, {"duprIds": ids[i:i + SUBSCRIBE_LIMIT], "topic": RATING_TOPIC})


def unsubscribe_ratings(dupr_ids: list[str]) -> None:
    ids = [i for i in dict.fromkeys(dupr_ids) if i]
    for i in range(0, len(ids), SUBSCRIBE_LIMIT):
        _partner_call("DELETE", SUBSCRIBE_PATH, {"duprIds": ids[i:i + SUBSCRIBE_LIMIT], "topic": RATING_TOPIC})


def parse_rating_event(body: dict) -> dict | None:
    """把 DUPR 的通知轉成 {dupr_id, doubles, singles, name}；不是分數通知就回 None。
    分數可能是 "NR"（尚無分數）或 null，_num 會轉成 None。"""
    if not isinstance(body, dict) or str(body.get("event") or "") not in RATING_EVENTS:
        return None
    msg = body.get("message") or {}
    raw = str(msg.get("duprId") or "").strip().upper()
    if not DUPR_ID_RE.match(raw):
        return None
    rating = msg.get("rating") or {}
    return {"dupr_id": raw, "doubles": _num(rating.get("doubles")), "singles": _num(rating.get("singles")),
            "name": str(msg.get("name") or "")[:60]}
