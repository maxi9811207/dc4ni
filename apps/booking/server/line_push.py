"""LINE 官方帳號推播（Messaging API push），背景執行緒送出，不拖慢請求。

設定 LINE_MESSAGING_TOKEN（官方帳號 Messaging API channel 的 channel access token）後啟用。
收得到的條件：會員用 LINE 登入過，而且加了官方帳號好友；官方帳號要和 LINE Login channel 在同一個 Provider，
userId 才會相同（在 LINE Login channel 的 Basic settings 連結官方帳號，登入時會提示加好友）。
"""
import json
import logging
import os
import queue
import threading
import urllib.error
import urllib.request

API = os.getenv("LINE_MESSAGING_API", "https://api.line.me").rstrip("/")
log = logging.getLogger("line_push")
_queue: "queue.Queue[tuple[str, str]]" = queue.Queue(maxsize=5000)
_worker: threading.Thread | None = None
sent = {"ok": 0, "failed": 0}


def enabled() -> bool:
    return bool(os.getenv("LINE_MESSAGING_TOKEN"))


def _send(to: str, text: str):
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text[:4900]}]}).encode()
    req = urllib.request.Request(API + "/v2/bot/message/push", data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['LINE_MESSAGING_TOKEN']}"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            sent["ok"] += 1
    except urllib.error.HTTPError as e:
        # 400：對方沒加好友或封鎖；429：超過每月免費則數。都只記錄，不影響站內通知
        sent["failed"] += 1
        log.warning("LINE push %s → %s %s", to[:8], e.code, e.read()[:200])
    except (urllib.error.URLError, TimeoutError) as e:
        sent["failed"] += 1
        log.warning("LINE push %s failed: %s", to[:8], e)


def _run():
    while True:
        to, text = _queue.get()
        try:
            _send(to, text)
        finally:
            _queue.task_done()


def push(to: str, text: str):
    """排入背景佇列；沒設定 token 或 to 空白時不做事。"""
    global _worker
    if not enabled() or not to:
        return
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_run, name="line-push", daemon=True)
        _worker.start()
    try:
        _queue.put_nowait((to, text))
    except queue.Full:
        sent["failed"] += 1
