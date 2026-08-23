"""電子書（EPUB 與 TXT）生成模組。

本模組負責讀取本機快取的章節 JSON 資料，並組合輸出為標準格式的 EPUB 電子書
與單一 TXT 純文字檔案。
"""
import html
import json
from pathlib import Path
from ebooklib import epub
from src.config import CHAPTERS_DIR, BOOK_TITLE, BOOK_AUTHOR


def load_cached_chapter(chapter_info: dict, cache_dir: Path = CHAPTERS_DIR) -> dict:
    """讀取本機快取的單一章節 JSON 檔案。

    Args:
        chapter_info: 包含 num, chapter_id, title 等資訊的字典。
        cache_dir: 快取目錄路徑，預設為 CHAPTERS_DIR。

    Returns:
        包含章節資料（num, title, content 等）的字典。

    Raises:
        FileNotFoundError: 當找不到對應的快取檔案時拋出。
    """
    cache_path = cache_dir / f"{chapter_info['num']:05d}_{chapter_info['chapter_id']}.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"尚未下載快取章節：{chapter_info['title']} ({cache_path})")
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_txt(
    catalog: list[dict],
    output_path: Path,
    title: str = BOOK_TITLE,
    author: str = BOOK_AUTHOR,
    cache_dir: Path = CHAPTERS_DIR,
) -> Path:
    """將所有章節快取內容組合並輸出為單一 TXT 純文字檔案。

    Args:
        catalog: 章節目錄列表。
        output_path: 輸出的 TXT 檔案路徑。
        title: 書籍名稱。
        author: 書籍作者。
        cache_dir: 章節快取目錄。

    Returns:
        輸出檔案路徑。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write(f"{title}\n")
        f_out.write(f"作者：{author}\n\n")
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
    cache_dir: Path = CHAPTERS_DIR,
) -> Path:
    """將所有章節快取內容封裝並輸出為標準 EPUB 電子書檔案。

    Args:
        catalog: 章節目錄列表。
        output_path: 輸出的 EPUB 檔案路徑。
        title: 書籍名稱。
        author: 書籍作者。
        cache_dir: 章節快取目錄。

    Returns:
        輸出檔案路徑。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier(f"twkan-novel-{title}")
    book.set_title(title)
    book.set_language("zh-TW")
    book.add_author(author)

    epub_chapters = []
    toc = []

    # 預設排版樣式
    style = """
    @namespace epub "http://www.idpf.org/2007/ops";
    body { font-family: "PingFang TC", "Microsoft JhengHei", "Noto Sans TC", sans-serif; line-height: 1.8; margin: 1em; }
    h1 { text-align: center; margin-bottom: 1.5em; font-size: 1.4em; }
    p { text-indent: 2em; margin-bottom: 0.8em; }
    """
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style.strip(),
    )
    book.add_item(nav_css)

    for item in catalog:
        data = load_cached_chapter(item, cache_dir=cache_dir)
        c_title = data["title"]
        file_name = f"chap_{item['num']:05d}.xhtml"

        # 轉換段落為 XHTML <p>，並跳脫特殊字元
        paragraphs = data["content"].split("\n\n")
        escaped_title = html.escape(c_title)
        html_content = f"<h1>{escaped_title}</h1>\n"
        for p in paragraphs:
            p_clean = p.strip()
            if p_clean:
                escaped_p = html.escape(p_clean).replace("\n", "<br/>")
                html_content += f"<p>{escaped_p}</p>\n"

        c = epub.EpubHtml(title=c_title, file_name=file_name, lang="zh-TW")
        c.content = f"<html><head><title>{escaped_title}</title><link rel='stylesheet' href='style/nav.css'/></head><body>{html_content}</body></html>"
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
