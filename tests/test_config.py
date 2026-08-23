"""設定模組測試。"""
from src.config import BOOK_ID, BASE_URL, CHAPTER_LIST_URL, CHAPTERS_DIR, OUTPUT_DIR


def test_config_values():
    """驗證設定值與預設目錄結構。"""
    assert BOOK_ID == "20"
    assert "twkan.com" in BASE_URL
    assert "chapterlist/20.html" in CHAPTER_LIST_URL
    assert CHAPTERS_DIR.exists()
    assert OUTPUT_DIR.exists()
