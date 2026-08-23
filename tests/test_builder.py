"""電子書生成器測試模組。"""
import json
import pytest
from pathlib import Path
from ebooklib import epub
from src.builder import load_cached_chapter, build_txt, build_epub


def test_load_cached_chapter(tmp_path: Path):
    """測試讀取快取章節成功與失敗的情境。"""
    cache_dir = tmp_path / "chapters"
    cache_dir.mkdir()

    chapter_info = {"num": 1, "title": "第1章 測試", "chapter_id": "101"}
    cpath = cache_dir / "00001_101.json"
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump({"num": 1, "title": "第1章 測試", "content": "測試內容段落。"}, f)

    data = load_cached_chapter(chapter_info, cache_dir=cache_dir)
    assert data["num"] == 1
    assert data["title"] == "第1章 測試"
    assert data["content"] == "測試內容段落。"

    # 測試快取遺失時拋出 FileNotFoundError
    missing_info = {"num": 2, "title": "第2章 遺失", "chapter_id": "102"}
    with pytest.raises(FileNotFoundError, match="尚未下載快取章節"):
        load_cached_chapter(missing_info, cache_dir=cache_dir)


def test_build_txt_and_epub(tmp_path: Path):
    """測試 TXT 與 EPUB 電子書生成整合。"""
    cache_dir = tmp_path / "chapters"
    cache_dir.mkdir()

    catalog = [
        {"num": 1, "title": "第1章 測試開端", "chapter_id": "101"},
        {"num": 2, "title": "第2章 續集進展", "chapter_id": "102"},
    ]

    for item in catalog:
        cpath = cache_dir / f"{item['num']:05d}_{item['chapter_id']}.json"
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "num": item["num"],
                    "title": item["title"],
                    "content": f"這是{item['title']}的第一段。\n\n這是第二段。",
                },
                f,
            )

    # 測試 TXT 生成
    txt_out = tmp_path / "output" / "test.txt"
    result_txt = build_txt(
        catalog,
        txt_out,
        title="自訂小說名稱",
        author="自訂作者",
        cache_dir=cache_dir,
    )
    assert result_txt == txt_out
    assert txt_out.exists()
    content = txt_out.read_text(encoding="utf-8")
    assert "自訂小說名稱" in content
    assert "自訂作者" in content
    assert "第1章 測試開端" in content
    assert "這是第2章 續集進展的第一段。" in content
    assert "------------------------------" in content

    # 測試 EPUB 生成
    epub_out = tmp_path / "output" / "test.epub"
    result_epub = build_epub(
        catalog,
        epub_out,
        title="測試小說",
        author="作者名",
        cache_dir=cache_dir,
    )
    assert result_epub == epub_out
    assert epub_out.exists()
    assert epub_out.stat().st_size > 0

    # 讀取生成的 EPUB 驗證內容
    book = epub.read_epub(str(epub_out))
    assert book.get_metadata("DC", "title")[0][0] == "測試小說"
    assert book.get_metadata("DC", "creator")[0][0] == "作者名"
    assert book.get_metadata("DC", "language")[0][0] == "zh-TW"

    # 驗證章節項目
    items = list(book.get_items_of_type(9))  # 9 = ITEM_DOCUMENT in ebooklib
    doc_titles = [item.get_name() for item in items]
    assert "chap_00001.xhtml" in doc_titles
    assert "chap_00002.xhtml" in doc_titles
