# Scholaverse — 學習歷程卡牌瀏覽平台

> 教育部教學實踐研究計畫配套教學平台
> 課程：輔仁大學「人工智慧概論」

## 專案簡介

本平台將學生在 5 大學習單元的表現數據，透過評分轉換規則對應為 RPG 角色屬性（種族、職業、裝備、武器、背景、表情姿勢），再由 AI Worker 上的 LLM 與文生圖模型產生個性化角色卡牌。學生在課程中累積學習進度、贏得代幣，可以多次重抽卡牌，並在角色大廳與全班同學的角色合影。

## 系統架構

```
使用者 → Cloudflare Zero Trust → vm-web-server（本專案）
                                    ├→ vm-ai-worker  (GPU / LLM / 文生圖)
                                    └→ vm-db-storage (圖片 + Metadata)
```

- **vm-web-server**：FastAPI 應用，負責學生認證、學習數據管理、卡牌瀏覽、代幣與成就系統
- **vm-ai-worker**：接收學習數據與角色配置，由 LLM 生成 prompt 並呼叫文生圖模型（Stable Diffusion 或 OpenAI gpt-image-2）
- **vm-db-storage**：儲存生成的卡牌圖片與 Metadata

## 技術棧

| 類別 | 技術 |
|------|------|
| 後端框架 | Python 3.12+, FastAPI, uvicorn |
| 套件管理 | uv |
| 資料庫 | SQLite + SQLAlchemy (async) + aiosqlite |
| 模板引擎 | Jinja2 + HTMX |
| 前端樣式 | Tailwind CSS (CDN)、Pixel Art 像素風格、Lucide Icons |
| HTTP 客戶端 | httpx |
| 認證 | Cloudflare Zero Trust（header: `cf-access-authenticated-user-email`） |
| 測試 | pytest + pytest-asyncio |

## 專案結構

```
intro-ai/
├── main.py              # FastAPI app 入口
├── pyproject.toml       # uv 套件管理
├── app/
│   ├── config.py        # 設定管理（讀取 .env）
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # FastAPI 路由（pages / admin / generation / announcements / tokens / config / internal）
│   ├── services/        # 業務邏輯（auth, storage, ai_worker, scoring, system_settings）
│   ├── templates/       # Jinja2 模板
│   └── static/          # CSS, JS, fonts, images（含畫師立繪）
├── tests/               # pytest 測試
├── scripts/             # 工具腳本（seed data 等）
└── docs/                # 規格書
```

## 主要頁面

左側導覽列依以下順序呈現：

| 路徑 | 名稱 | 說明 |
|------|------|------|
| `/` | 儀表板 | 最新卡牌與單元學習進度概覽 |
| `/cards` | 我的卡牌 | 個人卡牌牌組（訪客顯示示範卡） |
| `/hall` | 角色大廳 | 全班同學的最新代表卡牌 |
| `/progress` | 學習歷程 | 6 大單元評量成績、可選屬性、卡牌生成入口 |
| `/token-rules` | 點數規則 | 代幣取得與消耗規則說明 |
| `/tokens` | 點數紀錄 | 個人代幣異動明細（需登入）|
| `/announcements` | 公會告示板 | 站務公告（需登入）|
| `/atelier` | 肖像繪製所 | 雙畫師世界觀，視覺化呈現當前生圖後端 |
| `/admin/*` | 管理後台 | 限 teacher / admin 角色 |

## 學習單元與角色屬性對應

| 單元代碼 | 學習主題 | 解鎖角色屬性 |
|----------|----------|--------------|
| unit_1 | 先備知識 | 種族、性別 |
| unit_2 | MLP | 職業、體型 |
| unit_3 | CNN | 服飾裝備 |
| unit_4 | RNN | 武器（受 unit_2 職業類別影響可選範圍） |
| unit_5 | 進階技術 | 背景場景 |
| unit_6 | 自主學習 | 表情、姿勢 |

每個單元可選的屬性選項數量與品質，由預習分數、完成率、隨堂測驗成績決定（詳見 `app/services/scoring.py`）。

## 圖片生成後端

平台支援雙生圖後端，由全域系統設定 `image_backend` 控制：

| 設定值 | 後端 | 特性 |
|--------|------|------|
| `local` | vm-ai-worker 上的 Stable Diffusion | 自架 GPU、無外部成本、無人物一致性 |
| `cloud` | OpenAI gpt-image-2 | 雲端 API、有成本、支援 image edit 跨卡牌維持人物容貌 |

設定保存在 SQLite `system_settings` 表，可由管理者於後台即時切換。`/atelier` 頁面會把當前後端對應的「畫師人格」（公會畫匠 vs 宮廷畫師）以金邊高亮，將技術切換包裝為 RPG 世界觀敘事。

## 代幣與成就

- **代幣（tokens）**：學生完成單元、提交評量、達成里程碑可獲得代幣；卡牌重抽會消耗代幣。所有異動寫入 `token_transactions` 並可在 `/tokens` 查看。
- **成就（achievements）**：解鎖條件式徽章（見 `app/models/achievement.py` 的 `ACHIEVEMENT_TYPES`），於個人 profile 頁顯示。

## 管理後台

`/admin` 路由限 `teacher` / `admin` 角色，主要功能：

| 路徑 | 功能 |
|------|------|
| `/admin` | 後台儀表板（班級總覽、近期生成、系統設定） |
| `/admin/students` | 學生管理（綁定 / 解綁、代幣調整、批次匯出） |
| `/admin/roster` | 修課名單匯入與管理 |
| `/admin/import` | Excel 批次匯入完成率與評量成績 |
| `/admin/rules` | 屬性解鎖規則檢視 |
| `/admin/simulation` | 模擬生圖：以偽學生身份送單測試 prompt 與後端 |
| `/admin/cards/{id}` | 卡牌詳情（含生圖後端、雲端品質等 metadata） |

`/api/admin/system-settings/{key}` 提供 image_backend / ollama_model 等全域設定的即時切換。

## 快速開始

### 環境需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### 安裝

```bash
uv sync
```

### 設定環境變數

```bash
cp .env.example .env
```

主要環境變數：

| 變數 | 說明 |
|------|------|
| `DATABASE_URL` | SQLite 路徑（預設 `./data/scholaverse.db`） |
| `AI_WORKER_BASE_URL` / `DB_STORAGE_BASE_URL` | 兩台後端 VM 位址 |
| `USE_MOCK_AI_WORKER` / `USE_MOCK_STORAGE` | 開發時不打 VM、改用 mock |
| `GUEST_MODE` | 開啟訪客模式（正式上線請設 `false`） |
| `CF_AUTH_HEADER` | Cloudflare Zero Trust 帶入的使用者 email header 名稱 |

### 初始化資料庫

```bash
# 學習單元基本資料
uv run python scripts/seed_data.py

# 屬性解鎖規則
uv run python scripts/seed_attribute_rules.py

# （選用）訪客模式示範資料
uv run python scripts/seed_demo_data.py
```

### 啟動開發伺服器

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 執行測試

```bash
uv run pytest tests/ -v
```

## 訪客模式

設定 `GUEST_MODE=true` 後，未認證（或已認證但未註冊）的使用者可以瀏覽所有示範頁面，無需學號綁定。

| 操作 | 訪客 | 已註冊學生 |
|------|------|-----------|
| 瀏覽儀表板 / 大廳 / 卡牌 / 學習歷程 / 肖像繪製所 | ✅ 顯示示範資料 | ✅ |
| 選擇角色屬性、生成卡牌、查看代幣 | ❌ | ✅ |
| 管理後台 | ❌ | ✅（限 teacher / admin） |

啟用步驟：

```bash
# 1. 在 .env 設定
GUEST_MODE=true

# 2. 匯入示範學生資料（首次需執行）
uv run python scripts/seed_demo_data.py

# 3. 重啟伺服器
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **正式上線前**請將 `GUEST_MODE` 改回 `false` 並重啟伺服器。

## UI 設計規範

- 像素風格 RPG 介面（Pixel Art）
- 配色（CSS 變數定義於 `app/static/css/style.css`）：
  - 深色背景 `--rpg-bg-dark` `#0f0c29`
  - 深綠面板 `--rpg-bg-panel` `#1e3a1a`
  - 卡片底色 `--rpg-bg-card` `#1a2e14`
  - 金色強調 `--rpg-gold` `#d4a847`
  - 亮金強調 `--rpg-gold-bright` `#ffd700`
- 標題字型：Press Start 2P（像素字型）
- 中文內文：Noto Sans TC
- 圖示：Lucide Icons
- 響應式斷點：`md` (768px) 起切雙欄、`lg` (1024px) 起回到桌機 sidebar 常駐

詳細規範見 [`docs/ui-design-spec.md`](docs/ui-design-spec.md)。

## 文件

- [`docs/system-spec.md`](docs/system-spec.md) — 完整系統規格書
- [`docs/ui-design-spec.md`](docs/ui-design-spec.md) — UI 設計規範
- [`docs/vm-ai-worker-spec.md`](docs/vm-ai-worker-spec.md) — AI Worker API 規格
