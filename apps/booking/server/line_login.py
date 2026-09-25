"""LINE Login（網頁授權碼流程＋LIFF 的 ID token 驗證），只用標準函式庫。

需要在 LINE Developers 建立 LINE Login channel：
  LINE_CHANNEL_ID / LINE_CHANNEL_SECRET；要在 LINE 裡開啟（LIFF）再加 LINE_LIFF_ID。
  Callback URL 設為 https://<網域>/api/auth/line/callback
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = os.getenv("LINE_AUTH_URL", "https://access.line.me/oauth2/v2.1/authorize")
API = os.getenv("LINE_API_BASE", "https://api.line.me").rstrip("/")


class LineError(Exception):
    pass


def enabled() -> bool:
    return bool(os.getenv("LINE_CHANNEL_ID") and os.getenv("LINE_CHANNEL_SECRET"))


def liff_id() -> str:
    return os.getenv("LINE_LIFF_ID", "") if enabled() else ""


def authorize_url(redirect_uri: str, state: str, nonce: str) -> str:
    q = {"response_type": "code", "client_id": os.environ["LINE_CHANNEL_ID"], "redirect_uri": redirect_uri,
         "state": state, "scope": "profile openid email", "nonce": nonce, "bot_prompt": "normal"}
    return AUTH_URL + "?" + urllib.parse.urlencode(q)


def _post(path: str, form: dict) -> dict:
    req = urllib.request.Request(API + path, data=urllib.parse.urlencode(form).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("error_description", "")
        except ValueError:
            detail = ""
        raise LineError(f"LINE 驗證失敗{('：' + detail) if detail else ''}")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise LineError("暫時無法連線到 LINE，請稍後再試")


def verify_id_token(id_token: str, nonce: str | None = None) -> dict:
    """回傳 LINE 使用者資料：sub（LINE user id）、name、picture、email。"""
    form = {"id_token": id_token, "client_id": os.environ["LINE_CHANNEL_ID"]}
    if nonce:
        form["nonce"] = nonce
    data = _post("/oauth2/v2.1/verify", form)
    if not data.get("sub"):
        raise LineError("LINE 驗證失敗")
    return {"sub": data["sub"], "name": data.get("name") or "LINE 使用者",
            "picture": data.get("picture") or "", "email": (data.get("email") or "").lower()}


def exchange_code(code: str, redirect_uri: str, nonce: str) -> dict:
    tokens = _post("/oauth2/v2.1/token", {
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        "client_id": os.environ["LINE_CHANNEL_ID"], "client_secret": os.environ["LINE_CHANNEL_SECRET"]})
    if not tokens.get("id_token"):
        raise LineError("LINE 沒有回傳身分資料，請確認 channel 已開啟 OpenID Connect")
    return verify_id_token(tokens["id_token"], nonce)
