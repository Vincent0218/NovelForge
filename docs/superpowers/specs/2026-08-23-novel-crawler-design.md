# 小說抓取與電子書 (EPUB/TXT) 生成工具設計規格書

- **專案名稱**：Novel Crawler & EPUB/TXT Builder
- **目標小說**：《我都元嬰期了，你跟我說開學？》（來源：台灣小說網 twkan.com / Book ID: 20）
- **日期**：2026-08-23

---

## 1. 系統目標與需求

1. **章節抓取**：完整抓取全書共 2,500+ 章節內容。
2. **斷點續傳與快取**：即時快取下載章節，支援中斷後接續下載，避免重複發送請求。
3. **文字過濾與清洗**：移除網站浮水印、廣告代碼 (`<script>`/`loadAdv`)、引流推廣語（例如：`【寫到這裡我希望讀者記一下...】` 等）。
4. **輸出成果**：
   - 標準 **EPUB** 格式電子書（支援目錄跳轉、Metadata 設定）。
   - 完整整合的 **TXT** 純文字檔。
5. **環境規範**：遵循專案規則，嚴格使用 `uv` 及 `.venv` 虛擬環境，不污染全域環境。

---

## 2. 系統架構與模組設計

```
Novel-agy/
├── .venv/                   # 由 uv 建立的獨立虛擬環境
├── pyproject.toml           # 依賴管理與設定檔
├── data/
│   ├── catalog.json         # 章節目錄快取
│   └── chapters/            # 分章快取 (.json)
├── output/
│   ├── 我都元嬰期了，你跟我說開學？.epub
│   └── 我都元嬰期了，你跟我說開學？.txt
└── src/
    ├── __init__.py
    ├── config.py            # 常數與爬蟲設定
    ├── crawler.py           # 目錄與章節下載邏輯（支援多執行緒/重試/斷點續傳）
    ├── cleaner.py           # HTML 解析與內文清洗過濾
    ├── builder.py           # EPUB 與 TXT 檔案合成器
    └── main.py              # CLI 入口腳本
```

---

## 3. 模組詳細規格

### 3.1 `config.py`
- 設定小說 ID (`20`)、Base URL (`https://twkan.com`)。
- 並行下載數量（預設 6 個 Workers）、請求間隔（0.1~0.3 秒）、最大重試次數（3 次）。
- Request Headers（模擬瀏覽器 User-Agent 與 Referer）。

### 3.2 `cleaner.py`
- 輸入原始 HTML 內容。
- 使用 `BeautifulSoup` 提取 `#txtcontent0`。
- 移除 `.txtad`、`.txtcenter`、`<script>` 標籤。
- 正則表達式濾除網站浮水印（例如：`【寫到這裡我希望讀者記一下我們域名.*】` 等）。
- 格式化段落，將 `&emsp;` 或連續空白轉換為標準縮排換行。

### 3.3 `crawler.py`
- **目錄取得**：請求 `https://twkan.com/ajax_novels/chapterlist/20.html` 解析所有 `<li data-num="...">` 得到章節編號、名稱、連結。
- **章節下載**：
  - 檢查 `data/chapters/<idx>_<chapter_id>.json` 是否已存在。
  - 不存在則使用 `httpx` 發送 GET 請求，經由 `cleaner.py` 處理後存檔。
  - 使用 `concurrent.futures.ThreadPoolExecutor` 進行並行抓取，並使用 `tqdm` 呈現進度條。

### 3.4 `builder.py`
- **EPUB 生成**：
  - 使用 `ebooklib` 建立 `EpubBook`。
  - 設定書籍 metadata（書名、作者、語言 `zh-TW`）。
  - 將各章節新增為 `EpubHtml`，建立章節目錄（Table of Contents / Spine）。
  - 輸出至 `output/`。
- **TXT 生成**：
  - 依序遍歷快取章節，加入章節標題並寫入單一 `.txt` 檔案。

### 3.5 `main.py`
- 串接上述流程：取得目錄 -> 執行下載 -> 建立 EPUB 與 TXT -> 驗證成果。

---

## 4. 錯誤處理與強健性 (Robustness)

- **網路超時與連線異常**：每個章節下載有 3 次重試機會（指數退避）。
- **斷點續傳**：即使中途中斷，重新執行程式會自動跳過已下載完成的章節。
- **遺漏檢查**：在建立電子書前，校驗所有章節是否皆下載完整，如有缺失則回補抓取。
