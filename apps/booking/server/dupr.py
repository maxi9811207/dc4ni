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
