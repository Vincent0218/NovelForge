"""專案全域設定模組。"""
from pathlib import Path

BOOK_ID = "20"
BOOK_TITLE = "我都元嬰期了，你跟我說開學？"
BOOK_AUTHOR = "妙妙醬丷"
BASE_URL = "https://twkan.com"
CHAPTER_LIST_URL = f"{BASE_URL}/ajax_novels/chapterlist/{BOOK_ID}.html"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CHAPTERS_DIR = DATA_DIR / "chapters"
OUTPUT_DIR = ROOT_DIR / "output"

DEFAULT_WORKERS = 8
REQUEST_TIMEOUT = 20.0
MAX_RETRIES = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/book/{BOOK_ID}/index.html",
}

for d in [DATA_DIR, CHAPTERS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


