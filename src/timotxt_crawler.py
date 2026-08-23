"""提莫書屋 (timotxt.com) 爬蟲與小說下載模組。

負責《聚寶仙盆》等提莫書屋小說之目錄解析、字體反爬蟲解碼、多線程並行下載與快取管理。
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from src.cleaner import strip_leading_title
from src.font_decoder import decode_timotxt_text


# 提莫書屋《聚寶仙盆》預設配置
TIMOTXT_BASE_URL = "https://www.timotxt.com"
TIMOTXT_BOOK_ID = "0104529116"
TIMOTXT_BOOK_TITLE = "聚寶仙盆"
TIMOTXT_BOOK_AUTHOR = "香果味奶茶"
TIMOTXT_CATALOG_URL = f"{TIMOTXT_BASE_URL}/{TIMOTXT_BOOK_ID}/dir"

TIMOTXT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / TIMOTXT_BOOK_ID
TIMOTXT_CHAPTERS_DIR = TIMOTXT_DATA_DIR / "chapters"

DEFAULT_WORKERS = 8
REQUEST_TIMEOUT = 15.0
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{TIMOTXT_BASE_URL}/{TIMOTXT_BOOK_ID}/dir",
}

for d in [TIMOTXT_DATA_DIR, TIMOTXT_CHAPTERS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def parse_timotxt_catalog(html_str: str) -> List[Dict[str, Any]]:
    """解析提莫書屋目錄 HTML，提取所有章節並依照章節序號由小到大排序。

    Args:
        html_str: 目錄頁 HTML。

    Returns:
        章節清單列表，每項包含 num, title, url, chapter_id。
    """
    soup = BeautifulSoup(html_str, "html.parser")
    chapters_by_id: Dict[int, Dict[str, Any]] = {}

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        match = re.search(rf"/{TIMOTXT_BOOK_ID}/(\d+)\.html$", href)
        if not match:
            continue
        num = int(match.group(1))
        title = a_tag.get_text(strip=True)
        # 解碼標題中的混淆字（若有）
        title = decode_timotxt_text(title)
        full_url = f"{TIMOTXT_BASE_URL}/{TIMOTXT_BOOK_ID}/{num}.html" if href.startswith("/") else href

        chapters_by_id[num] = {
            "num": num,
            "title": title,
            "url": full_url,
            "chapter_id": str(num),
        }

    catalog = [chapters_by_id[k] for k in sorted(chapters_by_id.keys())]
    return catalog


def fetch_timotxt_catalog(
    client: Any = None, force_refresh: bool = False, cache_dir: Path = TIMOTXT_DATA_DIR
) -> List[Dict[str, Any]]:
    """獲取提莫書屋小說目錄，支援快取與強制線上刷新。"""
    cache_file = cache_dir / "catalog.json"
    if not force_refresh and cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    should_close = False
    if client is None:
        client = curl_requests.Session(impersonate="chrome120")
        should_close = True
    try:
        resp = client.get(TIMOTXT_CATALOG_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        catalog = parse_timotxt_catalog(resp.text)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        return catalog
    except Exception as e:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(f"無法取得提莫書屋小說目錄：{e}") from e
    finally:
        if should_close and hasattr(client, "close"):
            client.close()


def clean_timotxt_content(html_str: str, title: str = "") -> str:
    """清洗提莫書屋章節內容，過濾廣告容器、還原混淆字體、移除開頭重複標題並排版為全形縮排段落。"""
    soup = BeautifulSoup(html_str, "html.parser")
    content_div = soup.find("div", class_="content")
    if not content_div:
        content_div = soup

    # 移除廣告與腳本
    for unwanted in content_div.find_all(["div", "ins", "script"], class_=["gadBlock", "narrow", "adUnit", "clickforceads"]):
        unwanted.decompose()
    for tag in content_div.find_all("script"):
        tag.decompose()

    # 提取所有 <p> 段落
    paragraphs = []
    p_tags = content_div.find_all("p")
    if p_tags:
        for p in p_tags:
            text = p.get_text().strip()
            # 濾除頁尾宣傳/改版提示
            if "溫馨提示" in text or "書架" in text and "閱讀記錄" in text:
                continue
            # 字體解碼還原
            decoded_text = decode_timotxt_text(text)
            if decoded_text:
                paragraphs.append("　　" + decoded_text)
    else:
        # 若無 <p> 標籤，fallback 分行處理
        for line in content_div.get_text().splitlines():
            line = line.strip()
            if not line or "溫馨提示" in line:
                continue
            decoded = decode_timotxt_text(line)
            if decoded:
                paragraphs.append("　　" + decoded)

    full_content = "\n\n".join(paragraphs)
    # 移除開頭重複出現的章節標題
    return strip_leading_title(full_content, title=title)


def get_timotxt_chapter_cache_path(chapter_info: Dict[str, Any], cache_dir: Path = TIMOTXT_CHAPTERS_DIR) -> Path:
    """產生章節快取路徑（補五位數零對齊）。"""
    return cache_dir / f"{chapter_info['num']:05d}_{chapter_info['chapter_id']}.json"


def download_timotxt_chapter(
    client: Any, chapter_info: Dict[str, Any], cache_dir: Path = TIMOTXT_CHAPTERS_DIR
) -> Path:
    """下載單一章節並寫入本機 JSON 快取（支援斷點續傳）。"""
    cache_path = get_timotxt_chapter_cache_path(chapter_info, cache_dir)
    if cache_path.exists():
        return cache_path

    url = chapter_info["url"]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(1.5 * attempt)
                continue
            resp.raise_for_status()
            content = clean_timotxt_content(resp.text, title=chapter_info.get("title", ""))


            data = {
                "num": chapter_info["num"],
                "title": chapter_info["title"],
                "chapter_id": chapter_info["chapter_id"],
                "url": url,
                "content": content,
            }
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return cache_path
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"章節下載失敗 {chapter_info['title']} ({url}): {e}") from e
            time.sleep(0.5 * attempt)

    return cache_path


def download_all_timotxt_chapters(
    catalog: List[Dict[str, Any]],
    max_workers: int = DEFAULT_WORKERS,
    progress_hook: Optional[Callable[[Dict[str, Any], Optional[Exception]], None]] = None,
    cache_dir: Path = TIMOTXT_CHAPTERS_DIR,
) -> None:
    """多線程並行下載提莫書屋章節。"""
    session = curl_requests.Session(impersonate="chrome120")
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {
                executor.submit(download_timotxt_chapter, session, chapter, cache_dir): chapter
                for chapter in catalog
            }
            for future in as_completed(future_to_chapter):
                chap = future_to_chapter[future]
                try:
                    future.result()
                    if progress_hook:
                        progress_hook(chap, None)
                except Exception as exc:
                    if progress_hook:
                        progress_hook(chap, exc)
    finally:
        session.close()
