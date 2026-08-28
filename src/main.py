"""小說爬蟲與電子書生成 CLI 主程式入口。"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import time
from typing import Any, Callable, List
from tqdm import tqdm

from src.builder import build_epub, build_txt
from src.config import (
    BOOKS,
    DEFAULT_WORKERS,
    OUTPUT_DIR,
    BookConfig,
    get_book_config,
)
from src.crawler import (
    download_all_chapters,
    fetch_catalog,
    get_chapter_cache_path,
)
from src.timotxt_crawler import (
    download_all_timotxt_chapters,
    fetch_timotxt_catalog,
    get_timotxt_chapter_cache_path,
)


def list_available_books() -> None:
    """列出目前註冊表支援的所有小說與來源站點。"""
    print("\n📚 目前支援的小說清單：")
    print("-" * 75)
    print(f"{'Key / ID':<12} | {'來源站點':<10} | {'書名':<22} | {'作者':<12}")
    print("-" * 75)
    for key, book in BOOKS.items():
        print(f"{key:<12} | {book.site:<10} | {book.title:<22} | {book.author:<12}")
    print("-" * 75)
    print("💡 執行範例：uv run python -m src.main --book 0104529116\n")


def crawl_and_build_book(
    book_config: BookConfig,
    offline: bool = False,
    workers: int = DEFAULT_WORKERS,
) -> None:
    """執行單本小說的目錄獲取、並行下載與電子書封裝完整流程。"""
    book_config.ensure_dirs()
    print(f"📖 開始抓取小說：《{book_config.title}》（作者：{book_config.author}，來源：{book_config.site}）")

    # 1. 取得章節目錄
    force_refresh = not offline
    print(f"📋 正在獲取章節目錄（{'線上刷新最新章節' if force_refresh else '離線快取模式'}）...")

    if book_config.site == "timotxt":
        catalog = fetch_timotxt_catalog(force_refresh=force_refresh, book_config=book_config)
        get_cache_path = lambda chap: get_timotxt_chapter_cache_path(chap, book_config.chapters_dir)
        download_fn = lambda chaps, w, hook: download_all_timotxt_chapters(
            chaps, max_workers=w, progress_hook=hook, cache_dir=book_config.chapters_dir
        )
    else:
        catalog = fetch_catalog(force_refresh=force_refresh, book_config=book_config)
        get_cache_path = lambda chap: get_chapter_cache_path(chap, book_config.chapters_dir)
        download_fn = lambda chaps, w, hook: download_all_chapters(
            chaps, max_workers=w, progress_hook=hook, cache_dir=book_config.chapters_dir
        )

    total_chapters = len(catalog)
    cached_count = sum(1 for c in catalog if get_cache_path(c).exists())
    new_chapters_count = total_chapters - cached_count
    print(f"共發現 {total_chapters} 個章節（本機已快取 {cached_count} 章，本次需增量下載 {new_chapters_count} 章）。")

    # 2. 下載章節（已快取的章節自動秒級略過）
    print(f"🚀 開始檢查與下載章節（Worker: {workers}）...")
    with tqdm(total=total_chapters, desc="下載進度", unit="章") as pbar:

        def on_progress(chap: dict, err: Exception | None, is_new: bool = False) -> None:
            if err:
                tqdm.write(f"❌ 下載出錯 [{chap['title']}]: {err}")
            elif is_new:
                tqdm.write(f"📥 下載新章節：{chap['title']}")
            pbar.set_postfix_str(chap["title"][-15:] if len(chap["title"]) > 15 else chap["title"])
            pbar.update(1)

        download_fn(catalog, workers, on_progress)

    # 補抓未完成章節（最多重試 5 輪）
    retry_round = 1
    while retry_round <= 5:
        missing = [c for c in catalog if not get_cache_path(c).exists()]
        if not missing:
            break
        print(f"⚠️ 尚有 {len(missing)} 個章節未下載成功，正在進行第 {retry_round} 輪補抓...")
        time.sleep(2.0)
        with tqdm(total=len(missing), desc=f"補抓進度 (第{retry_round}輪)", unit="章") as pbar:

            def on_retry_progress(chap: dict, err: Exception | None, is_new: bool = False) -> None:
                if err:
                    tqdm.write(f"❌ 補抓出錯 [{chap['title']}]: {err}")
                else:
                    tqdm.write(f"📥 補抓成功：{chap['title']}")
                pbar.set_postfix_str(chap["title"][-15:] if len(chap["title"]) > 15 else chap["title"])
                pbar.update(1)

            download_fn(missing, workers, on_retry_progress)

        retry_round += 1

    missing = [c for c in catalog if not get_cache_path(c).exists()]
    if missing:
        raise RuntimeError(f"尚有 {len(missing)} 個章節經過多次重試仍未能下載完成！")

    # 3. 建立輸出檔案
    txt_path = OUTPUT_DIR / f"{book_config.title}.txt"
    epub_path = OUTPUT_DIR / f"{book_config.title}.epub"

    print("📄 正在產生 TXT 純文字檔...")
    build_txt(
        catalog,
        txt_path,
        title=book_config.title,
        author=book_config.author,
        cache_dir=book_config.chapters_dir,
    )
    txt_size = f" ({txt_path.stat().st_size / 1024 / 1024:.2f} MB)" if txt_path.exists() else ""
    print(f"✅ TXT 產生完成：{txt_path}{txt_size}")

    print("📚 正在封裝 EPUB 電子書...")
    build_epub(
        catalog,
        epub_path,
        title=book_config.title,
        author=book_config.author,
        cache_dir=book_config.chapters_dir,
    )
    epub_size = f" ({epub_path.stat().st_size / 1024 / 1024:.2f} MB)" if epub_path.exists() else ""
    print(f"✅ EPUB 封裝完成：{epub_path}{epub_size}")
    print(f"🎉 《{book_config.title}》全部 {total_chapters} 章下載與電子書封裝完成！")


def main(argv: list[str] | None = None) -> None:
    """CLI 主程式入口。"""
    parser = argparse.ArgumentParser(description="小說爬蟲與電子書生成工具（支援追更與增量更新）")
    parser.add_argument(
        "--book",
        "-b",
        type=str,
        default=None,
        help="指定要下載的小說 Key、書籍 ID 或書名（預設: 20）",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="列出目前註冊表支援的所有小說清單",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="離線模式：僅讀取本機快取的目錄，不向網站請求最新目錄",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"並行下載線程數 (預設: {DEFAULT_WORKERS})",
    )
    args = parser.parse_args(argv)

    if args.list:
        list_available_books()
        return

    book_config = get_book_config(args.book)
    crawl_and_build_book(book_config, offline=args.offline, workers=args.workers)


if __name__ == "__main__":
    main()
