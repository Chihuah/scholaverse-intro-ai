# Scholaverse - 學習歷程卡牌瀏覽平台 (intro-ai)

## 專案概述

教育部教學實踐研究計畫「從學習評分到角色養成：生成式 AI 支持下的遊戲化教學實踐」的配套教學平台。為輔仁大學「人工智慧概論」課程開發，將學生在 5 大學習單元的表現數據，透過評分轉換規則對應為 RPG 角色屬性（種族、職業、裝備、武器、背景），再由 vm-ai-worker 上的 LLM + 文生圖模型產生個性化角色頭像卡牌。

- 網域：app.scholaverse.cc
- 部署位置：vm-web-server (192.168.50.111)
- 完整規格書：`docs/system-spec.md`

## 架構

```
使用者 → Cloudflare Zero Trust → vm-web-server (本專案, FastAPI)
                                    ├→ vm-ai-worker (192.168.50.110) - GPU/LLM/文生圖
                                    └→ vm-db-storage (192.168.50.112) - 圖片+Metadata
```

- vm-ai-worker 和 vm-db-storage 目前尚未建立，使用 mock/stub 開發
- vm-web-server 不負責生成 prompt，而是將學習數據+角色配置送給 vm-ai-worker，由其 LLM 產生 prompt 並生圖
- 所有 VM IP 為暫定，透過環境變數配置，不寫死在程式碼中

## 技術棧

- Python 3.12+, FastAPI, uvicorn
- 套件管理：**uv**（不使用 pip）
- 模板：Jinja2 + HTMX + Tailwind CSS (CDN)
- 資料庫：SQLite + SQLAlchemy (async) + aiosqlite
- HTTP 客戶端：httpx（與其他 VM 通信）
- 測試：pytest + pytest-asyncio
- 版本控制：Git + GitHub (repo: chihuah/scholaverse-intro-ai)

## 重要規則

- 所有套件安裝一律使用 `uv add`，禁止使用 pip
- 認證由 Cloudflare Zero Trust 處理，從 header `cf-access-authenticated-user-email` 取得使用者 email
- 未註冊的使用者導向自助註冊頁面（填學號+姓名綁定）
- 前端採用 Pixel Art 像素風格 RPG 介面（參考 ref/PixelArt_UI_example.jpeg）
- 配色：深色背景 #1a1a2e、深綠面板 #2d3a1a、金色強調 #d4a847
- 字型：像素字型 (Press Start 2P) 用於標題，Noto Sans TC 用於中文內文
- main.py 中現有的 HTML 內容是舊的佔位頁面，應被完全替換，不要參考其內容

## 專案結構

```
intro-ai/
├── main.py              # FastAPI app 入口（待重構）
├── pyproject.toml       # uv 套件管理
├── app/
│   ├── config.py        # 設定管理（讀取 .env）
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # FastAPI 路由
│   ├── services/        # 業務邏輯（auth, storage, ai_worker, scoring）
│   ├── templates/       # Jinja2 模板
│   └── static/          # CSS, JS, fonts, images
├── tests/               # pytest 測試
├── scripts/             # 工具腳本（seed data 等）
├── docs/                # 規格書
└── ref/                 # 參考文件（計畫書、UI 參考圖）
```

## 可用的 Skills

- `/ui-review [file]` — 審查前端 UI 是否符合像素 RPG 設計規範
- `/pixel-component <名稱>` — 生成符合設計規範的 HTML/CSS 元件
- `/responsive-check [file]` — 檢查響應式設計
- `/api-scaffold <名稱>` — 建立新的 FastAPI router 模組
- `/run-tests [path]` — 執行 pytest 測試

## 常用指令

```bash
uv sync                                          # 安裝依賴
uv add <package>                                 # 新增套件
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload  # 啟動開發伺服器
uv run pytest tests/ -v                          # 執行測試
```

## 資料模型

6 張核心資料表：students, units, learning_records, card_configs, cards, token_transactions
詳見 `docs/system-spec.md` 第 3 節

## 評分轉換

5 大學習單元各對應一項角色屬性：
- 單元 1 (先備知識) → 種族、性別
- 單元 2 (MLP) → 職業、體型
- 單元 3 (CNN) → 服飾裝備
- 單元 4 (RNN) → 武器
- 單元 5 (進階技術) → 背景場景
- 自主學習 → 表情、姿勢、外框

分數越高，可選選項越多、品質越高。詳見 `docs/system-spec.md` 第 4 節
