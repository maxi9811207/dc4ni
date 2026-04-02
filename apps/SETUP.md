# HubSpot App 開發環境設定指南

## 你需要做的（人為步驟，約 30 分鐘）

### Step 1：建立 HubSpot 開發者帳號

1. 前往 https://developers.hubspot.com/
2. 點擊 "Create a developer account"
3. 用你的 Email 註冊（不需要信用卡）
4. 完成帳號驗證

### Step 2：建立測試帳號（Sandbox）

1. 登入開發者帳號
2. 點選左側選單 "Test accounts"
3. 點 "Create test account"
4. 這會給你一個有完整 Enterprise 功能的測試環境
5. 記下你的 **Portal ID**（在帳號設定中可以看到）

### Step 3：認證 CLI

在 terminal 執行：

```bash
cd ~/Desktop/code/money/apps/portal-audit
hs init
```

這會打開瀏覽器讓你登入。選擇你的開發者帳號，授權即可。
完成後會建立 `hubspot.config.yml`（已在 .gitignore 中）。

### Step 4：建立 App

在 HubSpot 開發者後台：

1. 進入 "Apps" → "Create app"
2. App 名稱：`Portal Audit`
3. 在 "Auth" tab 設定：
   - Redirect URL: 先填 `https://localhost:3000/oauth/callback`
   - 勾選以下 scopes：
     - `crm.objects.contacts.read`
     - `crm.objects.companies.read`
     - `crm.objects.deals.read`
     - `crm.lists.read`
     - `forms`
     - `automation`
     - `content`
4. 記下 **Client ID** 和 **Client Secret**

重複以上步驟建立第二個 App：`Data Quality Pro`
- Scopes:
  - `crm.objects.contacts.read`
  - `crm.objects.contacts.write`
  - `crm.objects.companies.read`
  - `crm.objects.companies.write`
  - `crm.schemas.read`

### Step 5：上傳 & 測試

```bash
# Portal Audit
cd ~/Desktop/code/money/apps/portal-audit
hs project upload
hs project dev   # 開發模式，會自動重新載入

# Data Quality Pro
cd ~/Desktop/code/money/apps/data-quality
hs project upload
hs project dev
```

### Step 6：在測試帳號中安裝 App

1. 在 HubSpot 測試帳號中，前往 Settings → Integrations → Connected apps
2. 安裝你剛才建立的 App
3. 前往任一 Contact 記錄，應該會看到新的 Tab

---

## 專案結構

```
apps/
├── portal-audit/                  # App 1: Portal 審計工具
│   ├── hsproject.json
│   └── src/app/
│       ├── app.json               # App 設定 + scopes
│       ├── extensions/
│       │   ├── audit-card.json    # UI Extension 定義
│       │   └── audit-card/
│       │       └── AuditCard.jsx  # 前端 React 元件
│       └── app.functions/
│           ├── serverless.json    # Serverless function 路由
│           └── runPortalAudit.js  # 後端核心邏輯
│
├── data-quality/                  # App 2: 數據品質工具（主力產品）
│   ├── hsproject.json
│   └── src/app/
│       ├── app.json
│       ├── extensions/
│       │   ├── dedup-card.json
│       │   └── dedup-card/
│       │       └── DedupCard.jsx  # 三個 Tab：去重、清洗、健康分數
│       └── app.functions/
│           ├── serverless.json
│           ├── scanDuplicates.js    # 掃描重複聯絡人
│           ├── mergeDuplicates.js   # 合併重複記錄
│           ├── runDataCleanup.js    # 數據清洗（名字大小寫、Email、電話）
│           └── calculateHealthScore.js  # CRM 健康分數
│
└── SETUP.md                       # 本文件
```

---

## 費用

| 項目 | 費用 |
|------|------|
| HubSpot 開發者帳號 | 免費 |
| HubSpot 測試帳號 | 免費 |
| App 上架 | 免費 |
| HubSpot 佣金 | **0%** |
| Serverless Functions 託管 | HubSpot 免費提供 |
| **總計** | **$0/月** |

---

## 上架 Marketplace 前的 Checklist

- [ ] App 在測試帳號中正常運作
- [ ] 建立 Privacy Policy 頁面（可用免費的 GitHub Pages）
- [ ] 建立 Terms of Service 頁面
- [ ] 準備 App logo（512x512 PNG）
- [ ] 準備 3-5 張截圖
- [ ] 撰寫 App 描述（英文）
- [ ] 提交 HubSpot 審核（2-4 週）
