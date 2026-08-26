"""小說爬蟲核心模組。

負責目錄解析、章節並行下載、指數退避重試與本機 JSON 快取斷點續傳。
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from src.cleaner import clean_chapter_content
from src.config import (
    CHAPTER_LIST_URL,
    CHAPTERS_DIR,
    DATA_DIR,
    DEFAULT_WORKERS,
    HEADERS,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
)


def parse_catalog_html(html_str: str) -> list[dict[str, Any]]:
    """解析小說目錄 HTML 字串並提取章節列表。

    Args:
        html_str: 目錄 HTML 原始字串。

    Returns:
        包含章節序號、標題、URL 與章節 ID 的字典列表，已按序號排序。
    """
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
        # 從 url 提取 chapter_id (如 /txt/20/29465 或 /txt/20/29465.html -> 29465)
        match = re.search(r"/(\d+)(?:\.html)?$", url)
        chapter_id = match.group(1) if match else str(num)

        catalog.append({
            "num": num,
            "title": title,
            "url": url,
            "chapter_id": chapter_id,
        })
    # 確保按章節序號由小到大排序
    catalog.sort(key=lambda x: x["num"])
    return catalog


def fetch_catalog(client: Any = None, force_refresh: bool = False) -> list[dict[str, Any]]:
    """獲取小說目錄清單。支援強制向網站請求最新目錄或讀取本機快取。

    Args:
        client: 可選的 HTTP 客戶端實例。
        force_refresh: 是否強制重新向網站抓取最新目錄（預設為 False，提供追更時傳入 True）。

    Returns:
        目錄列表。
    """
    catalog_cache = DATA_DIR / "catalog.json"

    # 若不強制刷新且快取存在，直接讀取本機快取
    if not force_refresh and catalog_cache.exists():
        with open(catalog_cache, "r", encoding="utf-8") as f:
            return json.load(f)

    should_close = False
    if client is None:
        client = curl_requests.Session(impersonate="chrome120")
        should_close = True
    try:
        resp = client.get(CHAPTER_LIST_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        catalog = parse_catalog_html(resp.text)
        with open(catalog_cache, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        return catalog
    except Exception as e:
        # 若線上取得失敗但有本機快取，則 fallback 至快取
        if catalog_cache.exists():
            with open(catalog_cache, "r", encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(f"無法取得小說目錄清單且無本機快取：{e}") from e
    finally:
        if should_close and hasattr(client, "close"):
            client.close()



def get_chapter_cache_path(chapter_info: dict[str, Any], cache_dir: Path = CHAPTERS_DIR) -> Path:
    """取得章節快取檔案路徑。

    Args:
        chapter_info: 章節資訊字典。
        cache_dir: 快取資料夾路徑。

    Returns:
        章節快取檔案路徑。
    """
    return cache_dir / f"{chapter_info['num']:05d}_{chapter_info['chapter_id']}.json"


def download_chapter(
    client: Any,
    chapter_info: dict[str, Any],
    cache_dir: Path = CHAPTERS_DIR,
) -> Path:
    """下載單一章節並儲存至本機快取，支援指數退避重試與斷點續傳。

    Args:
        client: HTTP 客戶端。
        chapter_info: 章節資訊字典。
        cache_dir: 快取存放資料夾。

    Returns:
        已下載之 JSON 快取檔案路徑。

    Raises:
        RuntimeError: 重試達上限仍無法下載時拋出。
    """
    cache_path = get_chapter_cache_path(chapter_info, cache_dir)
    if cache_path.exists():
        return cache_path

    url = chapter_info["url"]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            content = clean_chapter_content(resp.text)

            data = {
                "num": chapter_info["num"],
                "title": chapter_info["title"],
                "chapter_id": chapter_info["chapter_id"],
                "url": url,
                "content": content,
            }
            # 寫入暫存快取檔案
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return cache_path
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"章節下載失敗 {chapter_info['title']} ({url}): {e}") from e
            err_msg = str(e)
            is_rate_limit = "429" in err_msg or "Too Many Requests" in err_msg
            backoff = min(1.0 * (2 ** (attempt - 1)), 15.0)
            if is_rate_limit:
                backoff += 2.0
            time.sleep(backoff)

    raise RuntimeError(f"章節下載失敗 {chapter_info['title']} ({url})")


def download_all_chapters(
    catalog: list[dict[str, Any]],
    max_workers: int = DEFAULT_WORKERS,
    progress_hook: Callable[[dict[str, Any], Exception | None], None] | None = None,
    client: Any = None,
) -> None:
    """以多線程並行下載目錄中所有章節。

    Args:
        catalog: 章節目錄列表。
        max_workers: 最大並行線程數。
        progress_hook: 進度回呼函數，參數為 (chapter_info, exception_or_none)。
        client: 可選的 HTTP 客戶端實例。
    """
    should_close = False
    if client is None:
        client = curl_requests.Session(impersonate="chrome120")
        should_close = True

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 記錄下載前的快取狀態，以識別哪些章節為新下載
            cache_status = {
                chap["num"]: get_chapter_cache_path(chap, CHAPTERS_DIR).exists()
                for chap in catalog
            }
            future_to_chapter = {
                executor.submit(download_chapter, client, chapter, CHAPTERS_DIR): chapter
                for chapter in catalog
            }
            for future in as_completed(future_to_chapter):
                chap = future_to_chapter[future]
                was_cached = cache_status.get(chap["num"], False)
                try:
                    future.result()
                    if progress_hook:
                        try:
                            progress_hook(chap, None, not was_cached)
                        except TypeError:
                            progress_hook(chap, None)
                except Exception as exc:
                    if progress_hook:
                        try:
                            progress_hook(chap, exc, not was_cached)
                        except TypeError:
                            progress_hook(chap, exc)
    finally:
        if should_close and hasattr(client, "close"):
            client.close()

