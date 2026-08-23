"""小說爬蟲與電子書生成 CLI 主程式入口。"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import time
from tqdm import tqdm


from src.builder import build_epub, build_txt
from src.config import BOOK_AUTHOR, BOOK_TITLE, DEFAULT_WORKERS, OUTPUT_DIR
from src.crawler import download_all_chapters, fetch_catalog, get_chapter_cache_path


def main(argv: list[str] | None = None) -> None:
    """執行小說目錄獲取、章節並行下載、TXT 組合與 EPUB 封裝之完整流程。"""
    parser = argparse.ArgumentParser(description="小說爬蟲與電子書生成工具（支援追更與增量更新）")
    parser.add_argument("--offline", action="store_true", help="離線模式：僅讀取本機快取的目錄，不向網站請求最新目錄")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"並行下載線程數 (預設: {DEFAULT_WORKERS})")
    args = parser.parse_args(argv)


    print(f"📖 開始抓取小說：《{BOOK_TITLE}》（作者：{BOOK_AUTHOR}）")

    # 1. 取得目錄（預設聯網取得最新章節目錄，支援追更）
    force_refresh = not args.offline
    print(f"📋 正在獲取章節目錄（{'線上刷新最新章節' if force_refresh else '離線快取模式'}）...")
    catalog = fetch_catalog(force_refresh=force_refresh)
    total_chapters = len(catalog)
    print(f"共發現 {total_chapters} 個章節。")

    # 2. 下載章節（已快取的章節會自動跳過）
    workers = args.workers
    print(f"🚀 開始檢查與下載章節（Worker: {workers}）...")

    with tqdm(total=total_chapters, desc="下載進度", unit="章") as pbar:

        def on_progress(chap: dict, err: Exception | None) -> None:
            if err:
                tqdm.write(f"❌ 下載出錯 [{chap['title']}]: {err}")
            pbar.update(1)

        download_all_chapters(catalog, max_workers=workers, progress_hook=on_progress)

    # 補抓未完成章節（最多重試 5 輪）
    retry_round = 1
    while retry_round <= 5:
        missing = [c for c in catalog if not get_chapter_cache_path(c).exists()]
        if not missing:
            break
        print(f"⚠️ 尚有 {len(missing)} 個章節未下載成功，正在進行第 {retry_round} 輪補抓...")
        time.sleep(2.0)
        with tqdm(total=len(missing), desc=f"補抓進度 (第{retry_round}輪)", unit="章") as pbar:

            def on_retry_progress(chap: dict, err: Exception | None) -> None:
                if err:
                    tqdm.write(f"❌ 補抓出錯 [{chap['title']}]: {err}")
                pbar.update(1)

            download_all_chapters(missing, max_workers=workers, progress_hook=on_retry_progress)

        retry_round += 1

    missing = [c for c in catalog if not get_chapter_cache_path(c).exists()]
    if missing:
        raise RuntimeError(f"尚有 {len(missing)} 個章節經過多次重試仍未能下載完成！")

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
