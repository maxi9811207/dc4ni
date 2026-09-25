#!/usr/bin/env bash
# 約課系統一鍵安裝／更新（Ubuntu 22.04／24.04）
#
#   curl -fsSL https://raw.githubusercontent.com/maxi9811207/dc4ni/claude/upbeat-davinci-5wb5rp/apps/booking/deploy/install.sh | sudo bash
#
# 可選環境變數：
#   BOOKING_DOMAIN=booking.example.com   用網域對外（會另外建立 nginx 站台，並申請 HTTPS 憑證）
#                                        沒有網域可用 sslip.io，例如 IP 1.2.3.4 → BOOKING_DOMAIN=1-2-3-4.sslip.io
#   BOOKING_PORT=8080                    沒有網域時，用 http://主機IP:8080 對外（預設 8080）
#   BOOKING_AUTO_UPDATE=1                安裝自動更新：每 5 分鐘檢查 GitHub 分支，有新版就自動重新部署
#
# 網域會記在 /etc/booking.env，之後更新不必再指定。
# 只會新增 /opt/booking、/etc/booking.env、booking.service 與 nginx 的 booking 站台，
# 不會修改主機上既有的網站設定；nginx 設定檢查失敗會自動還原。
set -euo pipefail

REPO=https://github.com/maxi9811207/dc4ni.git
BRANCH=${BOOKING_BRANCH:-claude/upbeat-davinci-5wb5rp}
APP=/opt/booking
ENV_FILE=/etc/booking.env
PORT=${BOOKING_PORT:-8080}
DOMAIN=${BOOKING_DOMAIN:-}
if [ -z "$DOMAIN" ] && [ -f "$ENV_FILE" ]; then
  DOMAIN=$(sed -n 's/^BOOKING_DOMAIN=//p' "$ENV_FILE" | tail -1)
fi

[ "$(id -u)" = 0 ] || { echo "請用 sudo 執行"; exit 1; }

echo "==> 安裝套件"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3-venv nginx > /dev/null

echo "==> 下載程式"
SRC=$(mktemp -d)
git clone -q --depth 1 -b "$BRANCH" "$REPO" "$SRC"
COMMIT=$(git -C "$SRC" rev-parse HEAD)
id booking &>/dev/null || useradd --system --home "$APP" --shell /usr/sbin/nologin booking
mkdir -p "$APP/data"
rm -rf "$APP/server.new" && cp -r "$SRC/apps/booking/server" "$APP/server.new"
[ -f "$APP/server.new/static/index.html" ] || { echo "找不到前端檔案，請確認分支內容"; exit 1; }
rm -rf "$APP/server" && mv "$APP/server.new" "$APP/server"
rm -rf "$SRC"

echo "==> 安裝 Python 套件"
[ -d "$APP/venv" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q -r "$APP/server/requirements.txt"
chown -R booking:booking "$APP"

if [ ! -f "$ENV_FILE" ]; then
  echo "==> 建立場主帳號（之後用這組手機號碼與密碼登入後台）"
  read -rp "場主姓名：" OWNER_NAME < /dev/tty
  read -rp "場主手機號碼：" OWNER_PHONE < /dev/tty
  read -rsp "場主密碼（至少 6 碼）：" OWNER_PASSWORD < /dev/tty; echo
  read -rp "放入示範課程資料？(y/N)：" DEMO < /dev/tty
  cat > "$ENV_FILE" <<CONF
BOOKING_DATA_DIR=$APP/data
BOOKING_TZ=Asia/Taipei
BOOKING_OWNER_NAME=$OWNER_NAME
BOOKING_OWNER_PHONE=$OWNER_PHONE
BOOKING_OWNER_PASSWORD=$OWNER_PASSWORD
BOOKING_SEED_DEMO=$([ "${DEMO,,}" = y ] && echo 1 || echo 0)
# 向 DUPR 申請合作夥伴金鑰後填入，即可自動取得學員的 DUPR 姓名與分數
DUPR_CLIENT_KEY=
DUPR_CLIENT_SECRET=
DUPR_ENV=production
CONF
  chmod 600 "$ENV_FILE"
fi
# 補上新版本需要的設定欄位（不覆蓋已經填好的值）
for KEY in DUPR_CLIENT_KEY DUPR_CLIENT_SECRET LINE_CHANNEL_ID LINE_CHANNEL_SECRET LINE_LIFF_ID; do
  grep -q "^$KEY=" "$ENV_FILE" || echo "$KEY=" >> "$ENV_FILE"
done
if [ -n "$DOMAIN" ]; then
  sed -i '/^BOOKING_DOMAIN=/d' "$ENV_FILE"
  echo "BOOKING_DOMAIN=$DOMAIN" >> "$ENV_FILE"
fi

echo "==> 設定系統服務"
cat > /etc/systemd/system/booking.service <<UNIT
[Unit]
Description=Booking system
After=network.target

[Service]
User=booking
EnvironmentFile=$ENV_FILE
WorkingDirectory=$APP/server
ExecStart=$APP/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8100 --proxy-headers
Restart=always
MemoryMax=300M

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable -q booking
systemctl restart booking

for i in $(seq 1 20); do
  curl -fsS http://127.0.0.1:8100/api/venue > /dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:8100/api/venue > /dev/null || { journalctl -u booking -n 30 --no-pager; exit 1; }

echo "==> 設定 nginx"
SITE=/etc/nginx/sites-available/booking
if [ -n "$DOMAIN" ]; then
  LISTEN="listen 80;"
  NAME="server_name $DOMAIN;"
else
  LISTEN="listen $PORT;"
  NAME="server_name _;"
fi
BACKUP=$(mktemp)
[ -f "$SITE" ] && cp "$SITE" "$BACKUP"
# 已經設定過同一個網域／port 就不動（保留 certbot 加上的 HTTPS 設定）
if [ -f "$SITE" ] && grep -qF "$NAME" "$SITE" && { [ -n "$DOMAIN" ] || grep -qF "$LISTEN" "$SITE"; }; then
  echo "nginx 站台已存在，保留現有設定"
else
cat > "$SITE" <<NGINX
server {
    $LISTEN
    $NAME
    client_max_body_size 10M;
    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
ln -sf "$SITE" /etc/nginx/sites-enabled/booking
if ! nginx -t 2>/dev/null; then
  echo "nginx 設定檢查失敗，已還原，既有網站不受影響："
  nginx -t || true
  if [ -s "$BACKUP" ]; then cp "$BACKUP" "$SITE"; else rm -f "$SITE" /etc/nginx/sites-enabled/booking; fi
  exit 1
fi
systemctl reload nginx
fi

if [ -n "$DOMAIN" ] && [ -d "/etc/letsencrypt/live/$DOMAIN" ] && grep -q "listen 443" "$SITE"; then
  DOMAIN_HTTPS_DONE=1
fi
if [ -n "$DOMAIN" ] && [ -z "${DOMAIN_HTTPS_DONE:-}" ] && ! command -v certbot > /dev/null; then
  apt-get install -y -qq certbot python3-certbot-nginx > /dev/null
fi
if [ -n "$DOMAIN" ] && [ -z "${DOMAIN_HTTPS_DONE:-}" ] && command -v certbot > /dev/null; then
  certbot --nginx -d "$DOMAIN" --non-interactive --redirect --agree-tos --register-unsafely-without-email \
    || echo "HTTPS 憑證申請失敗（請確認 $DOMAIN 已指向這台主機），目前先以 http 運作"
fi

if [ -z "$DOMAIN" ] && command -v ufw > /dev/null && ufw status | grep -q active; then
  ufw allow "$PORT"/tcp > /dev/null
fi

echo "$COMMIT" > "$APP/.deployed"

if [ "${BOOKING_AUTO_UPDATE:-}" = 1 ]; then
  echo "==> 設定自動更新（每 5 分鐘檢查一次）"
  cat > /usr/local/sbin/booking-update <<UPD
#!/usr/bin/env bash
# 分支有新 commit 時重新執行安裝腳本；紀錄：journalctl -u booking-update
set -euo pipefail
LATEST=\$(git ls-remote $REPO refs/heads/$BRANCH | cut -f1)
[ -n "\$LATEST" ] || exit 0
[ "\$LATEST" = "\$(cat $APP/.deployed 2>/dev/null)" ] && exit 0
echo "更新到 \$LATEST"
curl -fsSL "https://raw.githubusercontent.com/maxi9811207/dc4ni/\$LATEST/apps/booking/deploy/install.sh" | BOOKING_BRANCH=$BRANCH bash
UPD
  chmod 700 /usr/local/sbin/booking-update
  cat > /etc/systemd/system/booking-update.service <<UNIT
[Unit]
Description=Booking system auto update
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/booking-update
UNIT
  cat > /etc/systemd/system/booking-update.timer <<UNIT
[Unit]
Description=Check for booking system updates every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT
  systemctl daemon-reload
  systemctl enable -q --now booking-update.timer
fi

IP=$(curl -fsS -4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo
echo "完成！"
if [ -n "$DOMAIN" ]; then echo "網址：https://$DOMAIN/"; else echo "網址：http://$IP:$PORT/"; fi
echo "場主後台：登入後自動進入，或網址加上 #/admin"
echo "設定檔：$ENV_FILE（修改後執行 sudo systemctl restart booking）"
echo "資料：$APP/data（請定期備份）"
