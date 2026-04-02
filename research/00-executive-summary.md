# Executive Summary — 被動收入網路創業計劃

> 產出日期：2026-04-02
> 操盤者：資深產品總監（兼職 8hr/week，Claude Code 執行開發維運）

---

## 最終推薦：API-as-a-Product（API 即產品）

### 為什麼是 API？

經過 5 輪研究迭代，從 8 個被動收入模式中篩選，**API-as-a-Product 在所有維度上都最符合你的約束條件：**

| 約束 | API-as-a-Product 表現 |
|------|----------------------|
| Claude Code 可建置維運 | ⭐⭐⭐⭐⭐ 純後端，零 UI，完美適配 |
| 月成本 < TWD 10,000 | ⭐⭐⭐⭐⭐ 預估月成本 TWD 300-3,000 |
| 全被動 | ⭐⭐⭐⭐⭐ API 天然無人值守 |
| 不露臉/無客服 | ⭐⭐⭐⭐⭐ 自助式產品 |
| 兼職 8hr/week | ⭐⭐⭐⭐ 4 週可上線 MVP |

### 商業模式一句話

**建立 3-5 個解決特定痛點的 Niche API，上架 RapidAPI 等 Marketplace，透過 Freemium + 訂閱制變現。**

---

## 數字預估

| 時間點 | API 數量 | 付費用戶 | MRR (USD) | MRR (TWD) | 月成本 (TWD) |
|--------|---------|---------|-----------|-----------|-------------|
| Week 4 | 2 | 0-2 | $0-20 | 0-600 | 300-500 |
| Week 8 | 3-4 | 5+ | $50-150 | 1,500-4,500 | 500-1,500 |
| Week 12 | 5 | 15+ | $150-500 | 4,500-15,000 | 1,000-3,000 |
| Month 6 | 8-10 | 50+ | $500-1,000 | 15,000-30,000 | 2,000-5,000 |
| Month 12 | 10+ SaaS | 100+ | $2,000-5,000 | 60,000-150,000 | 3,000-8,000 |

---

## 12 週啟動計劃摘要

```
Week 1-2:  建置 + 部署前 2 個 API → 上架 RapidAPI
Week 3-4:  優化 + 初步行銷 → 獲取第一批用戶
Week 5-8:  驗證 PMF → 擴展到 3-4 個 API → 目標 5 付費用戶
Week 9-12: 擴展到 5 個 API → 建立自動化維運 → 每週 < 1hr 維護
```

## 產品演進路線

```
Phase 1 (Now):    API Portfolio → 快速驗證，多個 niche 同時試
Phase 2 (Month 4): API → SaaS → 最成功的 API 加 UI，賣結果
Phase 3 (Month 8): SaaS + Extension → 多管道分發
Phase 4 (Month 12): 自有平台 → 脫離 Marketplace 佣金
```

## 首批 API 方向

1. **結構化數據擷取 API** — 非結構化文本 → JSON
2. **SEO 元數據生成器** — URL/內容 → SEO meta tags
3. **競品價格監控 API** — 商品追蹤 → 價格趨勢
4. **內容品質評分 API** — 文章 → 多維度品質分數
5. **品牌名稱產生器 API** — 關鍵字 → 名稱 + domain check

## 關鍵風險與退出條件

- **Pivot 信號（Week 8）：** 免費用戶 < 20 且付費 = 0
- **退出條件（Week 12）：** 2 次 pivot 後 MRR < $30
- **最大風險：** PMF 不確定 → 用多 API 組合分散

## 技術棧

TypeScript + Hono + PostgreSQL + Redis，部署在 Railway ($5/mo)，分發在 RapidAPI。

---

## 下一步

**準備好的話，告訴我「開始開發」，我會啟動 Week 1 的工作。**

---

## 完整報告目錄

| 文件 | 內容 |
|------|------|
| [01-trend-scan.md](./01-trend-scan.md) | 8 個被動收入模式掃描 |
| [02-opportunity-score.md](./02-opportunity-score.md) | 量化評分矩陣，Top 5 篩選 |
| [03-deep-validation.md](./03-deep-validation.md) | Top 5 方向深度驗證（競品、案例、風險） |
| [04-business-model.md](./04-business-model.md) | 商業模型畫布 + 技術架構 + 定價策略 |
| [05-action-roadmap.md](./05-action-roadmap.md) | 12 週行動計劃 + KPI + 維運 SOP |
