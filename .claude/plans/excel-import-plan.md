# Excel 匯入功能實作計畫

## 背景與目標

從 TronClass 匯出兩種 Excel 報表，透過 Admin 後台上傳介面，將學生學習資料寫入 `learning_records` 資料表。

---

## 兩種報表的格式摘要

### 報表 A：完成度報表（`完成度_人工智慧概論.xlsx`）

- **學生識別**：col 2（帳號/學號）→ `students.student_id`
- **標題行**：第 1 行（單層標題）
- **資料起始行**：第 2 行
- **章節完成度欄**（標題固定，以名稱偵測）：

  | 欄標題 | 對應 unit_code | 寫入欄位 |
  |---|---|---|
  | `1-人工智慧與深度學習的基礎` | `unit_1` | `completion_rate` |
  | `2-多層感知器 - 回歸與分類問題` | `unit_2` | `completion_rate` |
  | `3-卷積神經網路 - 電腦視覺` | `unit_3` | `completion_rate` |
  | `4-循環神經網路 - 自然語言處理` | `unit_4` | `completion_rate` |
  | `5-建構深度學習網路模型` | `unit_5` | `completion_rate` |
  | `6-自主學習` | `unit_6` | `completion_rate` |

- **課後測驗欄**（標題含「第X章 課後測驗」，動態偵測）：

  | 欄標題 | 對應 unit_code | 寫入欄位 |
  |---|---|---|
  | `第一章 課後測驗` | `unit_1` | `quiz_score` |
  | `第二章 課後測驗`（未來新增） | `unit_2` | `quiz_score` |
  | 以此類推... | | |

- **值解析規則**：

  | 原始值 | 解析結果 |
  |---|---|
  | `87.5%` | `87.5` |
  | `100.0分` | `100.0` |
  | `95.0分` | `95.0` |
  | `未完成` | `0.0` |
  | `—` 或 `None` | `NULL`（不寫入） |

- **不動欄位**：`preview_score`（此報表不含，保留原值）

---

### 報表 B：成績單報表（`score_list.xlsx`）

- **學生識別**：col 1（帳號）→ `students.student_id`
- **標題行**：第 2 行（雙層標題，第 1 行為分組標題）
- **資料起始行**：第 3 行
- **分數欄**（標題含「第X章 前測」或「第X章 課後測驗」，動態偵測）：

  | 欄標題格式 | 對應 unit_code | 寫入欄位 |
  |---|---|---|
  | `第一章 前測(X%)` | `unit_1` | `preview_score` |
  | `第二章 前測(X%)` | `unit_2` | `preview_score` |
  | 以此類推... | | |
  | `第一章 課後測驗(X%)` | `unit_1` | `quiz_score` |
  | `第二章 課後測驗(X%)` | `unit_2` | `quiz_score` |
  | 以此類推... | | |

- **章節序數對應表**（用於標題解析）：

  ```python
  CHAPTER_NUMBER_MAP = {
      "第一章": "unit_1",
      "第二章": "unit_2",
      "第三章": "unit_3",
      "第四章": "unit_4",
      "第五章": "unit_5",
      "第六章": "unit_6",
  }
  ```

- **值解析規則**：

  | 原始值 | 解析結果 |
  |---|---|
  | `100`、`85`、`76` 等數字 | 直接使用（float） |
  | `未繳` | `NULL`（不寫入） |
  | `None` | `NULL`（不寫入） |

- **不動欄位**：`completion_rate`（此報表不含，保留原值）

---

## 實作架構

### 新增／修改檔案

```
app/
├── services/
│   └── excel_import.py        # 核心解析邏輯（新增）
├── routers/
│   └── admin.py               # 新增 4 個 endpoint（已存在，擴充）
├── templates/
│   └── admin/
│       └── import.html        # 擴充現有頁面，加入 Excel 上傳區塊
```

---

## 詳細實作步驟

### Step 1：建立 `app/services/excel_import.py`

此模組負責解析 Excel，回傳結構化的 preview 資料，**不直接寫入 DB**。

#### 資料結構

```python
from dataclasses import dataclass, field

@dataclass
class StudentRecord:
    student_id: str            # 原始帳號（學號）
    unit_code: str             # "unit_1" ~ "unit_6"
    completion_rate: float | None = None
    quiz_score: float | None = None
    preview_score: float | None = None

@dataclass
class ExcelParseResult:
    records: list[StudentRecord] = field(default_factory=list)
    unrecognized_headers: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
```

#### 章節標題對應常數

```python
COMPLETION_HEADER_MAP = {
    "1-人工智慧與深度學習的基礎": "unit_1",
    "2-多層感知器 - 回歸與分類問題": "unit_2",
    "3-卷積神經網路 - 電腦視覺": "unit_3",
    "4-循環神經網路 - 自然語言處理": "unit_4",
    "5-建構深度學習網路模型": "unit_5",
    "6-自主學習": "unit_6",
}

CHAPTER_NUMBER_MAP = {
    "第一章": "unit_1",
    "第二章": "unit_2",
    "第三章": "unit_3",
    "第四章": "unit_4",
    "第五章": "unit_5",
    "第六章": "unit_6",
}
```

#### 值解析輔助函式

```python
def _parse_completion_rate(val) -> float | None:
    """'87.5%' → 87.5，'—'/None → None"""
    if val is None or str(val).strip() == "—":
        return None
    s = str(val).strip()
    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None
    return None

def _parse_quiz_completion(val) -> float | None:
    """'100.0分' → 100.0，'未完成' → 0.0，'—'/None → None"""
    if val is None or str(val).strip() == "—":
        return None
    s = str(val).strip()
    if s.endswith("分"):
        try:
            return float(s[:-1])
        except ValueError:
            return None
    if s == "未完成":
        return 0.0
    return None

def _parse_score(val) -> float | None:
    """85 → 85.0，'未繳'/None → None"""
    if val is None or str(val).strip() in ("未繳", "—", "未批改"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
```

#### `parse_completion_excel(file_bytes: bytes) -> ExcelParseResult`

```
1. 用 openpyxl 讀取（load_workbook）
2. 取第一個 sheet
3. 讀取第 1 行為 headers
4. 確認 col 2（index 1）存在且為帳號欄
5. 掃描所有欄標題：
   - 在 COMPLETION_HEADER_MAP 中 → 記錄 (col_idx, unit_code, "completion_rate")
   - 含「課後測驗」且能從 CHAPTER_NUMBER_MAP 找到章節 → 記錄 (col_idx, unit_code, "quiz_score")
   - 其他 → 加入 unrecognized_headers
6. 從第 2 行起逐行處理：
   - student_id = row[1]（col 2）
   - 對每個記錄的欄位，呼叫對應解析函式
   - 建立 StudentRecord 並加入 result.records
7. 回傳 ExcelParseResult
```

#### `parse_score_excel(file_bytes: bytes) -> ExcelParseResult`

```
1. 用 openpyxl 讀取
2. 取第一個 sheet
3. 讀取第 2 行（index 1）為 headers（跳過第 1 行分組標題）
4. 確認 col 1（index 0）存在且為帳號欄
5. 掃描所有欄標題：
   - 含「前測」且能從 CHAPTER_NUMBER_MAP 找到章節 → 記錄 (col_idx, unit_code, "preview_score")
   - 含「課後測驗」且能從 CHAPTER_NUMBER_MAP 找到章節 → 記錄 (col_idx, unit_code, "quiz_score")
6. 從第 3 行起逐行處理（跳過兩行標題）：
   - 略過空行（所有欄均為 None）
   - 略過結尾列（如「教師簽章」行）
   - student_id = row[0]（col 1）
   - 對每個記錄的欄位，呼叫 _parse_score()
   - 建立 StudentRecord 並加入 result.records
7. 回傳 ExcelParseResult
```

---

### Step 2：擴充 `app/routers/admin.py`

新增 4 個 endpoint：

#### `POST /api/admin/import-excel/completion/preview`

```python
@router.post("/api/admin/import-excel/completion/preview")
async def api_excel_completion_preview(
    request: Request,
    file: UploadFile = File(...),
    user: Student = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    # 1. 驗證檔案格式（.xlsx, < 5MB）
    # 2. 呼叫 parse_completion_excel()
    # 3. 查詢所有 students 建立 student_id → pk 的 map
    # 4. 計算統計：matched, not_found, will_update, will_create
    # 5. 回傳 HTMX HTML 片段（preview 摘要）
```

#### `POST /api/admin/import-excel/completion/commit`

```python
@router.post("/api/admin/import-excel/completion/commit")
async def api_excel_completion_commit(
    file: UploadFile = File(...),
    user: Student = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    # 1. 重新解析（不信任 session，重新讀檔）
    # 2. 執行 upsert（只更新 completion_rate、quiz_score，不動 preview_score）
    # 3. 回傳結果 HTML 片段
```

#### `POST /api/admin/import-excel/scores/preview`
（同上，對應 score_list 報表）

#### `POST /api/admin/import-excel/scores/commit`
（只更新 preview_score、quiz_score，不動 completion_rate）

#### 共用 Upsert 函式（module-level helper）

```python
async def _upsert_records(
    db: AsyncSession,
    records: list[StudentRecord],
    student_map: dict[str, int],  # student_id → students.id
    unit_map: dict[str, int],     # unit_code → units.id
) -> tuple[int, int, list[str]]:  # (created, updated, warnings)
```

---

### Step 3：擴充 `app/templates/admin/import.html`

頁面結構調整：
- Excel 匯入區塊（新增）← **放在最上方**
- 現有 CSV 匯入區塊（保留，未來改為上傳「預習影片觀看比率」）

Excel 匯入區塊分兩欄並排：

```
┌─────────────────────────────────────────────────────────┐
│  Excel 匯入                                             │
├──────────────────────┬──────────────────────────────────┤
│  完成度報表           │  成績單報表                      │
│  (完成度_xxx.xlsx)   │  (score_list.xlsx)               │
│                      │                                  │
│  [選擇檔案]          │  [選擇檔案]                      │
│  [上傳預覽]          │  [上傳預覽]                      │
│                      │                                  │
│  ── 預覽摘要 ──      │  ── 預覽摘要 ──                 │
│  比對到: N 位學生    │  比對到: N 位學生               │
│  將更新: N 筆        │  將更新: N 筆                   │
│  將新增: N 筆        │  將新增: N 筆                   │
│  找不到: [學號清單]  │  找不到: [學號清單]             │
│                      │                                  │
│  [確認匯入]          │  [確認匯入]                     │
└──────────────────────┴──────────────────────────────────┘
```

- 使用 HTMX：`hx-post` 上傳 → 回傳 HTML 片段顯示摘要
- 確認按鈕在預覽後才出現（初始隱藏）
- 匯入完成後替換摘要區域顯示結果

### Step 3b：更新 `app/templates/admin/dashboard.html`

- 「匯入成績 CSV」按鈕文字改為「匯入成績」

---

## 錯誤處理邊界情況

| 情況 | 處理方式 |
|---|---|
| 找不到學生學號 | 記錄 warning，跳過該行，匯入繼續 |
| 欄位標題異動 | `unrecognized_headers` 列出，不影響已認識欄位 |
| 值格式無法解析 | 視為 NULL，不寫入，記錄 warning |
| 非 .xlsx 格式 | 回傳 400 錯誤 |
| 檔案超過 5MB | 回傳 400 錯誤 |
| DB 寫入失敗 | rollback，回傳 500 錯誤 |
| 空行或結尾備註行 | 全欄為 None 時略過 |

---

## 不在本次範圍內

- 匯入歷史紀錄（log 誰在何時匯入）
- 自動排程匯入
- 匯入後自動觸發角色配置更新（需另外操作）

---

## 實作順序

1. **`app/services/excel_import.py`** — 解析邏輯，純函式，可獨立用 pytest 測試
2. **`admin.py` 新增 4 endpoint** — 依賴 Step 1
3. **`admin/import.html` 擴充 UI** — 依賴 Step 2
4. **端對端測試** — 用真實 Excel（含帳號欄）驗證完整流程，可使用`private/`資料夾裡的`completed_rate.xlsx`跟`score_list.xlsx`兩個excel檔案（前者為完成度之記錄、後者為前後測記錄）來測試驗證。
