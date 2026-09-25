#!/usr/bin/env bash
# 在主機上執行：把約課系統部署到 /opt/booking，並用 Docker 啟動
# 用法：sudo bash deploy/deploy.sh   （在 apps/booking 目錄內執行）
set -euo pipefail

TARGET=/opt/booking
mkdir -p "$TARGET"
rsync -a --delete --exclude data --exclude .env --exclude web/node_modules --exclude server/static ./ "$TARGET"/
cd "$TARGET"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已建立 $TARGET/.env，請先修改場主手機與密碼後再執行一次。"
  exit 1
fi

docker compose up -d --build
sleep 3
curl -fsS http://127.0.0.1:8100/api/venue > /dev/null && echo "約課系統已啟動：http://127.0.0.1:8100/"
