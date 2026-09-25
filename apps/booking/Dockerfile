# 階段一：打包前端
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npx vite build --outDir /static --emptyOutDir

# 階段二：後端＋靜態檔
FROM python:3.11-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/app.py server/dupr.py server/reports.py ./
COPY --from=web /static ./static
ENV BOOKING_DATA_DIR=/data
VOLUME /data
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100", "--proxy-headers"]
