"""設定模組測試。"""
import pytest
from src.config import (
    BASE_URL,
    BOOK_ID,
    BOOKS,
    CHAPTER_LIST_URL,
    CHAPTERS_DIR,
    OUTPUT_DIR,
    get_book_config,
)


def test_config_values():
    """驗證設定值與預設目錄結構。"""
    assert BOOK_ID == "20"
    assert "twkan.com" in BASE_URL
    assert "chapterlist/20.html" in CHAPTER_LIST_URL
    assert CHAPTERS_DIR.exists()
    assert OUTPUT_DIR.exists()


def test_books_registry():
    """驗證小說註冊表 BOOKS 的內容完整性。"""
    assert "20" in BOOKS
    assert "0104529116" in BOOKS
    assert BOOKS["20"].title == "我都元嬰期了，你跟我說開學？"
    assert BOOKS["0104529116"].title == "聚寶仙盆"
    assert BOOKS["20"].site == "twkan"
    assert BOOKS["0104529116"].site == "timotxt"


def test_get_book_config():
    """驗證 get_book_config 各種查詢模式（預設、Key、ID、書名模糊比對）。"""
    # 1. 預設模式
    default_book = get_book_config()
    assert default_book.key == "20"

    # 2. Key / ID 查詢
    book_timotxt = get_book_config("0104529116")
    assert book_timotxt.title == "聚寶仙盆"

    # 3. 書名比對
    book_by_name = get_book_config("聚寶仙盆")
    assert book_by_name.key == "0104529116"

    # 4. 書名關鍵字模糊比對
    book_by_fuzzy = get_book_config("元嬰期")
    assert book_by_fuzzy.key == "20"

    # 5. 不存在的書名拋出 KeyError
    with pytest.raises(KeyError, match="找不到小說"):
        get_book_config("不存在的神秘小說")


