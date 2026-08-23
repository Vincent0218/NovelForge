"""電子書（EPUB 與 TXT）生成模組。

本模組負責讀取本機快取的章節 JSON 資料，並組合輸出為標準格式的 EPUB 電子書
與單一 TXT 純文字檔案。
"""
import html
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from ebooklib import epub
from src.config import CHAPTERS_DIR, BOOK_TITLE, BOOK_AUTHOR


def get_system_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """尋找本機可用的繁體/中文字型，若無則回退至預設字型。"""
    font_paths = [
        "C:/Windows/Fonts/msjhbd.ttc" if bold else "C:/Windows/Fonts/msjh.ttc",  # 微軟正黑體
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",  # 微軟雅黑
        "C:/Windows/Fonts/simsun.ttc",                                          # 宋體
        "/System/Library/Fonts/PingFang.ttc",                                   # macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # Linux
    ]
    for p in font_paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_cover_image(title: str, author: str, width: int = 1200, height: int = 1600) -> bytes:
    """動態繪製標準 3:4 高畫質繁體中文電子書封面圖片（JPEG 格式）。

    Args:
        title: 書籍名稱。
        author: 書籍作者。
        width: 封面寬度（預設 1200 px）。
        height: 封面高度（預設 1600 px）。

    Returns:
        JPEG 圖片的二進位資料 bytes。
    """
    w, h = width, height
    img = Image.new("RGB", (w, h), color=(18, 24, 38))
    draw = ImageDraw.Draw(img)

    # 1. 繪製深邃墨藍漸層背景
    for y in range(h):
        r = int(18 + (30 - 18) * (y / h))
        g = int(24 + (38 - 24) * (y / h))
        b = int(38 + (58 - 38) * (y / h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 2. 繪製古典雙重邊框
    margin = 60
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(195, 160, 105), width=4)
    inner_m = 75
    draw.rectangle([inner_m, inner_m, w - inner_m, h - inner_m], outline=(150, 120, 80), width=1)

    # 四角裝飾
    c_size = 12
    for cx, cy in [(inner_m, inner_m), (w - inner_m, inner_m), (inner_m, h - inner_m), (w - inner_m, h - inner_m)]:
        draw.rectangle([cx - c_size, cy - c_size, cx + c_size, cy + c_size], fill=(195, 160, 105))

    # 3. 頂部標籤
    tag_font = get_system_font(36)
    draw.text((w / 2, 220), "— 精 校 典 藏 版 —", font=tag_font, fill=(195, 160, 105), anchor="mm")

    # 4. 書名自動折行排版（居中大字）
    title_font = get_system_font(72, bold=True)
    chars_per_line = 7 if len(title) > 10 else 9
    title_lines = []
    for i in range(0, len(title), chars_per_line):
        title_lines.append(title[i:i + chars_per_line])

    title_y_start = 560 - (len(title_lines) - 1) * 55
    for idx, t_line in enumerate(title_lines):
        draw.text((w / 2, title_y_start + idx * 110), t_line, font=title_font, fill=(255, 245, 225), anchor="mm")

    # 5. 作者資訊
    author_font = get_system_font(42)
    draw.text((w / 2, 1050), f"著  者 ： {author}", font=author_font, fill=(210, 185, 145), anchor="mm")

    # 分隔線
    draw.line([(w / 2 - 150, 1140), (w / 2 + 150, 1140)], fill=(195, 160, 105), width=2)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()



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
    add_cover: bool = True,
) -> Path:
    """將所有章節快取內容封裝並輸出為標準 EPUB 電子書檔案（含封面與精緻排版）。

    Args:
        catalog: 章節目錄列表。
        output_path: 輸出的 EPUB 檔案路徑。
        title: 書籍名稱。
        author: 書籍作者。
        cache_dir: 章節快取目錄。
        add_cover: 是否自動生成並嵌入書籍封面圖（預設 True）。

    Returns:
        輸出檔案路徑。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier(f"novelforge-{title}")
    book.set_title(title)
    book.set_language("zh-TW")
    book.add_author(author)

    # 1. 加入高畫質電子書封面
    if add_cover:
        cover_bytes = generate_cover_image(title, author)
        book.set_cover("cover.jpg", cover_bytes)

    epub_chapters = []
    toc = []

    # 2. 升級版專業繁體中文排版樣式
    style = """
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: "PingFang TC", "Microsoft JhengHei", "Noto Serif TC", "Songti TC", serif;
        line-height: 1.85;
        margin: 1.2em;
        text-align: justify;
        color: #2c3e50;
    }
    h1 {
        text-align: center;
        margin-top: 1.6em;
        margin-bottom: 2em;
        font-size: 1.45em;
        font-weight: bold;
        letter-spacing: 0.05em;
        color: #1a252f;
    }
    p {
        text-indent: 2em;
        margin-top: 0;
        margin-bottom: 0.6em;
    }
    @media (prefers-color-scheme: dark) {
        body { color: #dcdcdc; background-color: #1a1a1a; }
        h1 { color: #f5f5f5; }
    }
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
            # 移除開頭全形空白與多餘空白，完全交由 CSS text-indent: 2em 統一控制縮排
            p_clean = re.sub(r"^[　\s]+", "", p.strip())
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
    book.spine = ["cover", "nav"] + epub_chapters if add_cover else ["nav"] + epub_chapters

    epub.write_epub(str(output_path), book, {})
    return output_path

