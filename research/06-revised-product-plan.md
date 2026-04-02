# Round 2 — 需求端導向的產品規劃

> 產出日期：2026-04-02
> 前提：Round 1 的 API Portfolio 策略被否決，原因：(1) 沒有明確買家 (2) 沒有分發管道 (3) AI wrapper 無護城河

---

## 一、從錯誤中學到的三條鐵律

1. **先找到花錢的人，再想做什麼產品** — 不是「我能做什麼」而是「誰已經在為什麼付費」
2. **分發管道必須內建在產品選擇裡** — 如果上線後不知道怎麼被看見，這個方向就不成立
3. **護城河不能靠技術，要靠場景鎖定** — 在一個特定平台/場景裡解決痛點，比泛用工具強 100 倍

---

## 二、平台生態系分析：哪裡有內建分發？

| 平台 | 用戶規模 | App Store 分發力 | 佣金 | Claude Code 適配 | 適合全被動？ |
|------|---------|-----------------|------|-----------------|------------|
| **Shopify** | 476 萬商家 | ✅ 強（商家主動找 App） | 0%（首 $1M）→ 15% | ✅ | ⚠️ 可能需少量客服 |
| **WordPress** | 4.55 億站點 | ✅ 強（Plugin Directory） | 0%（自售） | ✅ | ⚠️ 需維護相容性 |
| **Slack** | 7500 萬日活 | ✅ 中（App Directory） | 0% | ✅ | ✅ |
| **Chrome Web Store** | 30 億 Chrome 用戶 | ⚠️ 弱（很擁擠） | 0% | ✅ | ✅ |
| **Figma** | 800 萬用戶 | ⚠️ 新市集 | 15% | ⚠️ 需設計知識 | ✅ |

### 結論：Shopify App Store 是最佳分發管道

**原因：**
- 商家**主動搜尋**解決方案 — 不是你去找他，是他來找你
- 商家**習慣付費** — Shopify 生態中付費是常態，平均每店 3.1 個 app
- **巨大的未滲透空間** — 98.1% 商家缺分析工具、93.9% 缺評價工具、88.4% 高流量店缺 SMS
- **佣金極友善** — 首 $100 萬零佣金，之後僅 15%
- **技術棧簡單** — Node.js + Shopify API，Claude Code 完全勝任

---

## 三、Shopify 商家的真實痛點（有數據支撐）

### 痛點 1：花了廣告費，但客戶買一次就走（留存缺口）

**數據：**
- 40% 的 Shopify 商家跑付費廣告但**零留存工具**（無 email、無忠誠度、無評價收集）
- Meta CPM 漲到 $10.88，Google Shopping CPC 漲 33.7%
- 平均 CAC 現在 $68-84，兩年內漲了 40-60%
- **88.4% 高流量店沒有 SMS marketing，84.9% 沒有忠誠度計畫**

**商家心聲：** 「我花了錢買流量，客人來了、買了、走了，再也不回來。」

### 痛點 2：Marketing app 太貴（定價缺口）

**數據：**
- Klaviyo（email/SMS）：$45-350+/mo，功能超出小商家需求
- Yotpo（評價/忠誠度）：$79-199+/mo
- Smile.io（忠誠度）：$49-599/mo
- 對月營收 < $10K 的小商家來說，這些工具的 ROI 不合理

**商家心聲：** 「我知道要做 email marketing，但 Klaviyo $45/月太貴了，我一個月才賺幾千塊。」

### 痛點 3：營運行銷類 app 分類收入差距巨大

**數據：**
- Marketing apps 平均年收 $19,900，是所有類別最高
- 但大多數收入被頭部 app 壟斷（Klaviyo 佔 20.8% 市場）
- 長尾市場（小商家的簡單需求）嚴重不足

---

## 四、產品方向建議（需求端出發）

### 方向 A：Shopify 輕量留存工具（最推薦）

#### 產品概念
**一個極簡的 Shopify App，幫小商家自動把一次性買家變回頭客。**

不是另一個 Klaviyo，而是一個「窮人版自動留存機器」：
- 客戶下單後自動發感謝 email + 折扣碼（鼓勵回購）
- X 天後自動發提醒 email（「你的 XX 該補貨了」）
- 簡單的購買後 review 請求
- 一個 Dashboard 看回購率

#### 誰買？
- Shopify 月營收 $1K-$10K 的小商家
- 他們知道需要做留存但覺得 Klaviyo 太貴太複雜
- 他們在 Shopify App Store 搜尋「email marketing」「customer retention」「repeat purchase」

#### 怎麼被看到？
- **Shopify App Store 搜尋** — 商家主動搜尋，你是搜尋結果
- **Freemium** — 免費版處理前 100 筆訂單/月，自然成長
- **"Powered by" 病毒循環** — 免費版 email 底部帶你的品牌 logo，收到 email 的其他商家看到 → 安裝

#### 定價
| 方案 | 價格 | 內容 |
|------|------|------|
| Free | $0 | 100 封 email/月 + "Powered by" 浮水印 |
| Starter | $9/mo | 1,000 封/月 + 去浮水印 |
| Growth | $29/mo | 10,000 封/月 + 進階分析 |

#### 為什麼這行得通？
1. **明確的買家** — 476 萬 Shopify 商家中 40% 缺留存工具 = 190 萬潛在用戶
2. **內建分發** — Shopify App Store 是主要獲客管道
3. **自帶病毒循環** — "Powered by" badge 在 email 中自然傳播
4. **價格錨定** — Klaviyo $45+，你 $9-29，明確的價值主張
5. **Claude Code 可完成** — Shopify App API + email 發送（Resend/Postmark），純後端邏輯
6. **接近全被動** — 安裝後自動運行，商家不需要操作

#### 風險
- Shopify 自身可能推出類似功能（平台風險）
- Email 送達率需要維護（SPF/DKIM 設定）
- 需要少量客服（Shopify 用戶期望有支援）→ 可用 AI chatbot 處理

---

### 方向 B：Shopify 智慧評價收集器（備選）

#### 產品概念
客戶購買後自動在最佳時機發送評價請求，收集到的評價自動展示在商品頁面，提升轉換率。

#### 誰買？
- 93.9% 的 Shopify 商家缺評價工具
- 競品 Yotpo 起步 $79/mo，Judge.me 免費版功能受限

#### 怎麼被看到？
- Shopify App Store 搜尋「product reviews」
- Freemium + "Powered by" 在評價區塊展示

#### 定價
- Free: 50 封評價請求/月
- Pro: $12/mo（無限 + 去品牌）
- Business: $29/mo（AI 分析 + 照片評價）

---

### 方向 C：開源工具 + 託管版（長期策略）

#### 產品概念
仿 Plausible Analytics / Papermark 模式 — 開源一個有價值的工具，用 GitHub 做分發，靠託管版收費。

#### 為什麼考慮？
- Plausible：$3.1M ARR，零廣告費，靠 Hacker News + 開源社群
- Papermark：1 年內 $1K → $45K MRR，靠 SEO + 開源
- Carrd：$146K/月，靠 "Made with Carrd" 病毒循環

#### 可能的方向
- 開源的 DocSend 替代品（已有 Papermark）
- 開源的 Typeform 替代品
- 開源的小型 analytics 工具（特定 niche）
- 開源的 status page / uptime monitor

#### 風險
- 開源社群經營不是全被動（issue、PR、討論）
- 需要 6-12 個月才有 traction
- 需要找到真正還沒被做的空缺

---

## 五、方向比較

| 維度 | A. Shopify 留存 | B. Shopify 評價 | C. 開源+託管 |
|------|----------------|----------------|-------------|
| 買家明確度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 分發管道 | ⭐⭐⭐⭐⭐ Shopify Store | ⭐⭐⭐⭐⭐ Shopify Store | ⭐⭐⭐ GitHub + HN |
| 病毒循環 | ⭐⭐⭐⭐⭐ Email badge | ⭐⭐⭐⭐ Review badge | ⭐⭐⭐ GitHub stars |
| 護城河 | ⭐⭐⭐ 場景鎖定 | ⭐⭐⭐ 場景鎖定 | ⭐⭐⭐⭐ 開源社群 |
| Claude Code 適配 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 被動程度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 收入天花板 | ⭐⭐⭐⭐ $5K-50K/mo | ⭐⭐⭐ $3K-30K/mo | ⭐⭐⭐⭐⭐ $10K-100K+/mo |
| 啟動速度 | ⭐⭐⭐⭐ 4-6 週 | ⭐⭐⭐⭐ 4-6 週 | ⭐⭐ 3-6 個月見效 |

---

## 六、最終推薦

### 主力：方向 A — Shopify 輕量留存工具

**一句話：** 幫 Shopify 小商家用 $9/月（而不是 $45/月）把一次性買家變回頭客。

**為什麼這是最佳選擇：**

1. **買家就在那裡** — 190 萬 Shopify 商家缺留存工具，他們在 App Store 主動搜尋
2. **分發已解決** — Shopify App Store 就是你的獲客管道
3. **病毒循環已設計** — 每封 email 底部的 "Powered by" 帶來新商家
4. **價格錨定清晰** — 「Klaviyo 太貴？試試我們只要 $9」
5. **技術 100% 可行** — Shopify App API + email service，Claude Code 端到端
6. **接近全被動** — 商家安裝 → 自動觸發 → 不需要操作

### 備選：方向 B — Shopify 評價收集

如果方向 A 在 8 週後未達標，pivot 到評價收集（93.9% 商家缺此工具）。

---

## 七、下一步

準備好的話，我可以：
1. 深入研究 Shopify App 的技術架構需求
2. 分析現有留存類 app 的具體競品
3. 設計詳細的 MVP 功能規格
4. 直接開始開發

---

## 研究來源

- [Shopify App Store Statistics 2026](https://uptek.com/shopify-statistics/app-store/)
- [Shopify Revenue Share Policy](https://shopify.dev/docs/apps/launch/distribution/revenue-share)
- [Market Clarity - Is Shopify App Business Worth It](https://mktclarity.com/blogs/news/shopify-app-worth-it)
- [StoreInspect - Shopify Retention Gap (358K Store Study)](https://storeinspect.com/blog/shopify-retention-gap)
- [StoreInspect - State of Shopify 2026](https://storeinspect.com/report/state-of-shopify)
- [Indie Hackers - $0 to $62K MRR](https://www.indiehackers.com/post/tech/from-0-to-62k-mrr-in-three-months-mUPVSYOlJAC2iogGK7d4)
- [Plausible Analytics - $3.1M ARR](https://www.indiehackers.com/post/i-did-it-my-open-source-company-now-makes-14-2k-monthly-as-a-single-developer-f2fec088a4)
- [Papermark - $1K to $45K MRR](https://medium.com/startup-insider-edge/the-100k-mrr-illusion-5-micro-saas-founders-proving-its-possible-and-how-they-did-it-c3571dd336b3)
- [Carrd - $146K/month solo developer](https://www.jermainebrown.org/posts/indie-hackers-generating-100k-monthly)
- [Indie Launches - 326 Projects Analyzed](https://indielaunches.com/indie-maker-analytics-2024-2025-projects/)
- [Slack Bot - $0 to $25K/mo](https://medium.com/slack-developer-blog/from-zero-to-25-000-mo-bf7caddea44d)
- [ProductLed - Growth Flywheel](https://www.productled.org/foundations/the-product-led-growth-flywheel)
- [Superhuman - 30-60% top of funnel from "Sent with" badge](https://www.news.aakashg.com/p/ultimate-guide-growth-loops)
