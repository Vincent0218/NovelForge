"""小說爬蟲與電子書生成 CLI 主程式入口。"""
import sys
from tqdm import tqdm

from src.builder import build_epub, build_txt
from src.config import BOOK_AUTHOR, BOOK_TITLE, DEFAULT_WORKERS, OUTPUT_DIR
from src.crawler import download_all_chapters, fetch_catalog


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
