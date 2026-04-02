# Loop 5 — 行動路線圖 (Action Roadmap)

> 產出日期：2026-04-02
> 引用：Loop 4 商業設計結論

---

## 一、12 週啟動計劃總覽

```
Phase 1: MVP 建置（Week 1-4）      → 目標：2 個 API 上線
Phase 2: 上線驗證（Week 5-8）      → 目標：50 免費用戶 + 5 付費用戶
Phase 3: 擴展自動化（Week 9-12）   → 目標：3-5 個 API + 自動化維運
```

**每週投入：8 小時（兼職）**

---

## 二、Phase 1：MVP 建置（Week 1-4）

### Week 1：基礎建設 + 第一個 API（8hr）

| 任務 | 時間 | 執行者 |
|------|------|--------|
| 註冊 Railway、RapidAPI、Stripe 帳號 | 1hr | 你 |
| Claude Code 建立專案骨架（TypeScript + Hono + PostgreSQL） | 2hr | Claude Code |
| 開發 API 1：結構化數據擷取 API（核心邏輯） | 3hr | Claude Code |
| 撰寫 API 文件 + 測試 | 1.5hr | Claude Code |
| 部署到 Railway | 0.5hr | Claude Code |

**Week 1 產出：** API 1 已部署，可透過 endpoint 測試

### Week 2：API 1 上架 + 開始 API 2（8hr）

| 任務 | 時間 | 執行者 |
|------|------|--------|
| 上架 API 1 到 RapidAPI（設定定價、文件、範例） | 2hr | 你 + Claude Code |
| 開發 API 2：SEO 元數據生成器（核心邏輯） | 3hr | Claude Code |
| 設定快取層（Redis / Upstash） | 1hr | Claude Code |
| 撰寫 API 2 文件 + 測試 | 1.5hr | Claude Code |
| 設定 BetterStack 監控 | 0.5hr | Claude Code |

**Week 2 產出：** API 1 已上架 RapidAPI，API 2 開發完成

### Week 3：API 2 上架 + 優化（8hr）

| 任務 | 時間 | 執行者 |
|------|------|--------|
| 上架 API 2 到 RapidAPI | 1.5hr | 你 + Claude Code |
| 根據測試結果優化 API 1 & 2 | 2hr | Claude Code |
| 加入 rate limiting + 用量追蹤 | 2hr | Claude Code |
| 建立成本監控 Dashboard（簡單腳本追蹤 API 成本） | 1.5hr | Claude Code |
| 撰寫 2 篇技術部落格（Dev.to/Medium）介紹 API | 1hr | Claude Code |

**Week 3 產出：** 2 個 API 上線 + 初步行銷內容

### Week 4：穩定化 + 第一輪數據回顧（8hr）

| 任務 | 時間 | 執行者 |
|------|------|--------|
| 監控 API 穩定性，修復發現的 bug | 2hr | Claude Code |
| 分析 RapidAPI 流量數據 + 用戶行為 | 1hr | 你 |
| 優化 API 文件（根據用戶常見問題） | 1.5hr | Claude Code |
| 研究並選定 API 3 方向（根據市場反饋） | 1.5hr | 你 + Claude Code |
| 開始開發 API 3 | 2hr | Claude Code |

**Week 4 產出：** 穩定運行的 2 個 API + API 3 開發中

---

## 三、Phase 2：上線驗證（Week 5-8）

### Week 5-6：獲客 + API 3 上線（16hr total）

| 任務 | 時間 |
|------|------|
| 完成 API 3 開發 + 上架 | 4hr |
| 在 Reddit (r/webdev, r/SaaS, r/Entrepreneur) 分享 API | 2hr |
| 在 Indie Hackers 發布 building in public 文章 | 2hr |
| 回應早期用戶反饋 | 2hr |
| 監控 + bug fix | 2hr |
| 分析轉換數據（Free → Pro） | 2hr |
| 優化定價策略（如有需要） | 1hr |
| 開始研究 API 4 方向 | 1hr |

### Week 7-8：數據驅動迭代（16hr total）

| 任務 | 時間 |
|------|------|
| 開發 + 上架 API 4 | 5hr |
| 根據數據調整定價和功能 | 2hr |
| 寫 case study（如果有付費用戶的話） | 2hr |
| 嘗試在 Apify Marketplace 上架表現最好的 API | 2hr |
| 設定自動化報表（每週收入/用量自動通知） | 2hr |
| Phase 2 回顧：是否達到 50 免費 + 5 付費的目標 | 1hr |
| 決定是否 continue / pivot / expand | 2hr |

**Phase 2 結束時的驗證檢查點：**

| 指標 | 目標 | 達到 → | 未達到 → |
|------|------|--------|----------|
| 免費用戶數 | ≥ 50 | 繼續 Phase 3 | 檢查分發策略 |
| 付費用戶數 | ≥ 5 | 繼續 Phase 3 | 檢查定價/價值主張 |
| API Uptime | ≥ 99% | 繼續 | 修復穩定性問題 |
| 每週維護時間 | < 2hr | 繼續 | 簡化架構 |
| 月成本 | < TWD 3,000 | 繼續 | 優化成本 |

---

## 四、Phase 3：擴展自動化（Week 9-12）

### Week 9-10：擴展 API 組合（16hr total）

| 任務 | 時間 |
|------|------|
| 開發 + 上架 API 5 | 5hr |
| 建立 API 自動化健康檢查腳本 | 2hr |
| 建立自動化成本告警（超過閾值通知） | 1hr |
| 優化快取策略（降低 AI API 成本） | 2hr |
| 建立簡單的 Landing Page（SEO 用） | 3hr |
| 分析哪個 API 最成功，投入更多資源 | 1hr |
| 收集用戶回饋，規劃 Phase 2 產品演進 | 2hr |

### Week 11-12：自動化維運 + 長期規劃（16hr total）

| 任務 | 時間 |
|------|------|
| 完善所有自動化監控和告警 | 3hr |
| 撰寫 Claude Code 維運 SOP（見下方） | 2hr |
| 設定定期健康檢查 cron job | 2hr |
| 建立自動備份機制 | 1hr |
| Product Hunt Launch（如指標達標） | 3hr |
| 12 週回顧 + Phase 2（SaaS）規劃 | 3hr |
| 決定是否開始 Workflow-as-SaaS 演進 | 2hr |

---

## 五、每階段驗證指標 (KPI)

| KPI | Week 4 | Week 8 | Week 12 |
|-----|--------|--------|---------|
| 上架 API 數量 | 2 | 3-4 | 5 |
| 免費用戶總數 | 10+ | 50+ | 150+ |
| 付費用戶總數 | 0-2 | 5+ | 15+ |
| MRR (USD) | $0-20 | $50-150 | $150-500 |
| MRR (TWD) | 0-600 | 1,500-4,500 | 4,500-15,000 |
| API Uptime | >95% | >99% | >99.5% |
| 每週維護時間 | 2-4hr | 1-2hr | <1hr |
| 月運營成本 (TWD) | 300-500 | 500-1,500 | 1,000-3,000 |

---

## 六、失敗退出條件

### 🚨 Hard Pivot 信號（Week 8 檢查）
如果以下**全部**成立，則需要 pivot：
- 免費用戶 < 20（分發完全失敗）
- 付費用戶 = 0（沒有付費意願）
- 嘗試了 3+ 個不同方向的 API 都沒有 traction

### Pivot 選項（優先順序）
1. 換不同的 API niche（成本最低的 pivot）
2. 從 API 轉向 Chrome Extension（轉換用已開發的後端邏輯）
3. 從 API 轉向 Workflow-as-SaaS（加 UI，賣結果）
4. 從 API 轉向數位產品（模板、工具包）

### 🛑 完全退出條件
- 12 週結束時 MRR < $30（TWD 900）
- 且嘗試了至少 2 次 pivot
- 且沒有任何成長趨勢

---

## 七、Claude Code 維運 SOP

### 日常自動化（不需人工介入）
```
1. BetterStack 監控 API uptime
   → 如果 down → 自動重啟（Railway 內建）
   → 如果持續 down → Email 告警

2. 成本監控腳本（每日跑一次）
   → 計算當日 AI API 呼叫成本
   → 超過閾值 → Email 告警

3. Railway auto-sleep
   → 無流量 10 分鐘後自動休眠
   → 有請求時自動喚醒
```

### 定期維護（Claude Code 執行，每週一次）
```
1. 檢查依賴套件更新
2. 檢查 API endpoint 回應時間
3. 分析用量趨勢
4. 檢查錯誤日誌
5. 產出週報（用量 / 收入 / 錯誤統計）
```

### 異常處理（Claude Code on-demand）
```
1. 收到用戶回報 → Claude Code 診斷 + 修復
2. 第三方 API 變動 → Claude Code 更新適配
3. 新 API 上架 → Claude Code 端到端開發部署
```

---

## 八、12 週後的展望

### 如果成功（MRR > $200）：
- **Month 4-6：** 擴展到 8-10 個 API，目標 MRR $500-1,000
- **Month 6-9：** 建自有 Dashboard + 直接銷售（脫離 RapidAPI 25% 佣金）
- **Month 9-12：** 開始 Workflow-as-SaaS，包裝最成功的 API 為 SaaS 產品
- **Month 12+ 目標：** MRR $2,000-5,000（TWD 60,000-150,000）

### 長期願景（12-24 個月）：
```
API Portfolio (5-10 APIs)
     ↓ 最成功的 1-2 個
Workflow-as-SaaS (賣結果，$29-99/mo)
     ↓ 需要更多分發
Chrome Extension (前端入口)
     ↓ 建立品牌
自有平台 + SEO 流量
     ↓
月被動收入 TWD 100,000+
```

---

## 九、下一步行動（本週可開始）

1. **今天：** 註冊 RapidAPI 開發者帳號
2. **今天：** 註冊 Railway 帳號
3. **明天：** 跟 Claude Code 說「開始開發第一個 API」
4. **本週：** 完成 API 1 核心邏輯 + 部署
5. **下週：** 上架 RapidAPI，開始收集第一批用戶

---

## 研究來源

- [RapidAPI - Developer Guide](https://rapidapi.com/guides/sell-apis-to-earn-money-as-a-developer)
- [Railway Docs](https://docs.railway.com/)
- [BetterStack - Free Monitoring](https://betterstack.com/)
- [Stripe - API Billing](https://stripe.com/billing)
- [Medium - Solo Founder SaaS Framework](https://medium.com/write-a-catalyst/from-0-to-2-500-my-6-step-framework-for-building-micro-saas-as-a-solo-founder-fba5d545b97c)
