# 平台 App Marketplace 全面比較研究

> 產出日期：2026-04-02
> 目的：找出最有機會賺到錢的平台市集

---

## 一、掃描範圍

搜集了 **49 個** App Marketplace，涵蓋電商、CRM、協作、設計、自動化、客服、財務、開發工具等領域。以下針對有明確開發者變現機制的平台做深度比較。

---

## 二、核心比較表（有開發者收入數據的平台）

| 平台 | 平台營收 | App 數量 | 平台佣金 | Indie 中位收入 | Indie 頂部收入 | 用戶付費習慣 | Claude Code 適配 |
|------|---------|---------|---------|--------------|--------------|-------------|----------------|
| **HubSpot** | $3.1B/yr | 2,000+ | **0%** | **$23K MRR** | $280K+ ARR | ✅ 極強（行銷/銷售預算） | ✅ |
| **Shopify** | $8.8B/yr | 14,800+ | 0%（首$1M）→15% | $725/mo | $49M/mo (Klaviyo) | ✅ 強（商家慣付費） | ✅ |
| **monday.com** | $1.2B/yr | 850+ | 0%（首$200K）→15% | 不明 | $30K MRR | ✅ 強 | ✅ |
| **Atlassian** | $4.8B/yr | 6,000+ | 0%（Forge 首$1M）→17% | 不明 | 數百萬 ARR | ✅ 強（企業IT） | ⚠️ 中（Forge 學習曲線） |
| **Salesforce** | $37.9B/yr | 6,000+ | 15% | 不明 | 數百萬 ARR | ✅ 極強（企業預算） | ⚠️ 低（Apex/LWC 生態） |
| **Slack** | $1.3B/yr | 3,500+ | **0%** | $2.5K/mo | $25K/mo | ⚠️ 中 | ✅ |
| **Zendesk** | $4.0B/yr | 1,500+ | 有（比例不明） | 不明 | 不明 | ✅ 強 | ✅ |
| **Zoom** | $4.8B/yr | 1,500+ | ~15% | 不明 | 不明 | ⚠️ 中 | ✅ |
| **Figma** | $1.0B/yr | 數百 | 15% | 不明 | 不明 | ⚠️ 弱（設計師不太付費） | ⚠️ 低 |
| **Framer** | $50M/yr | 280+ | **0%** | $500-2K/mo | $36K/mo | ⚠️ 弱（模板為主） | ⚠️ 低（設計導向） |
| **WordPress** | 生態>$19B | 60,000+ | 0%（自售）/30-70%（CodeCanyon） | $500/mo | $35M/yr (Yoast) | ✅ 強 | ✅ |
| **Bubble** | $74M/yr | 7,000+ | 有 | <$100/mo | $4M/yr (Zeroqode) | ❌ 弱 | ⚠️ 中 |
| **Chrome Web Store** | N/A | 200K+ | 0% | 不明 | $540K/yr (Eightify) | ⚠️ 中 | ✅ |
| **Canva** | $3.5B/yr | 1,000+ | 創新基金制 | 不明 | 不明 | ⚠️ 弱 | ⚠️ 低 |

---

## 三、深度分析：Top 5 最有機會的市集

### 🥇 #1 — HubSpot App Marketplace

**為什麼是第一名：**

| 維度 | 評估 |
|------|------|
| **佣金** | **0%** — HubSpot 完全不抽成，你拿 100% |
| **Indie 實際收入** | 中位 indie app 月入 **$23K MRR（$27.6 萬/年）**，只需 ~150 客戶 |
| **客群付費力** | HubSpot 用戶是行銷/銷售團隊 — 公司裡**最有預算**的部門 |
| **競爭程度** | 僅 2,000 app（vs Shopify 14,800）— 還有大量空白 |
| **分發能力** | 商家在 HubSpot 內主動搜尋解決方案 |
| **平台成長** | 營收 $3.1B（+19% YoY），29 萬付費客戶持續增長 |

**關鍵洞察（Clayton Farr 分析）：**
> HubSpot 市集月交易額估計 **$6,960 萬**，僅 1,251 個付費產品。很多產品**做得不好也在賺錢** — 只要找到有價值的痛點。

**風險：**
- HubSpot 生態學習成本（需了解 CRM/行銷自動化領域）
- 客群是 B2B，銷售週期可能較長
- 需要一定領域知識判斷做什麼

**Claude Code 適配度：** ✅ HubSpot App 用 Node.js + React，完全在 Claude Code 能力範圍

---

### 🥈 #2 — Shopify App Store

**為什麼排第二：**

| 維度 | 評估 |
|------|------|
| **佣金** | 首 $1M 生涯收入 0%，之後 15% |
| **市場規模** | 476 萬商家，全球最大電商平台之一 |
| **客群付費力** | 商家習慣付費，平均每店 3.1 個 app |
| **分發能力** | App Store 搜尋極強，商家主動找工具 |
| **競爭程度** | 14,800 app 較擁擠，但 98% 商家缺特定類別工具 |

**為什麼不是第一：**
- 中位 app 月收僅 $725（vs HubSpot $23K）
- 54.53% app 月收 < $1,000 — Winner-takes-most
- 前 3 個月中位收入是 **$0**
- 小商家付費能力有限（$9-29/mo 區間）

**適合做什麼：**
- 留存工具（40% 商家缺）
- 評價收集（93.9% 商家缺）
- SMS marketing（88.4% 高流量店缺）

---

### 🥉 #3 — monday.com App Marketplace

**為什麼排第三：**

| 維度 | 評估 |
|------|------|
| **佣金** | 首 $200K 生涯收入 0%，之後 15% |
| **市場規模** | 25 萬+ 企業客戶，87% 企業帳號裝過 app |
| **Indie 頂部收入** | 非技術創辦人幾個月內達 $30K MRR |
| **競爭程度** | 僅 850 app — **非常早期，空白多** |
| **平台成長** | 營收 $1.2B（+19% YoY），高速成長中 |

**優勢：** 市集還非常年輕，850 app 意味著大量未被滿足的需求。非技術創辦人都能做到 $30K MRR，技術產品總監+Claude Code 應該更有優勢。

**風險：** 市場較小、monday.com 用戶偏專案管理，付費意願不如行銷/銷售部門。

---

### #4 — Atlassian Marketplace（Jira/Confluence）

| 維度 | 評估 |
|------|------|
| **佣金** | Forge 首 $1M 0%（2026 新政策），之後 17% |
| **市場規模** | 全球最大開發團隊工具，企業級客戶 |
| **競爭** | 6,000 app，較成熟 |
| **技術門檻** | Forge 框架有學習曲線 |

**優勢：** 企業客戶付費力極強，新 Forge 0% 佣金是機會窗口。
**劣勢：** 技術棧不夠通用（Forge），Claude Code 適配度中等。

---

### #5 — Slack App Directory

| 維度 | 評估 |
|------|------|
| **佣金** | **0%** |
| **Indie 實際收入** | $2.5K-25K/mo（Standuply, Pull Reminders） |
| **分發** | App Directory 是自然獲客管道 |
| **競爭** | 3,500 app，中等 |

**優勢：** 零佣金、Bot 類產品簡單、Claude Code 很適合做 Slack Bot。
**劣勢：** 用戶付費意願不如 HubSpot/Shopify，Slack 在 Salesforce 下成長趨緩。

---

## 四、排除的平台（不適合我們的約束）

| 平台 | 排除原因 |
|------|----------|
| Salesforce AppExchange | 需要 Apex/LWC 專屬技術棧，學習成本過高 |
| Figma | 設計師付費意願低，市集太新太小 |
| Canva | 無直接收入分成模型，靠創新基金 |
| Bubble | 中位開發者月收 < $100，市場集中度太高 |
| Framer | 營收僅 $50M，市集太小（280 app），且偏模板銷售非技術產品 |
| VS Code | 無原生付費機制，需自建計費系統 |
| Zoom | 開發者收入數據不透明 |
| iOS/Android | 需要 mobile 開發能力，不適合「全由 Claude Code 完成」的約束 |
| WordPress | 市場極成熟，競爭激烈，需 12-24 個月才回本 |

---

## 五、最終推薦排名

| 排名 | 平台 | 綜合評分 | 核心理由 |
|------|------|---------|---------|
| **🥇** | **HubSpot** | ⭐⭐⭐⭐⭐ | 0% 佣金 + indie 中位收入最高($23K MRR) + 客群最有錢 + 競爭最少(2,000 app) |
| **🥈** | **Shopify** | ⭐⭐⭐⭐ | 最大市場 + 最強分發 + 明確痛點(留存缺口) + 但中位收入低 |
| **🥉** | **monday.com** | ⭐⭐⭐⭐ | 最年輕市集(850 app) + $30K MRR 案例 + 但市場較小 |
| 4 | Atlassian | ⭐⭐⭐ | 企業客戶強 + 新 Forge 0% 佣金 + 但技術門檻高 |
| 5 | Slack | ⭐⭐⭐ | 0% 佣金 + 簡單 + 但付費意願中等、成長趨緩 |

---

## 六、策略建議

### 如果選 HubSpot（推薦）
- **優勢：** 相同努力下，收入期望值最高
- **挑戰：** 需要花時間了解 CRM/行銷自動化領域
- **你的產品總監背景是加分項** — 你理解 B2B SaaS 用戶的痛點

### 如果選 Shopify（備選）
- **優勢：** 市場最大、痛點最明確（留存缺口有數據支撐）
- **挑戰：** 中位收入低，需要做對才能贏

### 組合策略
先做 HubSpot app（收入期望值最高），同時觀察 monday.com（最年輕的市集 = 最多空白機會）。如果 HubSpot 方向不對，Shopify 是最穩的備選。

---

## 研究來源

- [Clayton Farr - HubSpot Marketplace by the $ Numbers](https://claytonfarr.com/hubspot-marketplace)
- [Indie Hackers - Indies making $280K+ ARR on HubSpot](https://www.indiehackers.com/post/indies-are-making-280k-arr-on-hubspot-in-2024-608dc3fab2)
- [Shopify App Store Statistics 2026](https://uptek.com/shopify-statistics/app-store/)
- [StoreInspect - Shopify Retention Gap](https://storeinspect.com/blog/shopify-retention-gap)
- [Market Clarity - Shopify App Worth It](https://mktclarity.com/blogs/news/shopify-app-worth-it)
- [monday.com - Build $30K MRR on Marketplace](https://monday.com/appdeveloper/blog/build-30k-saas-monday-marketplace/)
- [monday.com - Revenue Sharing Program](https://developer.monday.com/apps/changelog/announcing-the-revshare-program)
- [Atlassian - Revenue Share Updates 2026](https://www.atlassian.com/blog/developer/updates-to-marketplace-revenue-share-2026)
- [Slack Bot - $0 to $25K/mo](https://medium.com/slack-developer-blog/from-zero-to-25-000-mo-bf7caddea44d)
- [Zendesk AI Revenue](https://theaieconomy.substack.com/p/zendesk-ai-arr-2026-growth)
- [Framer Creator Earnings](https://allaboutframer.com/the-no-nonsense-guide-to-making-money-with-framer-in-2025)
- [Bubble Plugins Profitability](https://mktclarity.com/blogs/news/bubble-plugins-profitable)
- [Figma - Selling Community Resources](https://help.figma.com/hc/en-us/articles/12067637274519-About-selling-Community-resources)
- [HubSpot Q4 2025 Results](https://ir.hubspot.com/news-releases/news-release-details/hubspot-reports-strong-q4-and-full-year-2025-results)
- [Shopify Revenue Share](https://shopify.dev/docs/apps/launch/distribution/revenue-share)
