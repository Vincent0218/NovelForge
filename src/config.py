"""專案全域設定與集中式小說/站點註冊表模組。"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"

DEFAULT_WORKERS = 8
REQUEST_TIMEOUT = 20.0
MAX_RETRIES = 5

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class BookConfig:
    """單本小說與來源站點之完整設定模型。"""

    key: str
    site: str
    book_id: str
    title: str
    author: str
    base_url: str
    catalog_url: str
    data_dir: Path
    chapters_dir: Path
    catalog_cache_path: Path
    headers: Dict[str, str] = field(default_factory=dict)

    def ensure_dirs(self) -> None:
        """確保該書籍專屬之快取與資料目錄存在。"""
        for d in [self.data_dir, self.chapters_dir, OUTPUT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


# 集中註冊表：所有支援的小說清單
BOOKS: Dict[str, BookConfig] = {
    "20": BookConfig(
        key="20",
        site="twkan",
        book_id="20",
        title="我都元嬰期了，你跟我說開學？",
        author="妙妙醬丷",
        base_url="https://twkan.com",
        catalog_url="https://twkan.com/ajax_novels/chapterlist/20.html",
        data_dir=DATA_DIR / "20",
        chapters_dir=DATA_DIR / "20" / "chapters",
        catalog_cache_path=DATA_DIR / "20" / "catalog.json",
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://twkan.com/book/20/index.html",
        },
    ),
    "0104529116": BookConfig(
        key="0104529116",
        site="timotxt",
        book_id="0104529116",
        title="聚寶仙盆",
        author="香果味奶茶",
        base_url="https://www.timotxt.com",
        catalog_url="https://www.timotxt.com/0104529116/dir",
        data_dir=DATA_DIR / "0104529116",
        chapters_dir=DATA_DIR / "0104529116" / "chapters",
        catalog_cache_path=DATA_DIR / "0104529116" / "catalog.json",
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://www.timotxt.com/0104529116/dir",
        },
    ),
}

DEFAULT_BOOK_KEY = "20"


def get_book_config(identifier: str | None = None) -> BookConfig:
    """依據書籍 ID、Key 或書名取得對應的小說設定。

    Args:
        identifier: 書籍 Key、ID 或書名。若為 None 或空字串，則回傳預設小說（我都元嬰期了，你跟我說開學？）。

    Returns:
        BookConfig: 小說設定物件。

    Raises:
        KeyError: 若找不到符合的小說設定。
    """
    if not identifier:
        return BOOKS[DEFAULT_BOOK_KEY]

    # 1. 直接精確比對 key
    if identifier in BOOKS:
        return BOOKS[identifier]

    # 2. 比對 book_id 或 title
    for book in BOOKS.values():
        if identifier == book.book_id or identifier == book.title:
            return book

    # 3. 模糊比對 title（包含關鍵字）
    matched = [book for book in BOOKS.values() if identifier.lower() in book.title.lower()]
    if len(matched) == 1:
        return matched[0]
    elif len(matched) > 1:
        titles = ", ".join(f"'{b.title}'" for b in matched)
        raise KeyError(f"搜尋關鍵字 '{identifier}' 匹配到多本小說: {titles}，請提供更精確的 ID 或名稱。")

    available = ", ".join(f"'{k}' ({v.title})" for k, v in BOOKS.items())
    raise KeyError(f"找不到小說 '{identifier}'。目前支援的小說清單包含: {available}")


# 初始化所有目錄
for d in [DATA_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
for book in BOOKS.values():
    book.ensure_dirs()

# 向下相容的全域常數別名（預設為第一本書）
_default_book = BOOKS[DEFAULT_BOOK_KEY]
BOOK_ID = _default_book.book_id
BOOK_TITLE = _default_book.title
BOOK_AUTHOR = _default_book.author
BASE_URL = _default_book.base_url
CHAPTER_LIST_URL = _default_book.catalog_url
CHAPTERS_DIR = _default_book.chapters_dir
HEADERS = _default_book.headers


