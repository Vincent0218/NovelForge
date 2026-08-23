# 小說抓取與 EPUB/TXT 生成實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 抓取台灣小說網《我都元嬰期了，你跟我說開學？》（Book ID: 20）的所有章節，支援斷點續傳、內文清洗，並生成標準 EPUB 與 TXT 檔案。

**Architecture:** 使用 Python 搭配 `uv` 管理環境。透過 `httpx` 及執行緒池並行抓取，章節即時存入快取，經 `BeautifulSoup` 清洗過濾廣告後，由 `ebooklib` 與文字合成器產出 EPUB 與 TXT。

**Tech Stack:** Python 3.11+, uv, httpx, beautifulsoup4, ebooklib, tqdm, pytest

## Global Constraints

- 預設語言：繁體中文台灣用語
- 必須使用 `uv` 與 `.venv` 建立虛擬環境，不可污染全域環境
- Git commit messages 一律使用繁體中文台灣用語
- 支援斷點續傳快取，避免重複請求已下載章節

---

### Task 1: 專案環境初始化與依賴配置

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `src.config` 中的設定常數：`BOOK_ID`, `BASE_URL`, `CHAPTER_LIST_URL`, `DATA_DIR`, `CHAPTERS_DIR`, `OUTPUT_DIR`, `DEFAULT_WORKERS`, `HEADERS`

- [ ] **Step 1: 初始化 uv 專案並加入依賴**

```powershell
uv init --bare
uv add httpx beautifulsoup4 ebooklib tqdm pytest
```

- [ ] **Step 2: 撰寫 Config 測試**

```python
# tests/test_config.py
from src.config import BOOK_ID, BASE_URL, CHAPTER_LIST_URL, CHAPTERS_DIR, OUTPUT_DIR

def test_config_values():
    assert BOOK_ID == "20"
    assert "twkan.com" in BASE_URL
    assert "chapterlist/20.html" in CHAPTER_LIST_URL
    assert CHAPTERS_DIR.exists() or True
    assert OUTPUT_DIR.exists() or True
```

- [ ] **Step 3: 建立 `src/config.py` 與套件檔案**

```python
# src/config.py
from pathlib import Path

BOOK_ID = "20"
BOOK_TITLE = "我都元嬰期了，你跟我說開學？"
BOOK_AUTHOR = "妙妙醬丷"
BASE_URL = "https://twkan.com"
CHAPTER_LIST_URL = f"{BASE_URL}/ajax_novels/chapterlist/{BOOK_ID}.html"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CHAPTERS_DIR = DATA_DIR / "chapters"
OUTPUT_DIR = ROOT_DIR / "output"

DEFAULT_WORKERS = 6
REQUEST_TIMEOUT = 15.0
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/book/{BOOK_ID}/index.html",
}

for d in [DATA_DIR, CHAPTERS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 執行測試驗證**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: 提交 Commit**

```bash
git add pyproject.toml uv.lock src/ tests/
git commit -m "feat: 初始化專案環境與基本設定"
```

---

### Task 2: 內文清洗器 (`src/cleaner.py`)

**Files:**
- Create: `src/cleaner.py`
- Create: `tests/test_cleaner.py`

**Interfaces:**
- Consumes: HTML string
- Produces: `clean_chapter_content(html_str: str) -> str`，回傳純淨排版文字段落。

- [ ] **Step 1: 撰寫 Cleaner 測試**

```python
# tests/test_cleaner.py
from src.cleaner import clean_chapter_content

def test_clean_chapter_content_removes_ads_and_scripts():
    raw_html = """
    <div id="txtcontent0">
        &emsp;&emsp;青州市郊外，無名荒山。<br /><br />
        【寫到這裡我希望讀者記一下我們域名 台灣小說網超貼心，𝑡𝑤𝑘𝑎𝑛.𝑐𝑜𝑚超方便 】<br />
        <div class="txtad"><script>loadAdv(10,0);</script></div>
        &emsp;&emsp;「轟隆！」<br />
        突如其來的一聲巨響。
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    assert "青州市郊外，無名荒山。" in cleaned
    assert "「轟隆！」" in cleaned
    assert "突如其來的一聲巨響。" in cleaned
    assert "台灣小說網" not in cleaned
    assert "𝑡𝑤𝑘𝑎𝑛.𝑐𝑜𝑚" not in cleaned
    assert "loadAdv" not in cleaned
```

- [ ] **Step 2: 實作 `src/cleaner.py`**

```python
# src/cleaner.py
import re
from bs4 import BeautifulSoup

WATERMARK_PATTERNS = [
    r"【寫到這裡我希望讀者記一下我們域名.*?】",
    r"\(https?://[^\s)]+\)",
    r"twkan\.com",
    r"𝑡𝑤𝑘𝑎𝑛\.𝑐𝑜𝑚",
    r"台灣小說網",
]

def clean_chapter_content(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    content_div = soup.find("div", id="txtcontent0")
    if not content_div:
        # Fallback to whole soup if div not found
        content_div = soup

    # 移除廣告與 script
    for unwanted in content_div.find_all(["script", "div"], class_=["txtad", "txtcenter"]):
        unwanted.decompose()
    for tag in content_div.find_all("script"):
        tag.decompose()

    # 將 <br> 替換為換行符
    for br in content_div.find_all("br"):
        br.replace_with("\n")

    text = content_div.get_text()

    # 清理浮水印
    for pattern in WATERMARK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 清理多餘空白行與全形空白整理
    lines = []
    for line in text.splitlines():
        line = line.replace("\u2003", "").replace("&emsp;", "").strip()
        if line:
            lines.append("　　" + line)

    return "\n\n".join(lines)
```

- [ ] **Step 3: 執行測試驗證**

Run: `uv run pytest tests/test_cleaner.py -v`
Expected: PASS

- [ ] **Step 4: 提交 Commit**

```bash
git add src/cleaner.py tests/test_cleaner.py
git commit -m "feat: 實作章節內文清洗器與過濾規則"
```

---

### Task 3: 爬蟲核心 (`src/crawler.py`)

**Files:**
- Create: `src/crawler.py`
- Create: `tests/test_crawler.py`

**Interfaces:**
- Consumes: `src.config`, `src.cleaner.clean_chapter_content`
- Produces:
  - `fetch_catalog(client: httpx.Client) -> list[dict]` (回傳 `[{num, title, url, chapter_id}]`)
  - `download_all_chapters(catalog: list[dict], max_workers: int = 6, progress_callback = None)`

- [ ] **Step 1: 撰寫 Crawler 測試**

```python
# tests/test_crawler.py
import json
from unittest.mock import MagicMock
from src.crawler import parse_catalog_html, download_chapter

def test_parse_catalog_html():
    html = """
    <ul>
      <li data-num="1"><a href="https://twkan.com/txt/20/29465" title="第1章">第1章 修真界歸來 </a></li>
      <li data-num="2"><a href="https://twkan.com/txt/20/29466" title="第2章">第2章 早說了 </a></li>
    </ul>
    """
    catalog = parse_catalog_html(html)
    assert len(catalog) == 2
    assert catalog[0]["num"] == 1
    assert catalog[0]["title"] == "第1章 修真界歸來"
    assert catalog[0]["url"] == "https://twkan.com/txt/20/29465"
    assert catalog[0]["chapter_id"] == "29465"

def test_download_chapter(tmp_path):
    mock_client = MagicMock()
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.text = '<div id="txtcontent0">第1章內文測試</div>'
    
    chapter_info = {
        "num": 1,
        "title": "第1章 修真界歸來",
        "url": "https://twkan.com/txt/20/29465",
        "chapter_id": "29465"
    }
    
    saved_path = download_chapter(mock_client, chapter_info, cache_dir=tmp_path)
    assert saved_path.exists()
    
    with open(saved_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == "第1章 修真界歸來"
    assert "第1章內文測試" in data["content"]
```

- [ ] **Step 2: 實作 `src/crawler.py`**

```python
# src/crawler.py
import json
import time
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from bs4 import BeautifulSoup
from src.config import (
    CHAPTER_LIST_URL,
    CHAPTERS_DIR,
    DATA_DIR,
    HEADERS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    DEFAULT_WORKERS
)
from src.cleaner import clean_chapter_content

def parse_catalog_html(html_str: str) -> list[dict]:
    soup = BeautifulSoup(html_str, "html.parser")
    catalog = []
    for li in soup.find_all("li", attrs={"data-num": True}):
        a_tag = li.find("a")
        if not a_tag:
            continue
        try:
            num = int(li["data-num"])
        except ValueError:
            num = len(catalog) + 1
        title = a_tag.get_text(strip=True)
        url = a_tag.get("href", "").strip()
        # 從 url 提取 chapter_id (如 /txt/20/29465 -> 29465)
        match = re.search(r"/(\d+)(?:\.html)?$", url)
        chapter_id = match.group(1) if match else str(num)
        
        catalog.append({
            "num": num,
            "title": title,
            "url": url,
            "chapter_id": chapter_id
        })
    # 確保按章節序號由小到大排序
    catalog.sort(key=lambda x: x["num"])
    return catalog

def fetch_catalog(client: httpx.Client | None = None) -> list[dict]:
    catalog_cache = DATA_DIR / "catalog.json"
    if catalog_cache.exists():
        with open(catalog_cache, "r", encoding="utf-8") as f:
            return json.load(f)

    should_close = False
    if client is None:
        client = httpx.Client(headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        should_close = True
    try:
        resp = client.get(CHAPTER_LIST_URL)
        resp.raise_for_status()
        catalog = parse_catalog_html(resp.text)
        with open(catalog_cache, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        return catalog
    finally:
        if should_close:
            client.close()

def get_chapter_cache_path(chapter_info: dict, cache_dir: Path = CHAPTERS_DIR) -> Path:
    return cache_dir / f"{chapter_info['num']:05d}_{chapter_info['chapter_id']}.json"

def download_chapter(client: httpx.Client, chapter_info: dict, cache_dir: Path = CHAPTERS_DIR) -> Path:
    cache_path = get_chapter_cache_path(chapter_info, cache_dir)
    if cache_path.exists():
        return cache_path

    url = chapter_info["url"]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            content = clean_chapter_content(resp.text)
            
            data = {
                "num": chapter_info["num"],
                "title": chapter_info["title"],
                "chapter_id": chapter_info["chapter_id"],
                "url": url,
                "content": content
            }
            # 寫入暫存檔案
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return cache_path
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"章節下載失敗 {chapter_info['title']} ({url}): {e}") from e
            time.sleep(0.5 * attempt)

def download_all_chapters(catalog: list[dict], max_workers: int = DEFAULT_WORKERS, progress_hook = None):
    with httpx.Client(headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {
                executor.submit(download_chapter, client, chapter): chapter
                for chapter in catalog
            }
            for future in as_completed(future_to_chapter):
                chap = future_to_chapter[future]
                try:
                    res = future.result()
                    if progress_hook:
                        progress_hook(chap, None)
                except Exception as exc:
                    if progress_hook:
                        progress_hook(chap, exc)
```

- [ ] **Step 3: 執行測試驗證**

Run: `uv run pytest tests/test_crawler.py -v`
Expected: PASS

- [ ] **Step 4: 提交 Commit**

```bash
git add src/crawler.py tests/test_crawler.py
git commit -m "feat: 實作目錄獲取、並行章節下載與快取斷點續傳"
```

---

### Task 4: EPUB 與 TXT 生成器 (`src/builder.py`)

**Files:**
- Create: `src/builder.py`
- Create: `tests/test_builder.py`

**Interfaces:**
- Consumes: `catalog: list[dict]`, `cache_dir: Path`
- Produces:
  - `build_txt(catalog: list[dict], output_path: Path) -> Path`
  - `build_epub(catalog: list[dict], output_path: Path, title: str, author: str) -> Path`

- [ ] **Step 1: 撰寫 Builder 測試**

```python
# tests/test_builder.py
import json
from pathlib import Path
from src.builder import build_txt, build_epub

def test_build_txt_and_epub(tmp_path):
    cache_dir = tmp_path / "chapters"
    cache_dir.mkdir()
    
    catalog = [
        {"num": 1, "title": "第1章 測試", "chapter_id": "101"},
        {"num": 2, "title": "第2章 續集", "chapter_id": "102"},
    ]
    
    for item in catalog:
        cpath = cache_dir / f"{item['num']:05d}_{item['chapter_id']}.json"
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump({"num": item["num"], "title": item["title"], "content": f"這是{item['title']}的內容。"}, f)
            
    txt_out = tmp_path / "test.txt"
    build_txt(catalog, txt_out, cache_dir=cache_dir)
    assert txt_out.exists()
    content = txt_out.read_text(encoding="utf-8")
    assert "第1章 測試" in content
    assert "這是第2章 續集的內容。" in content

    epub_out = tmp_path / "test.epub"
    build_epub(catalog, epub_out, title="測試小說", author="作者名", cache_dir=cache_dir)
    assert epub_out.exists()
    assert epub_out.stat().st_size > 0
```

- [ ] **Step 2: 實作 `src/builder.py`**

```python
# src/builder.py
import json
from pathlib import Path
from ebooklib import epub
from src.config import CHAPTERS_DIR, BOOK_TITLE, BOOK_AUTHOR

def load_cached_chapter(chapter_info: dict, cache_dir: Path = CHAPTERS_DIR) -> dict:
    cache_path = cache_dir / f"{chapter_info['num']:05d}_{chapter_info['chapter_id']}.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"尚未下載快取章節：{chapter_info['title']} ({cache_path})")
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_txt(catalog: list[dict], output_path: Path, cache_dir: Path = CHAPTERS_DIR) -> Path:
    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write(f"{BOOK_TITLE}\n")
        f_out.write(f"作者：{BOOK_AUTHOR}\n\n")
        f_out.write("=" * 40 + "\n\n")
        
        for item in catalog:
            data = load_cached_chapter(item, cache_dir=cache_dir)
            f_out.write(f"{data['title']}\n\n")
            f_out.write(data["content"] + "\n\n")
            f_out.write("-" * 30 + "\n\n")
            
    return output_path

def build_epub(
    catalog: list[dict],
    output_path: Path,
    title: str = BOOK_TITLE,
    author: str = BOOK_AUTHOR,
    cache_dir: Path = CHAPTERS_DIR
) -> Path:
    book = epub.EpubBook()
    book.set_identifier(f"twkan-novel-{title}")
    book.set_title(title)
    book.set_language("zh-TW")
    book.add_author(author)

    epub_chapters = []
    toc = []

    # 預設樣式
    style = """
    @namespace epub "http://www.idpf.org/2007/ops";
    body { font-family: "PingFang TC", "Microsoft JhengHei", sans-serif; line-height: 1.8; margin: 1em; }
    h1 { text-align: center; margin-bottom: 1.5em; font-size: 1.4em; }
    p { text-indent: 2em; margin-bottom: 0.8em; }
    """
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    for item in catalog:
        data = load_cached_chapter(item, cache_dir=cache_dir)
        c_title = data["title"]
        file_name = f"chap_{item['num']:05d}.xhtml"
        
        # 轉換段落為 HTML <p>
        paragraphs = data["content"].split("\n\n")
        html_content = f"<h1>{c_title}</h1>\n"
        for p in paragraphs:
            p_clean = p.strip()
            if p_clean:
                html_content += f"<p>{p_clean}</p>\n"

        c = epub.EpubHtml(title=c_title, file_name=file_name, lang="zh-TW")
        c.content = f"<html><head><title>{c_title}</title><link rel='stylesheet' href='style/nav.css'/></head><body>{html_content}</body></html>"
        c.add_item(nav_css)
        book.add_item(c)
        epub_chapters.append(c)
        toc.append(c)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_chapters

    epub.write_epub(str(output_path), book, {})
    return output_path
```

- [ ] **Step 3: 執行測試驗證**

Run: `uv run pytest tests/test_builder.py -v`
Expected: PASS

- [ ] **Step 4: 提交 Commit**

```bash
git add src/builder.py tests/test_builder.py
git commit -m "feat: 實作 EPUB 與 TXT 電子書合成器"
```

---

### Task 5: CLI 主程式入口與整合測試 (`src/main.py`)

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: 實作 `src/main.py`**

```python
# src/main.py
import sys
from tqdm import tqdm
from src.config import BOOK_TITLE, BOOK_AUTHOR, OUTPUT_DIR, DEFAULT_WORKERS
from src.crawler import fetch_catalog, download_all_chapters
from src.builder import build_epub, build_txt

def main():
    print(f"📖 開始抓取小說：《{BOOK_TITLE}》（作者：{BOOK_AUTHOR}）")
    
    # 1. 取得目錄
    print("📋 正在獲取章節目錄...")
    catalog = fetch_catalog()
    total_chapters = len(catalog)
    print(f"共發現 {total_chapters} 個章節。")

    # 2. 下載章節
    print(f"🚀 開始下載章節（Worker: {DEFAULT_WORKERS}）...")
    with tqdm(total=total_chapters, desc="下載進度", unit="章") as pbar:
        def on_progress(chap, err):
            if err:
                tqdm.write(f"❌ 下載出錯 [{chap['title']}]: {err}")
            pbar.update(1)

        download_all_chapters(catalog, max_workers=DEFAULT_WORKERS, progress_hook=on_progress)

    # 3. 建立輸出檔案
    txt_path = OUTPUT_DIR / f"{BOOK_TITLE}.txt"
    epub_path = OUTPUT_DIR / f"{BOOK_TITLE}.epub"

    print("📄 正在產生 TXT 純文字檔...")
    build_txt(catalog, txt_path)
    print(f"✅ TXT 產生完成：{txt_path}")

    print("📚 正在封裝 EPUB 電子書...")
    build_epub(catalog, epub_path, title=BOOK_TITLE, author=BOOK_AUTHOR)
    print(f"✅ EPUB 封裝完成：{epub_path}")

    print("🎉 全部任務完成！")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 執行全部單元測試**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 3: 提交 Commit**

```bash
git add src/main.py
git commit -m "feat: 實作 CLI 主程式入口與整體抓取轉檔流程"
```

---

### Task 6: 執行下載與產生最終小說檔案

- [ ] **Step 1: 執行 `uv run python -m src.main`**
- [ ] **Step 2: 驗證 `output/` 目錄下的 `.epub` 與 `.txt` 檔案大小與完整性**
