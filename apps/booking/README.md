# 約課系統

仿照 FitBook 約課系統的操作流程，藍色系介面，電腦與手機同一套單欄版面。
獨立運作，可掛在任何網域根目錄或子路徑下。

- 後端：Python FastAPI + SQLite（`server/app.py`，資料存在 `data/booking.db`）
- 前端：React + Vite（`web/`），打包後由後端直接提供
- 部署：`deploy/install.sh` 一鍵安裝（systemd + nginx，不需要 Docker 或 Node.js）

## 功能

### 學生端

| 頁面 | 功能 |
|---|---|
| 課程預約 | 週曆（今天、上一週／下一週），依日期列出課程：老師頭像、課名、新手友善標籤、時間、類別、老師（代課）、預約人數或「剩餘 N 位」、狀態按鈕（預約／已預約／候補／已候補／截止／已結束／停課） |
| 課程資訊 | 課程細節、老師、預約須知、選擇課卡、已預約學員（姓名遮罩）；預約、額滿加入候補、取消預約／候補 |
| 師資陣容 | 老師列表與介紹頁（近期課程、評價） |
| 課卡方案 | 全部／點數課卡／堂數課卡／無限課卡篩選，送出購買申請並顯示付款方式 |
| 關於場館 | 地址（Google 地圖）、電話、LINE、介紹、規範、評價列表 |
| 會員中心 | 預約紀錄（即將到來／歷史，可評價）、我的課卡與購買紀錄、通知、帳號設定 |
| 對話框 | 預約成功、預約人數已額滿（加入候補）、帳號停權、沒有可用課卡 |

### 場主端（`#/admin`）

| 頁面 | 功能 |
|---|---|
| 總覽 | 待確認訂單、本月營收、7 日內預約、學生人數、今日課程 |
| 課程 | 週曆排課；新增／編輯／複製課程、每週重複排課、停課（自動退卡並通知）、刪除 |
| 名單點名 | 出席／缺席、取消預約（可選擇退卡）、候補轉正式、代為預約 |
| 訂單 | 確認收款後自動開通課卡、取消訂單 |
| 會員 | 搜尋、課卡調整與展延、手動開通課卡、備註、停權／解除、設為場主 |
| 課卡方案 | 點數卡／堂數卡／無限卡，堂數或點數、效期、售價、上下架 |
| 老師 | 照片上傳、頭銜、介紹、顯示與排序 |
| 評價 | 查看與隱藏評價 |
| 場館設定 | 名稱、封面、地址、電話、LINE、介紹、規範、付款說明、課程類別、開放預約天數、顯示人數、候補開關 |

### DUPR 場

- 場主建課時勾選「DUPR 場」，設定依據雙打或單打分數、最低分／最高分，以及是否只限已驗證帳號。
- 課程列表顯示深藍色「DUPR 3.0–4.0」標籤，當天有 DUPR 場時可用「全部／DUPR 場／一般場」篩選。
- 學生在會員中心「DUPR」分頁綁定 DUPR ID：
  - **有 DUPR 合作夥伴金鑰時**（`DUPR_CLIENT_KEY`／`DUPR_CLIENT_SECRET`）：系統向 DUPR 取得姓名與單打、雙打分數，也可隨時「從 DUPR 更新分數」。
  - **沒有金鑰時**：學生自行填寫 DUPR ID 與分數，標示「待場館核對」。
- 報名、候補遞補時都會檢查 DUPR 條件；不符合的候補會被跳過並收到通知。
- 場主在會員資料中可核對並「驗證」DUPR 帳號、代為綁定或修正分數；點名名單會顯示每位學員的 DUPR 分數。
- 一個 DUPR ID 只能綁定一個帳號；學生自行修改分數後會失去驗證狀態。

### DUPR 賽事（分組、賽程、比分）

- 建 DUPR 場時選「賽制」與「每局分數」（11／15／21，領先 2 分獲勝）：
  - **輪換搭檔**：每組 4～7 人一面場，每局換搭檔。4 人打 3 局、5 人打 5 局（每局 1 人輪空）、6～7 人每人打 4 局；搭檔不重複、不會連續輪空。
  - **固定搭檔**：兩人一隊，同組隊伍互打一輪（每組 2～5 隊）。報名後可在課程頁用對方的手機或信箱指定隊友；沒指定的依分數首尾配對，讓各隊實力平均。
  - 依據**單打**分數的 DUPR 場固定為單打循環賽。
- 人到齊後，團主到「名單 → 賽事」：系統依 DUPR 分數由高到低建議分組，點兩位球員可互換、也可把人移到別組，確認後按「生成賽事」並通知所有球員。
- 比分：球員回報後由**對手**按確認才算數（對手也可改報，改由原回報方確認）；團主可直接登錄、修改或清除任何一局。排名只計已確認的比分，依勝場、得失分差、得分排序。
- 生成賽事後學員不能自行取消、固定搭檔不能換隊友；要調整名單請先刪除賽事再重新生成。

> DUPR 金鑰需以場館名義向 DUPR 申請 API 合作夥伴（partner）資格。
> 系統使用 `POST /api/auth/v1/token` 取得權杖、`GET /api/user/v1/{duprId}` 取得球員資料。

### 登入方式

- **LINE 登入**：設定 `LINE_CHANNEL_ID`／`LINE_CHANNEL_SECRET` 後，登入頁會出現「使用 LINE 登入」，並使用 LINE 的名字與頭像。
  LINE 提供的信箱與既有帳號相同時，會連到同一個帳號。
- **在 LINE 裡開啟（LIFF）**：再設定 `LINE_LIFF_ID`，從 LINE 開啟網站時會自動登入。
- **信箱註冊**：姓名、信箱、密碼（手機選填），沒有頭像，可自行上傳。
- 會員可在「會員中心 → 帳號」綁定／解除 LINE、設定信箱與密碼；使用者自己上傳的頭像不會被 LINE 頭像覆蓋。
- 舊的手機號碼帳號仍可用「手機＋密碼」登入。

LINE Developers 設定：建立 Provider → LINE Login channel，開啟 OpenID Connect（Email address permission 需另外申請），
Callback URL 填 `https://<網域>/api/auth/line/callback`；LIFF 的 Endpoint URL 填 `https://<網域>/`，Scope 勾選 `openid`、`profile`（可選 `email`）。
最後把 channel 從 Developing 切到 Published，否則只有 channel 管理員能登入。

金鑰在主機上執行 `sudo booking-line-setup` 貼上即可（會檢查格式、重新啟動並確認 LINE 登入已啟用，失敗會自動還原）。

- 還沒申請到 Email address permission 也能登入：LINE 回 `invalid_scope` 時會自動改成不要求信箱再授權一次。
- 設定了 `BOOKING_DOMAIN` 時，callback 一律使用 `https://<網域>/`（有網域時網站只從這個網址對外，不再開 8080）。

### 預約規則

- 堂數卡每堂扣 1 堂；點數卡依課程設定扣點；無限卡不扣次數；課程扣點設為 0 則為免費課程，不需課卡。
- 課程可限定只能使用某些課卡方案。
- 開課前 N 小時截止預約、開課前 M 小時內不能自行取消（每堂課可各自設定）。
- 額滿可加入候補；有人取消時，依候補順序自動遞補、扣卡並通知，沒有可用課卡的人會被跳過。
- 被停權的帳號無法預約或購買課卡。

## 本機開發

```bash
# 後端
cd server
pip install -r requirements.txt
BOOKING_OWNER_PHONE=0900000000 BOOKING_OWNER_PASSWORD=owner123 BOOKING_SEED_DEMO=1 \
  uvicorn app:app --port 8100 --reload

# 前端（另一個終端機，會把 /api 轉到 8100）
cd web
npm install
npm run dev
```

API 文件：`http://localhost:8100/api/docs`

## 部署

在主機（Ubuntu 22.04／24.04）上執行一行指令：

```bash
# 有網域（先把網域 A 紀錄指向主機 IP），會自動申請 HTTPS
curl -fsSL https://raw.githubusercontent.com/maxi9811207/dc4ni/claude/upbeat-davinci-5wb5rp/apps/booking/deploy/install.sh \
  | sudo BOOKING_DOMAIN=booking.example.com bash

# 沒有網域：用 sslip.io 免費網域（IP 172.237.11.215 → 172-237-11-215.sslip.io），一樣有 HTTPS
curl -fsSL https://raw.githubusercontent.com/maxi9811207/dc4ni/claude/upbeat-davinci-5wb5rp/apps/booking/deploy/install.sh \
  | sudo BOOKING_DOMAIN=172-237-11-215.sslip.io bash

# 只用 http://主機IP:8080（密碼會以明文傳送，不建議正式使用）
curl -fsSL https://raw.githubusercontent.com/maxi9811207/dc4ni/claude/upbeat-davinci-5wb5rp/apps/booking/deploy/install.sh \
  | sudo bash
```

第一次執行會詢問場主姓名、手機、密碼。腳本只會新增自己的檔案與 nginx 站台（`/etc/nginx/sites-available/booking`），
不修改主機上既有的網站；nginx 設定檢查失敗會自動還原。之後要更新版本，再執行同一行指令即可（資料會保留）。

| 項目 | 位置 |
|---|---|
| 程式 | `/opt/booking/server` |
| 資料（SQLite、上傳圖片） | `/opt/booking/data`，請定期備份 |
| 設定（場主帳號、DUPR、LINE 金鑰） | `/etc/booking.env`，修改後 `sudo systemctl restart booking` |
| 服務記錄 | `journalctl -u booking -f` |

也可以用 Docker：`cp .env.example .env` 填好後執行 `docker compose up -d --build`。
