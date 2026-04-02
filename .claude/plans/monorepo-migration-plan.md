# Monorepo 遷移與部署規劃筆記

> 整理自 2026-03-26 與 Claude Code 的討論，作為 repo 重新規劃的參考文件。

---

## 1. 問題背景

目前三個 VM 各自獨立，在 AI 輔助開發時，跨服務的協調（例如 API 欄位對齊）需要手動在不同 session 間搬運提示詞，效率低。

---

## 2. 解決方案：Monorepo

將三個 VM 的程式碼放進同一個 git repo：

```
scholaverse/
├── vm-web-server/     ← 現有 intro-ai 的程式碼
├── vm-ai-worker/      ← 現有 ai-worker 的程式碼
└── vm-db-storage/     ← 未來建立
```

### 優點

- 一個 Claude Code session 開在根目錄，能同時讀寫三邊程式碼
- 跨服務問題（schema 對齊、API 介面同步）可在同一 session 內直接處理
- 不需要人工在不同 session 間搬運上下文

---

## 3. 遷移方式

### 情境 A：不保留舊歷史（最簡單）

1. 建新 repo `chihuah/scholaverse`
2. 把三個專案的檔案直接複製進對應子目錄
3. 初始 commit 一次搞定
4. 舊 repo 設為 archived

### 情境 B：保留 web-server 的 git 歷史（推薦）

現有 repo 有 20+ 筆有意義的 commit，建議保留。

```bash
# 在舊 repo 裡，將所有歷史路徑加上子目錄前綴
git filter-repo --to-subdirectory-filter vm-web-server

# 在新 monorepo 裡，合併舊歷史
git remote add web-server <舊repo路徑>
git fetch web-server
git merge web-server/main --allow-unrelated-histories
```

vm-ai-worker 和 vm-db-storage 目前沒有 git 歷史，直接放進子目錄做初始 commit 即可。

---

## 4. Claude Code 工作流程

### CLAUDE.md 分層設計

```
scholaverse/
├── CLAUDE.md              ← 整體架構、三個 VM 的關係、共用規範
├── vm-web-server/
│   └── CLAUDE.md          ← web-server 專屬技術棧、注意事項
├── vm-ai-worker/
│   └── CLAUDE.md          ← ai-worker 專屬內容
└── vm-db-storage/
    └── CLAUDE.md
```

Claude Code 會從工作目錄往上找所有層級的 CLAUDE.md 並全部載入，子目錄的優先級高於根目錄，不會搞混。

### 日常開發方式

**只需要一個 session**，開在 monorepo 根目錄。

- **平時針對單一服務**：告訴 Claude「現在針對 `vm-ai-worker/` 做調整」，它只動那個子目錄
- **跨服務協調時**：直接說「同步 `vm-web-server/` 和 `vm-ai-worker/` 的 API 介面」，它兩邊一起看

不需要多個 tmux pane 或多個 session，一個就夠。

---

## 5. VM 自動同步與部署

### 流程

```
本機 Claude Code 修改程式碼
↓
git push 到 GitHub
↓
各 VM 自動 git pull（整個 repo）
↓
rsync 將對應子目錄複製到服務實際目錄
↓
自動 restart 服務
```

### 注意事項

- `git pull` 永遠拉整個 repo，無法只拉子目錄，但只傳輸有變動的檔案，實際影響很小
- restart 服務前，先判斷是否有該服務相關的子目錄有變動，避免不必要的重啟

### vm-web-server 自動同步腳本範例

```bash
#!/bin/bash
# /home/chihuah/sync-web-server.sh

REPO_DIR=~/scholaverse
DEPLOY_DIR=/var/www/app.scholaverse.cc/intro-ai

cd "$REPO_DIR"
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    git pull origin main

    # 只有 vm-web-server/ 有變動才部署
    CHANGED=$(git diff HEAD@{1} --name-only | grep "^vm-web-server/")
    if [ -n "$CHANGED" ]; then
        rsync -av --exclude='.env' \
                  --exclude='*.db' \
                  --exclude='outputs/' \
                  "$REPO_DIR/vm-web-server/" \
                  "$DEPLOY_DIR/"
        systemctl restart scholaverse-web
        echo "$(date): deployed and restarted"
    fi
fi
```

加進 crontab，每分鐘檢查一次：

```
* * * * * /home/chihuah/sync-web-server.sh >> /var/log/scholaverse-sync.log 2>&1
```

### rsync 排除清單

部署時必須排除以下檔案，避免覆蓋 VM 上的本地設定：

| 檔案/目錄 | 原因 |
|-----------|------|
| `.env` | 環境變數，各 VM 不同，不放 git |
| `*.db` | SQLite 資料庫，不能被覆蓋 |
| `outputs/` | 生成的圖片等使用者資料 |
| `uploads/` | 使用者上傳的檔案 |

---

## 6. 待辦事項

- [ ] 建立新 GitHub repo `chihuah/scholaverse`
- [ ] 用 `git filter-repo` 遷移 web-server 歷史到 `vm-web-server/` 子目錄
- [ ] 將 vm-ai-worker 現有程式碼放進 `vm-ai-worker/` 並初始 commit
- [ ] 設計根目錄 `CLAUDE.md`（整體架構描述）
- [ ] 在各 VM 上設定自動同步腳本與 crontab
- [ ] 舊 repo `chihuah/scholaverse_web-server_intro-ai` 設為 archived
