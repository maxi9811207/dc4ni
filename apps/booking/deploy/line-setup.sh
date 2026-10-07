#!/usr/bin/env bash
# 填入 LINE Login 金鑰並重新啟動：sudo booking-line-setup
# 值從 LINE Developers → 你的 LINE Login channel 複製：
#   Basic settings → Channel ID、Channel secret；LIFF 分頁 → LIFF ID（沒有可留空）
# 推播（選填）：LINE Official Account Manager 建官方帳號 → 設定 → Messaging API 啟用（選同一個 Provider）
#   → LINE Developers 該 Messaging API channel → Messaging API 分頁最下方發行 Channel access token
set -euo pipefail
ENV_FILE=/etc/booking.env
[ "$(id -u)" = 0 ] || { echo "請用 sudo 執行"; exit 1; }
[ -f "$ENV_FILE" ] || { echo "找不到 $ENV_FILE，請先安裝約課系統"; exit 1; }

clean() { printf '%s' "$1" | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | tr -d '[:space:][:cntrl:]'; }
cur() { sed -n "s/^$1=//p" "$ENV_FILE" | tail -1; }
echo "（每一項直接按 Enter＝維持目前的設定）"
read -rp "Channel ID（10 位數字）：" ID < /dev/tty
read -rsp "Channel secret（輸入時不會顯示）：" SECRET < /dev/tty; echo
read -rp "LIFF ID（輸入 - ＝清除）：" LIFF < /dev/tty
read -rsp "官方帳號推播 Channel access token（選填，輸入 - ＝清除）：" PUSH < /dev/tty; echo
ID=$(clean "$ID"); SECRET=$(clean "$SECRET"); LIFF=$(clean "$LIFF"); PUSH=$(clean "$PUSH")
[ -n "$ID" ] || ID=$(cur LINE_CHANNEL_ID)
[ -n "$SECRET" ] || SECRET=$(cur LINE_CHANNEL_SECRET)
if [ -z "$LIFF" ]; then LIFF=$(cur LINE_LIFF_ID); elif [ "$LIFF" = "-" ]; then LIFF=""; fi
if [ -z "$PUSH" ]; then PUSH=$(cur LINE_MESSAGING_TOKEN); elif [ "$PUSH" = "-" ]; then PUSH=""; fi
[[ "$ID" =~ ^[0-9]{10}$ ]] || { echo "Channel ID 應為 10 位數字，沒有修改任何設定"; exit 1; }
[[ "$SECRET" =~ ^[0-9a-f]{32}$ ]] || { echo "Channel secret 應為 32 碼英數字，沒有修改任何設定"; exit 1; }
[ -z "$LIFF" ] || [[ "$LIFF" =~ ^${ID}-[A-Za-z0-9]+$ ]] || { echo "LIFF ID 應為「${ID}-xxxx」格式，沒有修改任何設定"; exit 1; }
[ -z "$PUSH" ] || [[ "$PUSH" =~ ^[A-Za-z0-9+/=]{100,}$ ]] || { echo "Channel access token 格式不對（應為 100 字以上的一長串英數字），沒有修改任何設定"; exit 1; }

cp -p "$ENV_FILE" "$ENV_FILE.bak"
for KV in "LINE_CHANNEL_ID=$ID" "LINE_CHANNEL_SECRET=$SECRET" "LINE_LIFF_ID=$LIFF" "LINE_MESSAGING_TOKEN=$PUSH"; do
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
    [ -n "$PUSH" ] && echo "LINE 推播已啟用：會員要加官方帳號好友才收得到（到 LINE Login channel 的 Basic settings 連結官方帳號，登入時就會提示加好友）"
    ;;
  *)
    echo "服務沒有正常啟動，已還原原本的設定：${CFG:-無回應}"
    cp -p "$ENV_FILE.bak" "$ENV_FILE"
    systemctl restart booking
    exit 1
    ;;
esac
