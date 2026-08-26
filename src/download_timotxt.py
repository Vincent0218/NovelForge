"""提莫書屋《聚寶仙盆》專屬下載與轉檔執行腳本。"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import time
from tqdm import tqdm

from src.builder import build_epub, build_txt
from src.config import OUTPUT_DIR
from src.timotxt_crawler import (
    DEFAULT_WORKERS,
    TIMOTXT_BOOK_AUTHOR,
    TIMOTXT_BOOK_TITLE,
    TIMOTXT_CHAPTERS_DIR,
    download_all_timotxt_chapters,
    fetch_timotxt_catalog,
    get_timotxt_chapter_cache_path,
)


def main(argv: list[str] | None = None) -> None:
    """執行《聚寶仙盆》目錄獲取、並行下載、TXT 組合與 EPUB 封裝之完整流程。"""
    parser = argparse.ArgumentParser(description="提莫書屋《聚寶仙盆》小說抓取與轉檔工具")
    parser.add_argument("--offline", action="store_true", help="離線模式：僅讀取本機快取目錄，不連網更新")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"並行下載線程數 (預設: {DEFAULT_WORKERS})")
    args = parser.parse_args(argv)

    print(f"📖 開始抓取小說：《{TIMOTXT_BOOK_TITLE}》（作者：{TIMOTXT_BOOK_AUTHOR}）")

    # 1. 取得目錄
    force_refresh = not args.offline
    print(f"📋 正在獲取章節目錄（{'線上刷新' if force_refresh else '離線快取'}）...")
    catalog = fetch_timotxt_catalog(force_refresh=force_refresh)
    total_chapters = len(catalog)
    cached_count = sum(1 for c in catalog if get_timotxt_chapter_cache_path(c, TIMOTXT_CHAPTERS_DIR).exists())
    new_chapters_count = total_chapters - cached_count

    print(f"共發現 {total_chapters} 個章節（本機已快取 {cached_count} 章，本次需增量下載 {new_chapters_count} 章）。")

    # 2. 下載章節
    workers = args.workers
    print(f"🚀 開始檢查與下載章節（Worker: {workers}）...")

    with tqdm(total=total_chapters, desc="下載進度", unit="章") as pbar:

        def on_progress(chap: dict, err: Exception | None) -> None:
            if err:
                tqdm.write(f"❌ 下載出錯 [{chap['title']}]: {err}")
            pbar.update(1)

        download_all_timotxt_chapters(
            catalog, max_workers=workers, progress_hook=on_progress, cache_dir=TIMOTXT_CHAPTERS_DIR
        )

    # 補抓未完成章節（最多重試 5 輪）
    retry_round = 1
    while retry_round <= 5:
        missing = [c for c in catalog if not get_timotxt_chapter_cache_path(c, TIMOTXT_CHAPTERS_DIR).exists()]
        if not missing:
            break
        print(f"⚠️ 尚有 {len(missing)} 個章節未下載成功，正在進行第 {retry_round} 輪補抓...")
        time.sleep(2.0)
        with tqdm(total=len(missing), desc=f"補抓進度 (第{retry_round}輪)", unit="章") as pbar:

            def on_retry_progress(chap: dict, err: Exception | None) -> None:
                if err:
                    tqdm.write(f"❌ 補抓出錯 [{chap['title']}]: {err}")
                pbar.update(1)

            download_all_timotxt_chapters(
                missing, max_workers=workers, progress_hook=on_retry_progress, cache_dir=TIMOTXT_CHAPTERS_DIR
            )
        retry_round += 1

    missing = [c for c in catalog if not get_timotxt_chapter_cache_path(c, TIMOTXT_CHAPTERS_DIR).exists()]
    if missing:
        raise RuntimeError(f"尚有 {len(missing)} 個章節經過多次重試仍未能下載完成！")

    # 3. 建立輸出檔案
    txt_path = OUTPUT_DIR / f"{TIMOTXT_BOOK_TITLE}.txt"
    epub_path = OUTPUT_DIR / f"{TIMOTXT_BOOK_TITLE}.epub"

    print("📄 正在產生 TXT 純文字檔...")
    build_txt(
        catalog,
        txt_path,
        title=TIMOTXT_BOOK_TITLE,
        author=TIMOTXT_BOOK_AUTHOR,
        cache_dir=TIMOTXT_CHAPTERS_DIR,
    )
    print(f"✅ TXT 產生完成：{txt_path} ({txt_path.stat().st_size / 1024 / 1024:.2f} MB)")

    print("📚 正在封裝 EPUB 電子書...")
    build_epub(
        catalog,
        epub_path,
        title=TIMOTXT_BOOK_TITLE,
        author=TIMOTXT_BOOK_AUTHOR,
        cache_dir=TIMOTXT_CHAPTERS_DIR,
    )
    print(f"✅ EPUB 封裝完成：{epub_path} ({epub_path.stat().st_size / 1024 / 1024:.2f} MB)")

    print(f"🎉 《{TIMOTXT_BOOK_TITLE}》全部 {total_chapters} 章下載與電子書封裝完成！")



if __name__ == "__main__":
    main()
