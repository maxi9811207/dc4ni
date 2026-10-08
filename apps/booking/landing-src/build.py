#!/usr/bin/env python3
"""產生 Digital Court 品牌站的產品頁，並更新各頁共用的頂列、頁尾、產品卡與 sitemap。

    python3 apps/booking/landing-src/build.py

- 產品資料都在下面的 PRODUCTS；改文案改這裡，再跑一次。
- 產生：landing/<slug>.html（DC Pickleball 以外的產品頁）、landing/sitemap-main.xml
- 更新：landing/index.html、trainer.html、booking.html 裡 <!--gen:xxx--> … <!--/gen:xxx--> 之間的內容
- 產品圖放 landing/img/<slug>.webp（主圖）與 <slug>-scene.webp（情境圖），3:2；還沒放的話頁面顯示品牌底圖
- 新增產品網址時：nginx 的頁面清單（deploy/nginx-platform.conf 與正式主機）和 server/tenancy.py 的 RESERVED 都要加
"""
import html
import json
import re
from pathlib import Path

LANDING = Path(__file__).resolve().parent.parent / "landing"
SITE = "https://digital-court.cc"
TODAY = "2026-10-04"
EMAIL = "dc@dc-studio.cc"

# 首頁的兩個主力產品（頁面是手寫的，這裡只用來產生卡片、頁尾與 sitemap）
BOOKING = {"slug": "booking", "code": "Booking", "name": "匹克球預約報名系統", "cats": ["運動"],
           "card": "開團報名、收費對帳、DUPR 賽事、時段預約。球友用 LINE 一鍵報名，不用下載 App。每月 NT$490 起，可免費試用 7 天。"}
TRAINER = {"slug": "trainer", "code": "Pickleball", "name": "匹克球互動訓練機", "cats": ["運動"],
           "card": "互動投影、智能發球機、擊球感應與收球網架整合成一面會餵球、會出題、會計分的對打牆，一個人也能練。"}

PRODUCTS = [
    {
        "slug": "ballwall", "code": "BallWall", "name": "砸球互動牆", "cats": ["運動", "親子"],
        "card": "丟球打中牆上的投影目標就會爆開、加分，讓孩子跑跳流汗的室內運動遊戲。",
        "title": "砸球互動牆｜丟球打投影目標的親子運動遊戲",
        "desc": "DC BallWall 砸球互動牆把投影目標投在牆上，孩子用軟球丟中就會爆開、加分。適合親子館、室內遊樂場、幼兒園、補習班與運動中心，讓孩子在室內跑跳、練手眼協調。台灣在地安裝與維修。",
        "h1": ["砸球互動牆：", "丟中目標就爆開、", "越玩越想再來一局"],
        "lead": "投影機把氣球、怪獸、水果等目標投在牆上，感應器判斷球打中哪裡，打中就爆開、加分。孩子撿球、再丟，玩得滿身大汗，手眼協調也一起練。",
        "facts": ["牆面就是遊戲場", "多人同時搶分", "支援台灣 110V", "台灣在地安裝與維修"],
        "features": [
            ("打中就有反應", "感應器即時判定擊中位置，目標爆開、音效、加分同時出現。"),
            ("多人一起玩", "一面牆可以好幾個孩子一起丟、一起搶分，適合團體課與生日派對。"),
            ("搭配球池更好玩", "常見做法是放在海洋球池旁邊，球就地取材，玩完不用另外撿。"),
            ("安裝簡單", "投影機吊掛在牆前上方，牆面平整就能投，不用大興土木。"),
        ],
        "games_title": "遊戲內容",
        "games_lead": "目標、關卡與音效都不同，同一面牆可以換著玩。以下為內容示例，實際依版本而定。",
        "games": ["打氣球", "打怪獸", "水果切切樂", "打地鼠", "足球射門", "數字與字母"],
        "for": [
            ("親子館、室內遊樂場", "人多也能一起玩的團體互動區，家長在旁邊看得到、也拍得到。"),
            ("幼兒園、補習班", "體能課、下雨天的室內活動，消耗體力也練專注。"),
            ("運動中心、球館", "兒童班的暖身與手眼協調練習，下課等家長時也能玩。"),
        ],
        "specs": [
            ("組成", "投影機、擊球感應器、遊戲主機與內容"),
            ("投影", "3800 流明、XGA（1024×768）、長焦鏡頭"),
            ("安裝方式", "吊掛在牆前上方，投在平整牆面"),
            ("電源", "110–240V，可直接使用台灣電壓；功率約 300W"),
            ("互動方式", "擊中位置感應，即時判定"),
        ],
        "ops": False,
        "faq": [
            ("要用什麼球？", "一般用海洋球或軟球，安全、也不會傷到牆面。"),
            ("牆面有什麼要求？", "平整、淺色的牆面效果最好。牆面材質與尺寸可以先拍照給我們，我們會建議投影位置。"),
            ("會不會危險？", "用軟球就沒有危險；音量也可以依場地調整。"),
        ],
        "related": ["climb", "floor", "mobile"],
    },
    {
        "slug": "climb", "code": "Climb", "name": "互動攀岩牆", "cats": ["運動", "親子"],
        "card": "在攀岩牆投上遊戲目標，摸到就得分、計時比速度，攀岩變成闖關與比賽。",
        "title": "互動攀岩牆｜投影攀岩遊戲，摸到目標就得分",
        "desc": "DC Climb 互動攀岩牆把遊戲投影在攀岩牆上，攀爬時摸到目標就得分、計時，把攀岩變成闖關與比賽。裝在既有岩牆上即可使用，適合攀岩館、親子館、運動中心與學校。",
        "h1": ["互動攀岩牆：", "攀岩變成闖關、", "摸到目標就得分"],
        "lead": "投影機把目標、路線與計時投在攀岩牆上，感應器偵測手摸到哪裡。爬上去摸到目標就得分，還能計時比速度，第一次攀岩的孩子有明確目標，常客也有新挑戰。",
        "facts": ["裝在既有攀岩牆上", "計分、計時、比速度", "單通道或多通道", "台灣在地安裝與維修"],
        "features": [
            ("既有岩牆就能用", "投影與感應裝在牆前，不用換掉現有的攀岩牆與岩點。"),
            ("有目標更想爬", "遊戲化的目標與路線，降低新手的害怕，也讓常客一直有新玩法。"),
            ("計時比賽", "速度賽、計分賽，適合辦活動、比賽與生日派對。"),
            ("單通道到多通道", "依岩牆寬度選擇一條或多條賽道，同時進行。"),
        ],
        "games_title": "遊戲內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["摸目標得分", "速度攀爬計時", "收集星星", "打怪獸", "雙人對戰"],
        "for": [
            ("攀岩館、抱石館", "兒童班與新手的入門遊戲，也能辦親子活動與比賽。"),
            ("親子館、室內遊樂場", "讓攀岩區多一種玩法，孩子願意一爬再爬。"),
            ("學校、運動中心", "體育課與營隊的攀爬活動，有計分更有參與感。"),
        ],
        "specs": [
            ("組成", "投影機、感應器、遊戲主機與內容"),
            ("安裝方式", "投影與感應裝在岩牆前方，不需更換岩牆"),
            ("配置", "單通道；可選配多通道"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內攀岩牆、抱石牆"),
            ("安全", "沿用攀岩場原有的確保系統與軟墊"),
        ],
        "ops": True,
        "faq": [
            ("一定要有攀岩牆嗎？", "是的，DC Climb 是加在攀岩牆上的互動系統。還沒有岩牆的話，可以一起討論整體配置。"),
            ("安全怎麼處理？", "投影不會改變攀岩本身，仍然要搭配確保系統或抱石軟墊，依攀岩場原有的安全規範操作。"),
            ("可以多人比賽嗎？", "可以選配多通道，多條賽道同時計時、比速度。"),
        ],
        "related": ["ballwall", "trainer", "golf"],
    },
    {
        "slug": "golf", "code": "Golf", "name": "互動高爾夫模擬器", "cats": ["運動"],
        "card": "專業擊球幕布加投影，室內就能揮桿：練習場練穩定度，球場模式和朋友打一輪。",
        "title": "互動高爾夫模擬器｜室內揮桿練習與娛樂",
        "desc": "DC Golf 互動高爾夫模擬器在室內架起專業擊球幕布與投影，揮桿擊球後即時顯示結果，可以練習、也能和朋友打一輪。適合運動中心、球館、企業、會館與娛樂場所，可搭配線上預約按時段出租。",
        "h1": ["互動高爾夫模擬器：", "不用下場，", "室內就能揮桿"],
        "lead": "專業擊球幕布加上投影與感應，室內就能揮桿擊球、即時看到結果。練習場模式練穩定度，球場模式和朋友打一輪；下雨、天黑都不受影響。",
        "facts": ["專業擊球幕布", "練習與球場模式", "適合按時段出租", "台灣在地安裝與維修"],
        "features": [
            ("全天候", "不受天氣與日照影響，晚上、雨天照樣打。"),
            ("練習與娛樂兩用", "練習場模式練揮桿，球場與挑戰模式適合朋友同樂。"),
            ("按時段出租", "搭配 Digital Court 時段預約，按小時出租包廂，球友線上預約付款。"),
            ("依空間配置", "依天花板高度與空間深度，規劃幕布與擊球區的位置。"),
        ],
        "games_title": "模式",
        "games_lead": "以下為模式示例，實際依版本而定。",
        "games": ["練習場", "球場模式", "挑戰遊戲", "多人輪流比賽"],
        "for": [
            ("運動中心、球館", "多一種可以出租的運動項目，離峰時段也有收入。"),
            ("企業、會館、飯店", "會員設施與招待空間，不用出門就能打球。"),
            ("娛樂場所、餐酒館", "包廂娛樂，邊吃邊打、朋友聚會更有話題。"),
        ],
        "specs": [
            ("組成", "擊球幕布、投影機、擊球感應、主機與軟體"),
            ("模式", "練習場、球場與挑戰遊戲"),
            ("空間", "揮桿需要足夠的天花板高度與深度，場勘時確認"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內"),
        ],
        "ops": True,
        "faq": [
            ("天花板要多高？", "揮桿需要足夠高度，通常要 3 公尺左右，實際依場地與使用者身高確認，場勘時會量測。"),
            ("可以用自己的球桿嗎？", "可以，用一般的高爾夫球桿與球就能打。"),
            ("跟職業級模擬器有什麼不同？", "這款定位在娛樂與日常練習，價格親民、安裝單純；需要職業級擊球數據分析的話，留言告訴我們，我們一起評估。"),
        ],
        "related": ["trainer", "climb", "immersive"],
    },
    {
        "slug": "mobile", "code": "Mobile", "name": "移動互動投影車", "cats": ["親子", "教育", "商業"],
        "card": "投影機、感應器、主機裝在一台推車上，推到哪、插電就能玩地面互動遊戲，不用施工吊裝。",
        "title": "移動互動投影車｜地面互動遊戲推車，插電即用",
        "desc": "DC Mobile 移動互動投影車把投影機、動作感應與遊戲主機整合在一台推車上，推到教室、大廳或活動現場，插電就能投出會跟著腳步互動的地面遊戲。適合幼兒園、特教與早療、親子館、商場與活動。",
        "h1": ["移動互動投影車：", "推到哪、", "插電就能玩"],
        "lead": "投影機、動作感應器與遊戲主機整合在同一台推車上。推到教室、大廳或活動現場，插上電就能在地上投出會跟著腳步變化的互動遊戲，不用吊天花板、不用施工。",
        "facts": ["不用施工吊裝", "一台多用、隨處移動", "內建多款互動遊戲", "台灣在地安裝與維修"],
        "features": [
            ("一體成型、免施工", "投影、感應、主機都在推車裡，不用鑽孔吊掛；租來的場地或常換位置也能用。"),
            ("地面互動", "踩、跑、跳都會被偵測：魚群會散開、泡泡會破、落葉會飛起來。"),
            ("遊戲隨時換", "從情境、益智到運動類遊戲，依年齡與課程挑選。"),
            ("上課辦活動都好用", "平日上課、週末辦活動，同一台推過去就能用。"),
        ],
        "games_title": "遊戲內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["海浪與魚群", "踩泡泡", "落葉與花海", "打地鼠", "跳格子", "足球射門", "顏色與數字"],
        "for": [
            ("幼兒園、親子館", "下雨天也能在室內跑跳，邊玩邊認識顏色、數字。"),
            ("特教、早療、感統教室", "多情境、多感官的互動，搭配課程做手眼協調與動作練習。"),
            ("商場、活動、夜市", "推到人潮處當引流設施，週末活動、品牌快閃都能用。"),
        ],
        "specs": [
            ("組成", "投影機、動作感應器、遊戲主機、移動推車"),
            ("機型", "高款、矮款（依投影面積與擺放空間選擇）"),
            ("互動方式", "地面投影，偵測踩踏與移動"),
            ("內容", "多款互動遊戲，可洽談客製內容"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內，光線不要太強的空間"),
        ],
        "ops": False,
        "faq": [
            ("需要多大的空間？", "投影面積依機型與擺放方式而定，一般教室或大廳就放得下。告訴我們空間尺寸，我們會建議機型。"),
            ("可以投在牆上嗎？", "這台以地面互動為主。需要牆面互動，可以看 DC BallWall 砸球互動牆或 DC Sense 感統互動教室。"),
            ("遊戲可以更新嗎？", "可以，內容可以更新，也能洽談客製，例如加上單位 Logo、主題活動。"),
        ],
        "related": ["sense", "floor", "sandbox"],
    },
    {
        "slug": "floor", "code": "Floor", "name": "地面互動投影", "cats": ["商業", "親子"],
        "card": "走過去畫面就會動：魚群散開、花朵綻放，還有保齡球、跳一跳等地面遊戲；有戶外防水機型。",
        "title": "地面互動投影｜商場、餐廳、展場引流，室內戶外都有機型",
        "desc": "DC Floor 地面互動投影把會跟著腳步變化的畫面投在地上：魚群散開、花朵綻放、踩泡泡，也有保齡球、跳一跳等遊戲。室內吊掛與戶外防水機型，適合商場、餐廳、飯店、展場、公園與活動。",
        "h1": ["地面互動投影：", "走過去，", "地板就會跟著動"],
        "lead": "投影機與感應器裝在上方，把互動畫面投在地上。有人走過，魚群會散開、花朵會綻放；換成遊戲模式，還能玩保齡球、跳一跳。室內吊掛、戶外防水機型都有，是商場、餐廳、展場最直接的引流設施。",
        "facts": ["室內與戶外防水機型", "情境畫面與遊戲兩用", "可放品牌 Logo", "台灣在地安裝與維修"],
        "features": [
            ("吸睛引流", "會動的地面讓路過的人停下來、拍照分享，適合入口、走道與等候區。"),
            ("遊戲模式", "保齡球、跳一跳、踩泡泡等地面遊戲，大人小孩都能玩。"),
            ("戶外也能用", "戶外機型有防水恆溫機箱，公園、廣場、夜間活動都能投。"),
            ("品牌客製", "畫面可以加上品牌 Logo、節慶主題與活動訊息。"),
        ],
        "games_title": "畫面與遊戲",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["魚池與海浪", "花海", "踩泡泡", "保齡球", "跳一跳", "足球", "品牌 Logo 互動"],
        "for": [
            ("商場、百貨", "入口與中庭的互動地景，節慶換主題就有新話題。"),
            ("餐廳、飯店、宴會廳", "等候區、兒童區、婚宴入場的互動地面。"),
            ("公園、景區、夜間活動", "戶外防水機型，傍晚與夜間的投影效果最好。"),
        ],
        "specs": [
            ("機型", "室內吊掛型；戶外防水型（含防水恆溫機箱）"),
            ("投影", "依投影面積選擇亮度，戶外建議雷射投影機"),
            ("互動方式", "地面踩踏、移動感應"),
            ("內容", "情境畫面與遊戲，可客製品牌內容"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內各種地面；戶外以夜間或遮陰處效果最好"),
        ],
        "ops": False,
        "faq": [
            ("戶外白天看得到嗎？", "投影在強烈日光下會變淡，戶外以傍晚、夜間或遮陰處效果最好；需要白天使用，我們會依場地建議投影亮度。"),
            ("地面材質有限制嗎？", "淺色、霧面的地面效果最好；深色或反光的地面，可以加鋪投影地墊。"),
            ("可以放我們的 Logo 嗎？", "可以，畫面與活動主題都能洽談客製。"),
        ],
        "related": ["mobile", "immersive", "draw"],
    },
    {
        "slug": "sandbox", "code": "Sand", "name": "AR 互動沙桌", "cats": ["親子", "教育"],
        "card": "把沙堆高就變成山、挖低就變成海，投影即時畫出顏色、等高線與水流。",
        "title": "AR 互動沙桌｜堆沙即時變地形的親子與教學設備",
        "desc": "DC Sand AR 互動沙桌用深度感應偵測沙子的高低，即時投影出山、海、等高線與水流。孩子邊玩沙邊認識地形，適合親子館、幼兒園、科學教室與特教早療。",
        "h1": ["AR 互動沙桌：", "堆高變成山、", "挖低變成海"],
        "lead": "感應器偵測沙子的高低，投影機即時把顏色、等高線、水流投在沙上：堆高就長出山和雪，挖低就變成湖和海。孩子玩沙的同時，自然認識地形、顏色與空間。",
        "facts": ["即時偵測沙面高低", "玩沙同時學地形", "桌型一體設計", "台灣在地安裝與維修"],
        "features": [
            ("即時地形", "沙子一動，顏色與等高線馬上跟著變，像在捏一座真的島。"),
            ("寓教於樂", "地形、水循環、火山等主題，可以搭配自然與地理課。"),
            ("觸覺與專注", "玩沙本身就是很好的觸覺與手部活動，適合感統課程。"),
            ("一體桌型", "沙桌、投影、感應整合在一起，放好接電就能用。"),
        ],
        "games_title": "主題內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["地形與等高線", "湖泊與海洋", "火山", "捕魚遊戲", "恐龍世界", "四季變化"],
        "for": [
            ("親子館、室內遊樂場", "大人小孩都會圍過來玩的展示型設備。"),
            ("幼兒園、科學教室", "地形、水循環的體驗式教學。"),
            ("特教、早療、感統", "觸覺刺激與手部操作，孩子專注時間更長。"),
        ],
        "specs": [
            ("組成", "沙桌、投影機、深度感應器、主機與內容"),
            ("互動方式", "偵測沙面高低與手部動作"),
            ("內容", "地形、水流與多款主題遊戲"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內"),
        ],
        "ops": False,
        "faq": [
            ("沙子要另外準備嗎？", "我們會說明建議的沙子種類與用量，交機時一起確認。"),
            ("沙子會弄得到處都是嗎？", "沙桌有圍邊，建議搭配地墊並定期整理。"),
            ("可以幾個孩子一起玩？", "沙桌四周都能站人，可以多人同時玩。"),
        ],
        "related": ["draw", "sense", "mobile"],
    },
    {
        "slug": "draw", "code": "Draw", "name": "魔法塗鴉牆", "cats": ["親子", "教育"],
        "card": "孩子在紙上畫好、掃描一下，自己畫的魚和汽車就跑進牆上的動畫世界。",
        "title": "魔法塗鴉牆｜畫好掃描就動起來的互動投影",
        "desc": "DC Draw 魔法塗鴉牆讓孩子在紙上著色、掃描後，自己畫的魚、恐龍、汽車就出現在牆上的動畫世界裡游動、奔跑，還能用手互動。適合親子館、圖書館、展場、幼兒園與品牌活動。",
        "h1": ["魔法塗鴉牆：", "自己畫的魚，", "游進牆上的海洋"],
        "lead": "孩子在主題畫紙上著色，掃描後幾秒鐘，自己畫的魚、恐龍、汽車就出現在牆上的動畫世界裡，帶著自己的顏色游來游去，摸一下還會有反應。",
        "facts": ["畫好掃描就上牆", "多種主題畫紙", "多人同時創作", "台灣在地安裝與維修"],
        "features": [
            ("自己的作品會動", "每個孩子的畫都獨一無二，看到作品上牆特別有成就感。"),
            ("主題可以換", "海洋、恐龍、交通、節慶等主題，配合季節活動更新。"),
            ("手也能互動", "摸一下牆上的作品會有反應，畫完還能繼續玩。"),
            ("活動好幫手", "親子活動、生日派對、展覽與品牌活動，大人小孩都會停下來看。"),
        ],
        "games_title": "主題內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["海底世界", "恐龍樂園", "城市交通", "叢林動物", "節慶主題", "客製品牌主題"],
        "for": [
            ("親子館、幼兒園", "美勞課與互動遊戲合在一起，作品不再只能貼在牆上。"),
            ("圖書館、美術館、展場", "結合展覽主題的互動體驗。"),
            ("商場、品牌活動", "吉祥物、節慶主題的客製畫紙，活動有記憶點。"),
        ],
        "specs": [
            ("組成", "投影機、掃描設備、主機與內容、主題畫紙"),
            ("互動方式", "掃描畫作上牆、手部觸碰互動"),
            ("內容", "多款主題，可客製"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內牆面"),
        ],
        "ops": False,
        "faq": [
            ("畫紙用完怎麼辦？", "我們會提供主題畫紙，補充方式交機時說明。"),
            ("可以做成我們的主題嗎？", "可以洽談客製，例如品牌吉祥物、節慶或展覽主題。"),
            ("需要專人操作嗎？", "掃描與上牆都很簡單，現場人員看一次就會；交機時我們會教學。"),
        ],
        "related": ["sandbox", "mobile", "floor"],
    },
    {
        "slug": "sense", "code": "Sense", "name": "感統互動教室", "cats": ["教育"],
        "card": "牆面加地面的 L 型互動投影，多情境、多感官的感統、手眼協調與互動繪本課程。",
        "title": "感統互動教室｜L 型牆面＋地面互動投影，特教早療適用",
        "desc": "DC Sense 感統互動教室用牆面加地面的 L 型投影，打造多情境、多感官的互動空間，搭配手眼協調、動作與認知遊戲、互動繪本。適合特教學校與資源班、早療機構、感覺統合教室與幼兒園。",
        "h1": ["感統互動教室：", "牆面加地面，", "一間教室多種情境"],
        "lead": "牆面與地面同時投影，孩子就站在情境裡：踩、跳、拍、丟都會有回應。搭配手眼協調、動作、認知配對與互動繪本內容，讓課程更有趣，孩子更願意參與。",
        "facts": ["牆面＋地面 L 型投影", "多情境、多感官", "互動繪本與課程內容", "台灣在地安裝與教學"],
        "features": [
            ("L 型沉浸空間", "牆面與地面一起投影，孩子像走進故事裡。"),
            ("多感官回應", "畫面與聲音同時回應動作，適合手眼協調與動作練習。"),
            ("課程內容", "認知配對、顏色形狀、互動繪本、科學小實驗等主題。"),
            ("老師好操作", "一鍵切換情境與遊戲，課程節奏由老師掌握。"),
        ],
        "games_title": "課程內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["手眼協調遊戲", "認知配對", "互動繪本", "情境探索", "科學小實驗", "動作模仿"],
        "for": [
            ("特教學校、資源班", "把課程變成遊戲，提升參與度。"),
            ("早療機構、感覺統合教室", "多情境、多感官的活動空間，輔助課程進行。"),
            ("幼兒園、課後照顧", "下雨天的室內體能與認知活動。"),
        ],
        "specs": [
            ("配置", "牆面＋地面 L 型投影（一體式）"),
            ("互動方式", "牆面觸碰、地面踩踏感應"),
            ("內容", "多情境遊戲、互動繪本、課程主題，可客製"),
            ("電源", "出貨前確認符合台灣 110V"),
            ("適用場地", "室內教室，可遮光效果最好"),
            ("教學", "交機時提供教師操作教學"),
        ],
        "ops": False,
        "faq": [
            ("這是醫療器材嗎？", "不是。DC Sense 是互動教學與活動設備，用來輔助課程與活動，不能取代專業治療。"),
            ("教室要多大？", "依牆面寬度與地面投影範圍配置。留言提供教室尺寸，我們會給建議。"),
            ("可以配合學校或機構的採購流程嗎？", "可以，我們會提供報價單與規格資料，配合採購流程。"),
        ],
        "related": ["mobile", "sandbox", "draw"],
    },
    {
        "slug": "immersive", "code": "Immersive", "name": "沉浸式投影空間", "cats": ["商業"],
        "card": "牆面、地面、天花板一起投影，一鍵把瑜伽教室、宴會廳、展廳變成森林、海底或星空。",
        "title": "沉浸式投影空間｜瑜伽、美容、宴會、展廳的 360 度投影",
        "desc": "DC Immersive 沉浸式投影空間用多台投影機把牆面、地面與天花板連成一個 360 度的畫面，森林、海底、星空隨時切換。適合瑜伽與皮拉提斯教室、美容與 SPA、宴會廳與餐廳、展廳與企業接待。",
        "h1": ["沉浸式投影空間：", "一鍵把教室變成", "森林、海底或星空"],
        "lead": "多台投影機把牆面、地面、天花板接成一個完整畫面，空間一鍵換成森林、海底、星空或品牌主題。瑜伽課多了情境，宴會與展廳多了話題，空間不用重新裝潢。",
        "facts": ["牆面、地面、天花板 360 度", "情境一鍵切換", "依空間客製規劃", "台灣在地安裝與維修"],
        "features": [
            ("不用重新裝潢", "換畫面就換主題，同一個空間可以有很多種面貌。"),
            ("課程有情境", "瑜伽、冥想、皮拉提斯配上森林、海浪、星空，課程更有記憶點。"),
            ("宴會與活動", "婚宴入場、尾牙、品牌發表會的主題投影，可以加上互動效果。"),
            ("依空間規劃", "依空間尺寸與天花板高度，規劃投影機數量與位置。"),
        ],
        "games_title": "情境內容",
        "games_lead": "以下為內容示例，實際依版本而定。",
        "games": ["森林", "海底", "星空", "極光", "花海", "品牌主題", "餐桌投影（選配）"],
        "for": [
            ("瑜伽、皮拉提斯、冥想教室", "同一間教室，不同課程配不同情境。"),
            ("美容、SPA、會館", "放鬆的光影情境，提升空間質感。"),
            ("宴會廳、餐廳、展廳", "主題宴會、沉浸式用餐、企業接待與展覽。"),
        ],
        "specs": [
            ("配置", "依空間規劃投影機數量（牆面、地面、天花板）"),
            ("內容", "情境畫面庫，可客製品牌主題，可加互動效果"),
            ("選配", "餐桌投影"),
            ("電源", "依投影機數量規劃"),
            ("適用場地", "室內，可遮光的空間效果最好"),
            ("價格", "依空間規劃專案報價"),
        ],
        "ops": True,
        "faq": [
            ("空間要多大？", "從小型教室到宴會廳都能規劃，空間越大需要的投影機越多。提供平面圖與照片，我們會評估。"),
            ("白天可以用嗎？", "可遮光的空間效果最好；有大面窗戶的話，需要窗簾或調整投影亮度。"),
            ("內容可以自己換嗎？", "可以，在操作介面就能切換情境；也能洽談客製品牌內容。"),
        ],
        "related": ["floor", "golf", "draw"],
    },
]

ALL = [BOOKING, TRAINER] + PRODUCTS
BY_SLUG = {p["slug"]: p for p in ALL}
GRID_ORDER = ["ballwall", "climb", "golf", "mobile", "floor", "sandbox", "draw", "sense", "immersive"]
e = html.escape


def label(p):
    return f"DC {p['code']} {p['name']}"


# ---------------------------------------------------------------- 共用片段

NAV = [("/#products", "全部產品", ""), ("/booking", "預約系統", ""), ("/trainer", "匹克球訓練機", ""),
       ("/#solutions", "解決方案", "opt"), ("/#faq", "常見問題", "opt")]


def header(current="", cta=("/#contact", "洽詢報價"), nav=None):
    nav = nav or NAV
    links = "\n".join(
        f'      <a{" class=" + chr(34) + c + chr(34) if c else ""} href="{h}"{" aria-current=" + chr(34) + "page" + chr(34) if h == current else ""}>{t}</a>'
        for h, t, c in nav)
    menu = "".join(f'<a href="{h}">{t}</a>' for h, t, _ in nav) + f'<a href="{cta[0]}">{cta[1]}</a>'
    return f"""<header class="top">
  <div class="wrap">
    <a class="brand" href="/" aria-label="Digital Court 首頁"><img src="/favicon.svg" alt="" width="30" height="30">Digital Court</a>
    <nav class="nav" aria-label="主選單">
{links}
    </nav>
    <details class="menu"><summary aria-label="選單">☰</summary><nav aria-label="選單">{menu}</nav></details>
    <a class="btn" href="{cta[0]}">{cta[1]}</a>
  </div>
</header>"""


def footer():
    sport = ["booking", "trainer", "ballwall", "climb", "golf"]
    proj = ["mobile", "floor", "sandbox", "draw", "sense", "immersive"]
    li = lambda s: f'<li><a href="/{s}">{e(BY_SLUG[s]["name"])}</a></li>'  # noqa: E731
    return f"""<footer>
  <div class="wrap">
    <div class="cols">
      <div><h4>Digital Court</h4><p>互動運動設備與場館預約系統。設備的台灣銷售、安裝、繁體中文內容與維修，都由我們負責。</p><p style="margin-top:8px"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
      <div><h4>運動與場館</h4><ul>{"".join(li(s) for s in sport)}</ul></div>
      <div><h4>互動投影</h4><ul>{"".join(li(s) for s in proj)}</ul></div>
      <div><h4>場館帳號</h4><ul><li><a href="/signup">免費試用 7 天</a></li><li><a href="/account">場主登入</a></li><li><a href="/terms">服務條款</a></li><li><a href="/privacy">隱私權政策</a></li><li><a href="/report">檢舉</a></li></ul></div>
    </div>
    <div class="legal"><span>© 2026 Digital Court</span><span>產品圖片與規格以實際出貨為準</span></div>
  </div>
</footer>"""


def tile(p, soft=False, sub=None):
    return (f'<div class="ph" aria-hidden="true"><span class="dc">DC</span><span class="ring"></span>'
            f'<span class="pn"><b>DC {e(p["code"])}</b><span>{e(sub or p["name"])}</span></span></div>')


def shot(p, kind="", lazy=True, alt=None):
    src = f'/img/{p["slug"]}{"-" + kind if kind else ""}.webp'
    alt = alt if alt is not None else f'{label(p)}{"使用情境" if kind == "scene" else ""}'
    return (f'<div class="shot{" soft" if kind == "scene" else ""}"><img src="{src}" alt="{e(alt)}" width="1536" height="1024"'
            f'{" loading=" + chr(34) + "lazy" + chr(34) if lazy else ""} onerror="this.remove()">{tile(p, kind == "scene")}</div>')


def card(p, big=False):
    tags = "".join(f'<span class="tag">{c}</span>' for c in p["cats"])
    go = "看預約系統 →" if p["slug"] == "booking" else "看產品介紹 →"
    return (f'<a class="pcard" href="/{p["slug"]}" data-cats="{" ".join(p["cats"])}">{shot(p)}'
            f'<div class="body"><div class="tags">{tags}</div><h3><small>DC {e(p["code"])}</small>{e(p["name"])}</h3>'
            f'<p>{e(p["card"])}</p><span class="go">{go}</span></div></a>')


VENUE_TYPES = ["匹克球館／運動中心", "親子館／室內遊樂場", "學校／幼兒園／補習班", "特教／早療／感統", "商場／餐廳／展場",
               "企業／飯店／會館", "瑜伽／美容／健身", "經銷合作", "其他"]


def lead_form(topic="", products=False):
    venue = "".join(f"<option>{v}</option>" for v in VENUE_TYPES)
    if products:
        picks = "".join(f'<label><input type="checkbox" name="products" value="{e(p["name"])}"> {e(p["name"])}</label>' for p in ALL)
        pick = f'<fieldset><legend>想了解的產品 <small>可複選</small></legend><div class="checks">{picks}</div></fieldset>'
    else:
        needs = ["價格", "規格與尺寸", "空間配置／場勘", "客製內容", "搭配線上預約"]
        pick = ('<fieldset><legend>想了解 <small>選填、可複選</small></legend><div class="checks">'
                + "".join(f'<label><input type="checkbox" name="needs" value="{n}"> {n}</label>' for n in needs) + "</div></fieldset>")
    return f"""<form class="lead-form" data-topic="{e(topic)}" novalidate>
        <label>稱呼 <input name="name" autocomplete="name" required maxlength="40" placeholder="例：王經理"></label>
        <label>聯絡方式 <small>LINE ID、手機或 Email 都可以</small><input name="contact" required maxlength="100" placeholder="例：LINE ID wang123"></label>
        <label>單位名稱 <small>選填</small><input name="org" autocomplete="organization" maxlength="80" placeholder="例：○○匹克球館、○○幼兒園"></label>
        <label>場地類型 <select name="size"><option value="">請選擇</option>{venue}</select></label>
        <div class="pair">
          <label>地區 <small>選填</small><input name="area" maxlength="12" placeholder="例：台中市"></label>
          <label>預計台數 <small>選填</small><select name="qty"><option value="">請選擇</option><option>1 台</option><option>2～4 台</option><option>5 台以上</option><option>還在評估</option></select></label>
        </div>
        {pick}
        <label>想說的話 <small>選填</small><textarea name="message" rows="3" maxlength="1000" placeholder="例：場館有一個閒置角落，想了解需要多大空間"></textarea></label>
        <label class="hp" aria-hidden="true">網站 <input name="website" tabindex="-1" autocomplete="off"></label>
        <button class="btn" type="submit">送出</button>
        <p class="privacy">你填的資料只用來聯絡你、提供報價，不會提供給其他人。</p>
        <p class="form-msg" role="status" hidden></p>
      </form>"""


def related(slugs):
    return '<div class="pgrid">' + "".join(card(BY_SLUG[s]) for s in slugs) + "</div>"


# ---------------------------------------------------------------- 產品頁

def head(p):
    url = f"{SITE}/{p['slug']}"
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "@id": f"{url}#page", "url": url, "name": p["title"], "inLanguage": "zh-Hant-TW",
             "isPartOf": {"@id": f"{SITE}/#website"}, "breadcrumb": {"@id": f"{url}#crumbs"}},
            {"@type": "BreadcrumbList", "@id": f"{url}#crumbs", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Digital Court", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": p["name"], "item": url}]},
            {"@type": "FAQPage", "@id": f"{url}#faq", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p["faq"]]},
        ],
    }
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(p["title"])}｜Digital Court</title>
<meta name="description" content="{e(p["desc"])}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-48.png" sizes="48x48" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="alternate" type="text/plain" href="/llms.txt" title="LLM 摘要">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Digital Court">
<meta property="og:title" content="DC {e(p["code"])} {e(p["name"])}｜Digital Court">
<meta property="og:description" content="{e(p["card"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og-home.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="zh_TW">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<link rel="stylesheet" href="/brand.css">
</head>"""


OPS = """
  <section class="band" id="ops" aria-labelledby="ops-title">
    <div class="wrap ops">
      <div>
        <p class="eyebrow">營運方式</p>
        <h2 id="ops-title">按時段出租、賣次數卡，用 Digital Court 預約系統就能做</h2>
        <p class="lead">設備可以單獨購買。想讓它自己賺錢，可以搭配我們的預約系統：球友線上選時段、付款，你在後台對帳。</p>
      </div>
      <div class="side">
        <ul>
          <li><b>計時出租</b><span>用「時段預約」開成例如每 30 分鐘一段，球友線上挑時段，匯款後回填後五碼，你在後台對帳。</span></li>
          <li><b>次數卡</b><span>賣 10 次卡這類課卡，每次預約自動扣次數，常客不用每次付款。</span></li>
          <li><b>LINE 通知</b><span>預約成功、開始前一天的提醒都推到球友的 LINE。</span></li>
        </ul>
        <div class="dark"><b>DC Booking 預約報名系統</b><p>每月 NT$490 起，可以先免費試用 7 天、不用信用卡。</p><a class="btn" href="/booking">看預約系統 →</a></div>
      </div>
    </div>
  </section>
"""


def product_page(p):
    h1 = "".join(f'<span class="nw">{e(x)}</span>' for x in p["h1"])
    facts = "".join(f"<li>{e(x)}</li>" for x in p["facts"])
    feats = "".join(f'<article class="card"><h3>{e(t)}</h3><p>{e(d)}</p></article>' for t, d in p["features"])
    games = "".join(f"<li>{e(g)}</li>" for g in p["games"])
    fors = "".join(f'<article class="card"><h3>{e(t)}</h3><p>{e(d)}</p></article>' for t, d in p["for"])
    specs = p["specs"] + [("售後服務", "在地安裝、教學、保固與維修（依合約）")]
    if not any(k == "價格" for k, _ in specs):
        specs.append(("價格", "依數量與配置專人報價"))
    dl = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in specs)
    faq = "".join(f"<details{' open' if i == 0 else ''}><summary>{e(q)}</summary><p>{e(a)}</p></details>"
                  for i, (q, a) in enumerate(p["faq"]))
    band_specs = "" if p["ops"] else ' class="band"'
    return f"""{head(p)}
<body>
<!--gen:header-->
{header(f"/{p['slug']}", ("#contact", "洽詢報價"))}
<!--/gen:header-->

<main>
  <section class="hero" aria-labelledby="hero-title">
    <div class="wrap">
      <div>
        <p class="eyebrow">DC {e(p["code"])}・{e("・".join(p["cats"]))}</p>
        <h1 id="hero-title">{h1}</h1>
        <p class="lead">{e(p["lead"])}</p>
        <div class="ctas">
          <a class="btn" href="#contact">洽詢報價</a>
          <a class="btn ghost" href="#specs">看規格</a>
        </div>
        <ul class="facts" aria-label="重點">{facts}</ul>
      </div>
      {shot(p, lazy=False)}
    </div>
  </section>

  <section id="features" aria-labelledby="features-title">
    <div class="wrap">
      <p class="eyebrow">特色</p>
      <h2 id="features-title">為什麼選 DC {e(p["code"])}</h2>
      <div class="grid2">{feats}</div>
    </div>
  </section>

  <section class="band" id="games" aria-labelledby="games-title">
    <div class="wrap split">
      <div>
        <p class="eyebrow">{e(p["games_title"])}</p>
        <h2 id="games-title">{e(p["games_title"])}</h2>
        <p class="lead">{e(p["games_lead"])}</p>
        <ul class="games">{games}</ul>
      </div>
      {shot(p, "scene")}
    </div>
  </section>

  <section id="for" aria-labelledby="for-title">
    <div class="wrap">
      <p class="eyebrow">適合場所</p>
      <h2 id="for-title">誰在用 DC {e(p["code"])}</h2>
      <div class="grid3">{fors}</div>
    </div>
  </section>
{OPS if p["ops"] else ""}
  <section{band_specs} id="specs" aria-labelledby="specs-title">
    <div class="wrap specs">
      <div>
        <p class="eyebrow">規格與配置</p>
        <h2 id="specs-title">組成與規格</h2>
        <p class="lead">每個場地的空間、光線與用途都不一樣。留言給我們場地照片或安排場勘，我們會提供配置建議與報價。</p>
        <p class="note">規格以實際出貨型號為準。</p>
      </div>
      <dl>{dl}</dl>
    </div>
  </section>

  <section id="faq" aria-labelledby="faq-title">
    <div class="wrap">
      <p class="eyebrow">常見問題</p>
      <h2 id="faq-title">常見問題</h2>
      <div class="faq">{faq}</div>
    </div>
  </section>

  <section class="band" id="contact" aria-labelledby="contact-title">
    <div class="wrap apply">
      <div>
        <p class="eyebrow">洽詢報價</p>
        <h2 id="contact-title">告訴我們你的場地，我們提供配置建議與報價</h2>
        <p class="lead">留下聯絡方式與場地類型，我們會盡快與你聯絡。也可以直接寫信到 <a href="mailto:{EMAIL}">{EMAIL}</a>。</p>
        <p class="note">有場地照片的話，聯絡時一起提供，配置建議會更準確。</p>
      </div>
      {lead_form(label(p))}
    </div>
  </section>

  <section aria-labelledby="more-title">
    <div class="wrap">
      <p class="eyebrow">其他產品</p>
      <h2 id="more-title">也可以看看</h2>
      {related(p["related"])}
      <p class="note"><a href="/#products">看全部產品 →</a></p>
    </div>
  </section>
</main>

<!--gen:footer-->
{footer()}
<!--/gen:footer-->
<script src="/brand.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- 手寫頁面的共用區塊

def replace_block(text, name, body):
    pat = re.compile(rf"(<!--gen:{name}-->\n)(?:.*?\n)?(<!--/gen:{name}-->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"找不到 <!--gen:{name}--> 區塊")
    return pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)


BOOKING_NAV = [("/#products", "全部產品", ""), ("#features", "功能", ""), ("#dupr", "DUPR 賽事", ""),
               ("#demos", "示範場館", "opt"), ("#pricing", "價格", ""), ("#faq", "常見問題", "opt")]


def update_handwritten():
    blocks = {
        "index.html": {"header": header(), "footer": footer(), "products": '<div class="pgrid" id="pgrid">'
                       + "".join(card(BY_SLUG[s]) for s in GRID_ORDER) + "</div>",
                       "featured": '<div class="feature2">' + card(BOOKING) + card(TRAINER) + "</div>",
                       "form": lead_form("", products=True)},
        "trainer.html": {"header": header("/trainer", ("#contact", "洽詢報價")), "footer": footer(),
                         "related": related(["ballwall", "golf", "climb"]), "form": lead_form(label(TRAINER))},
        "booking.html": {"header": header("", ("/signup", "免費試用 7 天"), BOOKING_NAV), "footer": footer()},
    }
    for name, parts in blocks.items():
        path = LANDING / name
        text = path.read_text()
        for k, v in parts.items():
            text = replace_block(text, k, v)
        path.write_text(text)


def sitemap():
    pages = ["", "booking", "trainer"] + GRID_ORDER + ["signup", "terms", "privacy"]
    rows = "\n".join(f"  <url><loc>{SITE}/{s}</loc><lastmod>{TODAY}</lastmod></url>" for s in pages)
    (LANDING / "sitemap-main.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n')


if __name__ == "__main__":
    for p in PRODUCTS:
        (LANDING / f"{p['slug']}.html").write_text(product_page(p))
    update_handwritten()
    sitemap()
    print("產品頁：", ", ".join(p["slug"] for p in PRODUCTS))
