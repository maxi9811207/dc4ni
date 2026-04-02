# Loop 4 — 商業設計 (Business Model)

> 產出日期：2026-04-02
> 引用：Loop 3 驗證結論 — API-as-a-Product 為主力方向，Workflow-as-SaaS 為 Phase 2

---

## 一、商業模型畫布

### Value Proposition（價值主張）
**為開發者和中小企業提供即插即用的 Niche AI/Data API，解決他們不想自建的特定功能需求。**

核心價值：
- 開發者不需要自己訓練模型、管理基礎設施
- 一行程式碼整合，即時獲得 AI 能力或數據處理能力
- Freemium 免費試用，付費按量計價，無長期綁約

### Customer Segments（客戶區隔）
| 客群 | 需求 | 付費能力 | 優先級 |
|------|------|----------|--------|
| 獨立開發者 / Side project | 快速整合特定功能 | $0-19/mo | 中（量大但 ARPU 低） |
| 中小 SaaS 公司 | 避免自建特定功能 | $19-99/mo | **高（核心客群）** |
| 電商賣家 / 行銷人 | 數據分析、內容生成 | $9-49/mo | 高 |
| Agency / 接案公司 | 批量處理客戶需求 | $49-199/mo | 中高 |

### Channels（通路）
| 通路 | 成本 | 效果 | 優先級 |
|------|------|------|--------|
| RapidAPI Marketplace | 25% 佣金 | 自帶流量 | **Phase 1 首選** |
| Apify Marketplace | 佣金制 | 爬蟲/數據類流量 | Phase 1 |
| 自有 Landing Page + SEO | TWD 0-500 | 長期自有流量 | Phase 2 |
| Dev.to / Medium 技術文章 | 免費 | 開發者信任 | 持續 |
| Product Hunt Launch | 免費 | 爆發式曝光 | Phase 2 上線時 |
| GitHub README 推廣 | 免費 | 開發者社群 | 持續 |

### Revenue Streams（收入來源）

**三層定價模型：**

```
Free Tier:     100 calls/月 — $0
               ↓ 自然轉換
Pro Tier:      5,000 calls/月 — $9/mo
               ↓ 用量成長
Business Tier: 50,000 calls/月 — $29/mo
               ↓ 大量需求
Enterprise:    自訂 — $99+/mo
```

**收入組合預估（12 個月後）：**
- 3-5 個 API 產品上架
- 每個 API 50-200 付費用戶
- ARPU $15-25/mo
- 月收入目標：TWD 30,000-80,000

### Key Resources（核心資源）
- Claude Code（開發 + 維運）
- 產品總監經驗（方向判斷、產品設計）
- API 分發平台帳號
- Stripe 帳號（支付處理）
- 雲端基礎設施（Railway/Fly.io）

### Key Activities（核心活動）

**建置期（一次性，4-8 週）：**
- 市場研究 → 選定 3-5 個 API 方向
- Claude Code 開發 API
- 撰寫 API 文件
- 上架 Marketplace
- 設定監控告警

**維運期（每週 < 1 小時）：**
- 監控 API 運行狀態（自動化告警）
- 查看收入報表
- Claude Code 處理 bug fix（如有）

### Key Partners（核心合作夥伴）
- RapidAPI / Apify（分發平台）
- Stripe（支付處理）
- Railway / Fly.io（基礎設施）
- Claude Code（開發維運）

### Cost Structure（成本結構）

| 項目 | 月費 (TWD) | 備註 |
|------|-----------|------|
| Railway Hobby | 150 ($5) | API 託管 |
| Domain | 30 ($1) | 年繳攤提 |
| Stripe | 交易 2.9%+$0.30 | 變動成本 |
| RapidAPI 佣金 | 收入 25% | 變動成本 |
| Claude API（如需） | 0-1,500 | 視 API 是否呼叫 LLM |
| **固定成本合計** | **~200-300** | |
| **含變動成本上限** | **~3,000-5,000** | 依收入規模 |

**結論：月成本遠低於 TWD 10,000 預算上限。**

---

## 二、API 產品方向建議

### 選擇標準
1. 有付費意願的使用場景
2. 現有解決方案不夠好或太貴
3. Claude Code 可端到端實作
4. 不需要大量算力或特殊硬體
5. 數據/功能有一定獨特性

### 推薦的 5 個 API 方向

#### API 1：結構化數據擷取 API（Structured Data Extractor）
- **功能：** 輸入任意非結構化文本（email、PDF 內容、網頁文字），輸出結構化 JSON
- **場景：** 發票/收據解析、履歷解析、產品資訊擷取
- **獨特性：** 可針對特定 schema 客製化，比通用 LLM 更精準
- **技術：** Claude API + 結構化 output
- **定價：** Free 50 calls → Pro $9/mo → Business $29/mo

#### API 2：多語言 SEO 元數據生成器（SEO Meta Generator）
- **功能：** 輸入 URL 或內容，自動生成 title/description/keywords/OG tags，支持多語言
- **場景：** 電商賣家、部落客、SaaS 公司
- **獨特性：** 不只生成，還根據最新 SEO 最佳實踐評分和建議
- **技術：** 爬蟲 + AI 分析
- **定價：** Free 20 calls → Pro $9/mo → Business $29/mo

#### API 3：競品價格監控 API（Price Monitor）
- **功能：** 追蹤指定商品/服務的價格變動，回傳歷史價格 + 趨勢分析
- **場景：** 電商賣家定價策略、採購決策
- **獨特性：** 提供趨勢分析而非純爬蟲數據
- **技術：** 排程爬蟲 + 數據分析
- **定價：** Free 5 products → Pro $19/mo → Business $49/mo

#### API 4：內容品質評分 API（Content Quality Scorer）
- **功能：** 分析文章/網頁內容的 SEO 品質、可讀性、AI 偵測分數
- **場景：** 內容行銷團隊、SEO agency
- **獨特性：** 多維度評分（SEO + 可讀性 + AI 偵測 + 情感分析）
- **技術：** NLP 分析 + AI
- **定價：** Free 30 calls → Pro $9/mo → Business $29/mo

#### API 5：商業名稱/品牌產生器 API（Brand Name Generator）
- **功能：** 輸入行業/關鍵字，產生品牌名稱 + 檢查 domain 可用性 + 商標初篩
- **場景：** 創業者、行銷 agency
- **獨特性：** 整合 domain check + 商標搜尋，一站式完成
- **技術：** AI 生成 + Whois API + 商標資料庫
- **定價：** Free 10 calls → Pro $9/mo → Business $19/mo

---

## 三、定價策略

### 核心原則
- **Freemium 轉換模式：** 免費層足夠試用但不足以生產使用
- **按月訂閱 + 超額按量計費：** 基礎保底收入 + 上行空間
- **年繳折扣 20%：** 增加客戶留存

### 定價甜蜜點
- 根據市場研究，$9-29/mo 是獨立開發者/中小企業最容易接受的區間
- Free → $9 的轉換率通常 2-5%
- $9 → $29 的升級率通常 10-20%（用量自然成長）

---

## 四、技術架構概要

```
┌─────────────────────────────────────────────┐
│           Distribution Layer                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ RapidAPI │  │  Apify   │  │ Self-host │ │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘ │
│       │              │              │        │
│       └──────────────┼──────────────┘        │
│                      ▼                       │
│  ┌──────────────────────────────────────┐   │
│  │         API Gateway (自建)           │   │
│  │  • Rate limiting                      │   │
│  │  • API key 管理                       │   │
│  │  • 用量追蹤                           │   │
│  │  • 快取層                             │   │
│  └──────────────────┬───────────────────┘   │
│                     ▼                        │
│  ┌──────────────────────────────────────┐   │
│  │         API Services                  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐   │   │
│  │  │ API 1  │ │ API 2  │ │ API 3  │   │   │
│  │  └────────┘ └────────┘ └────────┘   │   │
│  └──────────────────┬───────────────────┘   │
│                     ▼                        │
│  ┌──────────────────────────────────────┐   │
│  │         External Services             │   │
│  │  • Claude API (AI 推論)               │   │
│  │  • Redis (快取)                       │   │
│  │  • PostgreSQL (數據存儲)              │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 技術選型

| 層級 | 選擇 | 理由 |
|------|------|------|
| 語言 | Node.js (TypeScript) | Claude Code 最擅長、生態系成熟 |
| 框架 | Hono / Fastify | 輕量、高效能、適合 API |
| 託管 | Railway ($5/mo) | 便宜、自動 sleep、開發者友善 |
| 資料庫 | PostgreSQL (Railway 內建) | 免費附帶、可靠 |
| 快取 | Redis (Upstash free tier) | Serverless Redis、免費 10K cmd/day |
| AI | Claude API / OpenAI API | 按需使用、no fixed cost |
| 支付 | Stripe | 業界標準、自動化計費 |
| 監控 | BetterStack (free tier) | Uptime monitoring + 告警 |
| Domain | Cloudflare ($10/yr) | 便宜 + CDN + DNS |

### 成本控制設計
- Railway auto-sleep：無流量時零成本
- Redis cache：減少重複 AI 呼叫（最大成本來源）
- Rate limiting：防止濫用
- 快取常見請求的結果：降低 Claude/OpenAI API 成本

---

## 五、MVP 定義

### MVP 做什麼
- 先做 1-2 個 API（建議從 API 1 或 API 2 開始）
- 完整的 API endpoint + 文件
- Freemium + Pro 兩層定價
- 上架 RapidAPI
- 基本監控告警

### MVP 不做什麼
- ❌ 不建自有前端 Dashboard（Phase 2）
- ❌ 不做 Enterprise 方案
- ❌ 不建自有支付系統（用 RapidAPI 內建）
- ❌ 不做多 region 部署
- ❌ 不做複雜的 analytics

### MVP 成功指標
- 上線後 30 天內有 50+ 免費用戶
- 上線後 60 天內有 5+ 付費用戶
- API uptime > 99%
- 每週維護時間 < 1 小時

---

## 六、風險清單 + 緩解方案

| 風險 | 嚴重度 | 機率 | 緩解方案 |
|------|--------|------|----------|
| API 沒人用（PMF 風險） | 高 | 中 | 同時上架多個 API 分散風險；先上最有把握的 |
| RapidAPI 平台風險 | 中 | 低 | 同時在多個平台上架；Phase 2 建自有通路 |
| AI API 成本失控 | 中 | 中 | 強快取策略；rate limit；成本即時監控 |
| 競品複製 | 中 | 中 | 持續迭代、深耕 niche、建立口碑 |
| 第三方 API 變動 | 低 | 中 | 抽象層設計，便於切換供應商 |
| Claude Code 維運能力限制 | 中 | 低 | 保持架構簡單；選擇成熟可靠的技術棧 |

---

## 七、Phase 2 演進路線（API → SaaS）

當 API 月收達 TWD 30,000+ 時，考慮：

1. **建自有 Dashboard** — 用戶可自助管理 API key、查看用量
2. **包裝為 Workflow-as-SaaS** — 把最成功的 API 加上 UI，賣「結果」而非 API call
3. **Chrome Extension** — 讓非技術用戶也能使用 API 能力
4. **白標服務** — 讓其他 SaaS 公司 resell 你的 API 能力

---

## 研究來源

- [RapidAPI - Popular APIs](https://rapidapi.com/collection/popular-apis)
- [RapidAPI - Sell APIs Guide](https://rapidapi.com/guides/sell-apis-to-earn-money-as-a-developer)
- [Apify - Best RapidAPI Alternatives 2026](https://blog.apify.com/best-rapidapi-alternatives/)
- [Railway Pricing 2026](https://www.srvrlss.io/provider/railway/)
- [Fly.io vs Railway 2026](https://thesoftwarescout.com/fly-io-vs-railway-2026-which-developer-platform-should-you-deploy-on/)
- [Nordic APIs - 9 API Monetization Models](https://nordicapis.com/9-types-of-api-monetization-models/)
- [Orbilontech - API Economy 2026](https://orbilontech.com/api-economy-2026-business-guide/)
