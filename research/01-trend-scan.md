# Loop 1 — 模式掃描 (Trend Scan)

> 產出日期：2026-04-02
> 約束條件：Claude Code 可建置維運 / 月成本 < TWD 10,000 / 全自動 / 不露臉 / 無需客服

---

## 一、掃描方法

透過 Web 搜尋 2024-2026 年被動收入趨勢、indie hacker 成功案例、AI 自動化商業模式、Micro-SaaS 市場報告，並以約束條件做硬過濾。

---

## 二、符合約束的被動收入模式清單

### 模式 A：Micro-SaaS（AI 驅動的垂直小工具）

| 項目 | 內容 |
|------|------|
| **描述** | 針對特定 niche 解決一個痛點的 SaaS 訂閱制產品（如 AI 產品描述生成器、AI 評論分析器、AI 記帳工具） |
| **收入模型** | 月訂閱制 $9-49/mo per user |
| **自動化可行性** | ⭐⭐⭐⭐ — 自助註冊、Stripe 自動扣款、AI 自動處理，幾乎零人工 |
| **預估月收入範圍** | TWD 3,000 - 150,000+（取決於 niche 和獲客） |
| **啟動時間** | 4-8 週 MVP |
| **月維運成本** | TWD 500-3,000（VPS + Domain + API calls） |
| **Claude Code 適配度** | ✅ 高 — 全端可由 Claude Code 完成 |

**市場數據：** Micro-SaaS 市場 2024 年 $15.7B，年增 30%，預計 2030 年達 $59.6B。

---

### 模式 B：API-as-a-Product（API 即產品）

| 項目 | 內容 |
|------|------|
| **描述** | 建置一個有價值的 REST API，提供數據處理、轉換、AI 推論等服務，透過 pay-per-call 或訂閱制變現 |
| **收入模型** | Freemium + 訂閱制 / Pay-per-call / Credit-based |
| **自動化可行性** | ⭐⭐⭐⭐⭐ — API 天然就是無人值守的產品 |
| **預估月收入範圍** | TWD 1,000 - 100,000+ |
| **啟動時間** | 2-4 週 |
| **月維運成本** | TWD 300-2,000（Serverless / VPS） |
| **Claude Code 適配度** | ✅ 極高 — 純後端，最適合 Claude Code 開發 |

**分發平台：** RapidAPI、Apify Marketplace、Zuplo 等可直接上架。

---

### 模式 C：Programmatic SEO 內容站 + 聯盟行銷/廣告

| 項目 | 內容 |
|------|------|
| **描述** | 用資料庫 + 模板批量生成數千個 SEO 頁面，攻佔長尾關鍵字，透過廣告(AdSense)或聯盟行銷變現 |
| **收入模型** | 廣告收入 + 聯盟行銷佣金 |
| **自動化可行性** | ⭐⭐⭐⭐ — 建置後自動生成頁面，SEO 流量被動進來 |
| **預估月收入範圍** | TWD 3,000 - 80,000+ |
| **啟動時間** | 4-8 週（但 SEO 見效需 3-6 個月） |
| **月維運成本** | TWD 300-1,500（Hosting + Domain） |
| **Claude Code 適配度** | ✅ 高 — 站點生成、模板系統都可由 Claude Code 完成 |

**風險警告：** Google 2025 年 12 月核心更新嚴打低品質 AI 內容，需確保數據獨特性和頁面價值。成功案例 6 個月內流量增 200-500%。

---

### 模式 D：數位產品（模板/工具/素材包）

| 項目 | 內容 |
|------|------|
| **描述** | 製作 Notion 模板、Excel 工具、設計素材、程式碼片段、Prompt 包等，上架 Gumroad/Etsy/自有站販售 |
| **收入模型** | 一次性購買 $5-50 / 產品 |
| **自動化可行性** | ⭐⭐⭐⭐⭐ — 平台處理一切，零客服 |
| **預估月收入範圍** | TWD 1,000 - 50,000 |
| **啟動時間** | 1-2 週 |
| **月維運成本** | TWD 0-500（平台抽成為主） |
| **Claude Code 適配度** | ⚠️ 中 — Claude Code 可產模板，但設計類需額外工具 |

---

### 模式 E：自動化工作流模板販售（n8n/Make.com）

| 項目 | 內容 |
|------|------|
| **描述** | 建立解決特定問題的自動化工作流，包裝成模板在專屬市集販售 |
| **收入模型** | 一次性購買 $10-200 / 模板 |
| **自動化可行性** | ⭐⭐⭐⭐ — 建好後掛在市集被動售出 |
| **預估月收入範圍** | TWD 3,000 - 60,000 |
| **啟動時間** | 2-4 週 |
| **月維運成本** | TWD 0-500 |
| **Claude Code 適配度** | ⚠️ 中 — Claude Code 可寫 JSON workflow，但需人工在平台測試 |

**實際案例：** 有創作者 5 個 n8n 模板月入 $3,200 USD，每週僅花 2 小時維護。

**平台：** AutomationWorkflows.io、HaveWorkflow.com、n8nMarket.com、Gumroad。

---

### 模式 F：Micro-SaaS 包裝自動化工作流（Workflow-as-SaaS）

| 項目 | 內容 |
|------|------|
| **描述** | 用 n8n 等自動化工具建後端邏輯，前端包一層簡單 UI，以訂閱制販售「結果」而非「工作流」 |
| **收入模型** | 月訂閱 $29-199/mo |
| **自動化可行性** | ⭐⭐⭐⭐ — 後端全自動，前端自助服務 |
| **預估月收入範圍** | TWD 5,000 - 100,000+ |
| **啟動時間** | 4-6 週 |
| **月維運成本** | TWD 1,000-5,000 |
| **Claude Code 適配度** | ✅ 高 — 前後端都可由 Claude Code 完成 |

**概念：** 這是「自動化套利」— 不賣工具，賣工具產出的結果（如自動產出的 lead list、市場報告、SEO 分析）。

---

### 模式 G：Chrome Extension / 瀏覽器擴充

| 項目 | 內容 |
|------|------|
| **描述** | 開發解決特定痛點的 Chrome Extension，透過 Freemium 訂閱變現 |
| **收入模型** | Freemium + 訂閱 $3-15/mo |
| **自動化可行性** | ⭐⭐⭐⭐ — Chrome Web Store 自動分發 |
| **預估月收入範圍** | TWD 2,000 - 80,000+ |
| **啟動時間** | 2-4 週 |
| **月維運成本** | TWD 0-1,500 |
| **Claude Code 適配度** | ✅ 高 — JS/TS 為主，Claude Code 擅長 |

---

### 模式 H：開源 + Premium（Open Core）

| 項目 | 內容 |
|------|------|
| **描述** | 建立一個開源工具吸引使用者，透過 Premium 版/託管版/進階功能變現 |
| **收入模型** | 託管版訂閱 / 進階功能一次性付費 |
| **自動化可行性** | ⭐⭐⭐ — 開源社群可能帶來 issue/PR 需處理 |
| **預估月收入範圍** | TWD 0 - 100,000+（高變異性） |
| **啟動時間** | 4-8 週 |
| **月維運成本** | TWD 500-3,000 |
| **Claude Code 適配度** | ✅ 高 — 可完全用 Claude Code 開發 |

**風險：** 開源社群經營非完全被動，可能需回應 issue。

---

## 三、已排除的模式（不符合約束）

| 模式 | 排除原因 |
|------|----------|
| 個人品牌 / KOL | 需露臉、持續內容產出 |
| 線上課程 | 需錄影、偶爾客服 |
| 自由接案 / 顧問 | 本質是主動收入 |
| Drop shipping | 需處理客服與退貨 |
| Podcast / YouTube | 需持續產出、非全被動 |
| 社群媒體經營 | 需每日投入 |
| 實體商品 | 需物流、客服 |

---

## 四、初步觀察

1. **最高 Claude Code 適配度的方向：** API-as-a-Product（模式 B）和 Micro-SaaS（模式 A/F）— 純程式碼產品，Claude Code 可端到端完成。
2. **最快啟動的方向：** 數位產品（模式 D）1-2 週，API-as-a-Product（模式 B）2-4 週。
3. **最高被動程度的方向：** API-as-a-Product 和數位產品 — 上架後幾乎零維護。
4. **最高收入天花板的方向：** Micro-SaaS（模式 A/F）— 訂閱制複利效應。
5. **風險最低的方向：** 數位產品（模式 D）— 零成本啟動，失敗代價極低。

---

## 五、研究來源

- [Indie Hackers - Autonomous Business](https://www.indiehackers.com/post/tech/growing-a-fully-autonomus-business-to-a-500k-mo-in-3-months-diZ8gkqMHm0CvEsc7Pfo)
- [DEV Community - Passive Income for Automation Developers 2026](https://dev.to/bishal_paul_ai/passive-income-for-automation-developers-in-2026-1a48)
- [Medium - 10 Profitable Micro-SaaS Ideas 2026](https://medium.com/the-money-guide/10-boring-micro-saas-ideas-that-earn-2-000-month-without-the-ai-hype-af1b6ef53109)
- [Lovable - Micro SaaS Ideas for Solopreneurs 2026](https://lovable.dev/guides/micro-saas-ideas-for-solopreneurs-2026)
- [Medium - 15 AI Micro-SaaS Ideas Ranked 2026](https://medium.com/@vicki-larson/in15-ai-micro-saas-ideas-ranked-by-launch-speed-market-saturation-2026-guide-96d4820a4ee4)
- [Zuplo - Turning APIs into Revenue](https://zuplo.com/learning-center/turning-apis-into-passive-income-revenue-stream)
- [Zuplo - API Monetization Ultimate Guide 2026](https://zuplo.com/blog/api-monetization-ultimate-guide)
- [Backlinko - Programmatic SEO 2026](https://backlinko.com/programmatic-seo)
- [Jasmine Directory - Programmatic SEO Guide 2026](https://www.jasminedirectory.com/blog/the-ultimate-guide-to-programmatic-seo-in-2026/)
- [Medium - n8n Automations $3,200/Month](https://medium.com/write-a-catalyst/i-built-5-n8n-automations-that-generate-3-200-month-passively-72e2a3050e17)
- [AutomationWorkflows.io](https://automationworkflows.io/)
- [Cory Zue - Solopreneur](https://www.coryzue.com/writing/solopreneur/)
- [Vocus - 2026 AI 賺錢被動收入策略](https://vocus.cc/article/695a5236fd89780001532d8f)
- [啟程教育 - 2026 網路賺錢](https://startingedu.com/the-way-to-makemoneyonline/)
