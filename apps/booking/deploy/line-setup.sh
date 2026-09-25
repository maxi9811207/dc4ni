#!/usr/bin/env bash
# 填入 LINE Login 金鑰並重新啟動：sudo booking-line-setup
# 值從 LINE Developers → 你的 LINE Login channel 複製：
#   Basic settings → Channel ID、Channel secret；LIFF 分頁 → LIFF ID（沒有可留空）
set -euo pipefail
ENV_FILE=/etc/booking.env
[ "$(id -u)" = 0 ] || { echo "請用 sudo 執行"; exit 1; }
[ -f "$ENV_FILE" ] || { echo "找不到 $ENV_FILE，請先安裝約課系統"; exit 1; }

clean() { printf '%s' "$1" | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | tr -d '[:space:][:cntrl:]'; }
read -rp "Channel ID（10 位數字）：" ID < /dev/tty
read -rsp "Channel secret（輸入時不會顯示）：" SECRET < /dev/tty; echo
read -rp "LIFF ID（沒有就直接按 Enter）：" LIFF < /dev/tty
ID=$(clean "$ID"); SECRET=$(clean "$SECRET"); LIFF=$(clean "$LIFF")
[[ "$ID" =~ ^[0-9]{10}$ ]] || { echo "Channel ID 應為 10 位數字，沒有修改任何設定"; exit 1; }
[[ "$SECRET" =~ ^[0-9a-f]{32}$ ]] || { echo "Channel secret 應為 32 碼英數字，沒有修改任何設定"; exit 1; }
[ -z "$LIFF" ] || [[ "$LIFF" =~ ^${ID}-[A-Za-z0-9]+$ ]] || { echo "LIFF ID 應為「${ID}-xxxx」格式，沒有修改任何設定"; exit 1; }

cp -p "$ENV_FILE" "$ENV_FILE.bak"
for KV in "LINE_CHANNEL_ID=$ID" "LINE_CHANNEL_SECRET=$SECRET" "LINE_LIFF_ID=$LIFF"; do
  KEY=${KV%%=*}
  sed -i "/^$KEY=/d" "$ENV_FILE"
  echo "$KV" >> "$ENV_FILE"
done
chmod 600 "$ENV_FILE"
systemctl restart booking

for _ in $(seq 1 15); do
  CFG=$(curl -fsS http://127.0.0.1:8100/api/auth/config 2>/dev/null) && break
  sleep 1
done
DOMAIN=$(sed -n 's/^BOOKING_DOMAIN=//p' "$ENV_FILE" | tail -1)
case "${CFG:-}" in
  *'"line_enabled":true'*)
    echo "完成！LINE 登入已啟用：${CFG}"
    [ -n "$DOMAIN" ] && echo "LINE Developers 的 Callback URL 必須是：https://$DOMAIN/api/auth/line/callback"
    [ -n "$DOMAIN" ] && [ -n "$LIFF" ] && echo "LIFF 的 Endpoint URL 必須是：https://$DOMAIN/"
    ;;
  *)
    echo "服務沒有正常啟動，已還原原本的設定：${CFG:-無回應}"
    cp -p "$ENV_FILE.bak" "$ENV_FILE"
    systemctl restart booking
    exit 1
    ;;
esac
