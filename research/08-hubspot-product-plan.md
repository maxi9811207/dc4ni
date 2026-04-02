# HubSpot 生態系產品方向研究

> 產出日期：2026-04-02
> 前提：HubSpot 被選為最佳平台市集（0% 佣金、indie 中位 $23K MRR、29 萬付費客戶）

---

## 一、HubSpot 市集現況

### 基礎數據
- **2,000+ app**，2.5M 活躍安裝
- **1,251 個付費產品**，月交易額估計 **$6,960 萬**
- 平均每個付費產品 **$56K MRR**（$668K ARR）
- Indie 開發者中位數 **$23K MRR**（~150 客戶）
- 付費 app 的中位價格 **$263/月**，平均 **$2,008/月**
- HubSpot **不抽佣金**，開發者拿 100%

### 客群特性
HubSpot 的 29 萬付費客戶主要是 **行銷與銷售團隊** — 這是公司裡最有預算的部門。他們：
- 習慣為工具付費（HubSpot 本身就很貴）
- 有迫切的業務問題需要解決
- 願意為省時間的工具付 premium 價格

---

## 二、HubSpot 用戶最大的痛點

| 痛點 | 嚴重度 | 能否用 App 解決？ |
|------|--------|-----------------|
| **定價太貴，功能被鎖在高階方案** | 🔴 #1 | ✅ 做一個更便宜的替代品 |
| **報表功能受限（Pro 以下幾乎沒有）** | 🔴 | ✅ 報表/分析類 app |
| **學習曲線陡峭，操作複雜** | 🟡 | ⚠️ 難用 app 解決 |
| **Email 功能爛（追蹤不穩、常進 spam）** | 🟡 | ✅ Email 增強類 app |
| **Landing page builder 極差** | 🔴 | ✅ CMS 模組 |
| **Salesforce 整合問題（重複、sync 斷）** | 🟡 | ✅ 數據清洗/sync 類 |
| **高階自動化只有 Pro+** | 🔴 | ✅ 工作流增強類 app |

---

## 三、市集空白區域（Clayton Farr 數據）

### 幾乎零競爭的新類別
以下類別在 HubSpot 市集中 **幾乎沒有或完全沒有 app**：

| 類別 | 現有 app 數 | 需求等級 |
|------|-----------|---------|
| Brand Protection | 0-2 | 中 |
| Drop Shipping | 0-2 | 低 |
| E-Merchandising | 0-2 | 中 |
| Employee Engagement | 0-2 | 中 |
| Payroll | 0-2 | 中 |
| POS | 0-2 | 中 |
| Product Reviews | 0-2 | 高 |
| Shopping Cart | 0-2 | 中 |

### 高需求但 app 品質不佳的類別

| 類別 | 中位安裝數 | 現有問題 |
|------|----------|---------|
| Payment Gateways | 1,929 | 僅 2 個產品，極度供不應求 |
| Social Media | 649 | 14 個產品但品質參差 |
| Advertising | 578 | 11 個產品 |
| Webinar | 227 | 14 個產品 |

### AI 類 — 最大成長空間
- 僅 **11.41%** 的 listing 是 AI 相關
- AI agent 類 app 幾乎為零
- HubSpot 剛推出 Breeze AI、MCP server、Claude/ChatGPT connector，生態正在起飛

---

## 四、具體產品方向建議

### 方向 A：CRM 報表增強器（最推薦）⭐⭐⭐⭐⭐

#### 產品概念
**幫 HubSpot Starter/Free 用戶解鎖 Pro 等級的報表能力。**

HubSpot Free/Starter 的報表功能極度受限 — 自訂報表、儀表板、漏斗分析都要 Pro（$800+/月）。做一個 app，讓 $49-99/月的小團隊也能看到他們需要的數據。

#### 誰買？
- HubSpot Starter 用戶（買不起 Pro 但需要報表）
- 小型銷售/行銷團隊（5-20 人）
- 他們目前的替代方案：手動用 Excel，或花 $800/月升級 Pro

#### 怎麼被看到？
- HubSpot App Store 搜尋 "reporting" "analytics" "dashboard"
- 用戶在 HubSpot Community 抱怨報表受限時的自然發現

#### 定價
- Free: 3 個自訂報表
- Starter: $49/mo — 無限報表 + 基礎儀表板
- Pro: $99/mo — 進階分析 + 自動排程報告 + 匯出

#### 為什麼可行？
1. **痛點真實且強烈** — 報表受限是 #2 抱怨
2. **價格錨定清晰** — HubSpot Pro $800/mo vs 你的 $49-99/mo
3. **HubSpot 不會打你** — 這幫他們留住 Starter 用戶（否則他們會流失到競品）
4. **技術可行** — 用 HubSpot API 讀取 CRM 數據，前端渲染圖表
5. **中位價格 $263/mo** — 你定 $49-99 是市場低端，容易成交

#### 風險
- HubSpot 可能降低 Pro 門檻（但他們一直在漲價，不太可能）
- 需要深入了解 HubSpot CRM 數據模型

---

### 方向 B：AI 銷售助手（高潛力但競爭在升溫）⭐⭐⭐⭐

#### 產品概念
**一個嵌入 HubSpot 的 AI agent，自動分析 deal pipeline，預測哪些 deal 會贏/會掉，給出行動建議。**

#### 誰買？
- 銷售經理（需要 deal 洞察但 Gong 太貴 $100+/user/mo）
- 小型 B2B 銷售團隊

#### 定價
- $39-79/mo

#### 為什麼可行？
- AI agent 在 HubSpot 市集幾乎為零
- HubSpot 剛推出 Breeze AI 和 MCP，生態正起飛
- 銷售團隊為 deal intelligence 付費意願極高

#### 風險
- Gong、Clari 等大玩家可能做 HubSpot 整合
- HubSpot 自己的 Breeze 可能蠶食這個空間

---

### 方向 C：簡易自動化工作流（填補 Feature Gate）⭐⭐⭐⭐

#### 產品概念
**幫 Starter 用戶做到 Pro 才有的工作流自動化。** 例如：
- 自動 lead 分配（round robin）
- 自動 follow-up 提醒
- Deal stage 變更時自動通知
- 自動建立任務

#### 誰買？
- HubSpot Starter 用戶（自動化被鎖在 Pro）
- 小型銷售團隊不想升級但需要基本自動化

#### 定價
- $29-59/mo

#### 為什麼可行？
- 自動化是 HubSpot 最常見的升級原因
- 很多用戶只需要 3-5 個簡單自動化，不值得花 $800/mo 升 Pro
- 技術簡單 — 用 HubSpot webhook + 簡單邏輯

#### 風險
- 最接近 HubSpot 核心功能，平台風險最高

---

### 方向 D：CMS 模組包（低風險入門）⭐⭐⭐

#### 產品概念
**高品質的 HubSpot CMS 模組**（定價表、圖片輪播、進階 Footer、testimonial 區塊等）。

#### 誰買？
- 用 HubSpot CMS 的行銷團隊
- 不想請開發者但需要更好的網站元件

#### 定價
- 一次性 $29-99/模組，或 $19/mo 套餐

#### 為什麼可行？
- 現有模組品質很差（多數 < 10 安裝）
- HubSpot Landing page builder 是 #1 被罵的功能
- 定價表、Footer、Gallery 等模組有明確缺口
- 開發最簡單，適合快速驗證市場

#### 風險
- 一次性收入，不是 MRR（除非做套餐訂閱）
- 市場較小

---

### 方向 E：數據清洗/重複偵測工具 ⭐⭐⭐

#### 產品概念
**自動偵測和合併 HubSpot CRM 中的重複聯絡人/公司記錄。**

#### 誰買？
- 任何有 1,000+ 聯絡人的 HubSpot 用戶（幾乎所有人）
- 特別是 HubSpot-Salesforce 雙向 sync 的用戶（重複問題嚴重）

#### 定價
- $29-79/mo

#### 為什麼可行？
- 重複資料是普遍且持續的問題
- HubSpot 原生去重功能有限
- 用 AI 做模糊比對（fuzzy matching）可以做得比原生好

#### 風險
- 有幾個現有競品（Dedupely, Insycle）
- 需要處理大量數據，可能有效能挑戰

---

## 五、方向比較

| 維度 | A. 報表增強 | B. AI 銷售助手 | C. 自動化工作流 | D. CMS 模組 | E. 數據清洗 |
|------|-----------|--------------|---------------|------------|-----------|
| 痛點強度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 付費意願 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 競爭程度 | ⭐⭐⭐⭐ 少 | ⭐⭐⭐⭐⭐ 極少 | ⭐⭐⭐ 有些 | ⭐⭐⭐⭐ 少 | ⭐⭐⭐ 有些 |
| Claude Code 適配 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 平台風險 | ⭐⭐⭐⭐ 低 | ⭐⭐⭐ 中 | ⭐⭐ 高 | ⭐⭐⭐⭐⭐ 極低 | ⭐⭐⭐⭐ 低 |
| 收入天花板 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 被動程度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 啟動速度 | ⭐⭐⭐ 6-8 週 | ⭐⭐⭐ 6-8 週 | ⭐⭐⭐⭐ 4-6 週 | ⭐⭐⭐⭐⭐ 2-3 週 | ⭐⭐⭐ 6-8 週 |

---

## 六、最終推薦

### 策略：先 D 快速入場，再做 A 主力

```
Week 1-3:   方向 D — CMS 模組包（快速上架，學習 HubSpot 生態）
Week 4-10:  方向 A — CRM 報表增強器（主力產品，$49-99/mo MRR）
Week 11+:   根據數據決定是否加做 B 或 C
```

**為什麼這個順序？**

1. **CMS 模組是最快的入場票** — 2-3 週可上架，風險最低，先熟悉 HubSpot 生態和審核流程
2. **報表增強器是真正的搖錢樹** — 痛點最強、價格錨定最清晰（$49 vs $800）、收入天花板高
3. **做了 D 和 A 之後，你會對 HubSpot 用戶有第一手理解**，再決定 B 或 C

### 收入預估

| 時間 | 產品 | 預估月收 (USD) | 預估月收 (TWD) |
|------|------|---------------|---------------|
| Month 1 | CMS 模組 | $100-500 | 3,000-15,000 |
| Month 3 | CMS + 報表 app | $500-2,000 | 15,000-60,000 |
| Month 6 | 報表 app 為主 | $2,000-5,000 | 60,000-150,000 |
| Month 12 | 組合產品 | $5,000-15,000 | 150,000-450,000 |

（基於 HubSpot indie 中位 $23K MRR，上述預估偏保守）

---

## 研究來源

- [Clayton Farr - HubSpot Marketplace by the $ Numbers](https://claytonfarr.com/hubspot-marketplace)
- [Indie Hackers - Indies making $280K+ ARR on HubSpot](https://www.indiehackers.com/post/indies-are-making-280k-arr-on-hubspot-in-2024-608dc3fab2)
- [HubSpot - Building Apps in 2025](https://gadget.dev/blog/building-hubspot-apps-in-2025-whats-new-whats-changing-and-how-to-get-started)
- [HubSpot - App Categories](https://developers.hubspot.com/docs/apps/developer-platform/list-apps/listing-your-app/understand-app-categories)
- [HubSpot - Thinking Outside the Box](https://developers.hubspot.com/blog/thinking-outside-the-box-building-creative-apps-for-hubspots-marketplace)
- [HubSpot Community - Pain Points](https://community.hubspot.com/t5/CRM/What-are-the-biggest-pain-points-in-your-current-customer/td-p/1138830)
- [tldv - Honest HubSpot Review 2026](https://tldv.io/blog/hubspot-review/)
- [EngageBay - HubSpot Pros and Cons 2026](https://www.engagebay.com/blog/hubspot-pros-and-cons/)
- [HubSpot - Marketplace 2,000 Apps Milestone](https://community.hubspot.com/t5/Releases-and-Updates/2-000-Apps-2-5M-Active-Installs/ba-p/1209474)
- [Studio Nope - Best HubSpot Modules 2026](https://www.studionope.com/blog/best-hubspot-marketplace-modules-2026)
