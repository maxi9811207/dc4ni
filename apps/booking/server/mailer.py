"""寄信（Resend HTTP API）。在背景執行緒送出：不拖慢請求，寄失敗只記錄、不影響主流程。

環境變數：
  RESEND_API_KEY   Resend 的 API 金鑰（沒填就不寄）
  MAIL_FROM        寄件者，例如  Digital Court <dc@dc-studio.cc>（網域需在 Resend 驗證過）
"""
import json
import logging
import os
import threading
import urllib.request

log = logging.getLogger("mailer")


def enabled() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("MAIL_FROM"))


def _send(to: list[str], subject: str, text: str, reply_to: str | None):
    body = {"from": os.environ["MAIL_FROM"], "to": to, "subject": subject, "text": text}
    if reply_to:
        body["reply_to"] = reply_to
    req = urllib.request.Request(
        os.getenv("RESEND_API_URL", "https://api.resend.com/emails"), data=json.dumps(body).encode(), method="POST",
        # Resend 前面有 Cloudflare，urllib 預設的 User-Agent 會被擋
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json",
                 "User-Agent": "DigitalCourt/1.0 (+https://digital-court.cc)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            log.info("mail sent to %s: %s", to, r.status)
    except Exception as e:  # noqa: BLE001
        log.warning("mail to %s failed: %s", to, e)


def send(to: list[str] | str, subject: str, text: str, reply_to: str | None = None):
    if not enabled():
        return
    threading.Thread(target=_send, args=([to] if isinstance(to, str) else to, subject, text, reply_to), daemon=True).start()
