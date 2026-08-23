"""小說爬蟲與電子書生成 CLI 主程式入口。"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time
from tqdm import tqdm

from src.builder import build_epub, build_txt
from src.config import BOOK_AUTHOR, BOOK_TITLE, DEFAULT_WORKERS, OUTPUT_DIR
from src.crawler import download_all_chapters, fetch_catalog, get_chapter_cache_path


def main() -> None:
    """執行小說目錄獲取、章節並行下載、TXT 組合與 EPUB 封裝之完整流程。"""
    print(f"📖 開始抓取小說：《{BOOK_TITLE}》（作者：{BOOK_AUTHOR}）")

    # 1. 取得目錄
    print("📋 正在獲取章節目錄...")
    catalog = fetch_catalog()
    total_chapters = len(catalog)
    print(f"共發現 {total_chapters} 個章節。")

    # 2. 下載章節
    print(f"🚀 開始下載章節（Worker: {DEFAULT_WORKERS}）...")
    with tqdm(total=total_chapters, desc="下載進度", unit="章") as pbar:

        def on_progress(chap: dict, err: Exception | None) -> None:
            if err:
                tqdm.write(f"❌ 下載出錯 [{chap['title']}]: {err}")
            pbar.update(1)

        download_all_chapters(catalog, max_workers=DEFAULT_WORKERS, progress_hook=on_progress)

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

            download_all_chapters(missing, max_workers=DEFAULT_WORKERS, progress_hook=on_retry_progress)
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
