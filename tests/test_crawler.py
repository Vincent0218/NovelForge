"""爬蟲核心模組單元測試。"""

import json
from unittest.mock import MagicMock, patch
import pytest
import httpx

from src.crawler import (
    parse_catalog_html,
    fetch_catalog,
    get_chapter_cache_path,
    download_chapter,
    download_all_chapters,
)


def test_parse_catalog_html():
    html = """
    <ul>
      <li data-num="2"><a href="https://twkan.com/txt/20/29466" title="第2章">第2章 早說了 </a></li>
      <li data-num="1"><a href="https://twkan.com/txt/20/29465" title="第1章">第1章 修真界歸來 </a></li>
      <li data-num="invalid"><a href="https://twkan.com/txt/20/29467.html" title="第3章">第3章 測試</a></li>
      <li data-num="4">無連結項目</li>
    </ul>
    """
    catalog = parse_catalog_html(html)
    assert len(catalog) == 3
    # 驗證排序與欄位
    assert catalog[0]["num"] == 1
    assert catalog[0]["title"] == "第1章 修真界歸來"
    assert catalog[0]["url"] == "https://twkan.com/txt/20/29465"
    assert catalog[0]["chapter_id"] == "29465"

    assert catalog[1]["num"] == 2
    assert catalog[1]["title"] == "第2章 早說了"
    assert catalog[1]["url"] == "https://twkan.com/txt/20/29466"
    assert catalog[1]["chapter_id"] == "29466"

    # invalid num 的 fallback
    assert catalog[2]["title"] == "第3章 測試"
    assert catalog[2]["chapter_id"] == "29467"


def test_get_chapter_cache_path(tmp_path):
    chapter_info = {
        "num": 5,
        "title": "第5章 測試章節",
        "url": "https://twkan.com/txt/20/29469",
        "chapter_id": "29469",
    }
    path = get_chapter_cache_path(chapter_info, cache_dir=tmp_path)
    assert path == tmp_path / "00005_29469.json"


def test_fetch_catalog_from_cache(tmp_path):
    cache_file = tmp_path / "catalog.json"
    fake_catalog = [{"num": 1, "title": "第1章", "url": "url1", "chapter_id": "1"}]
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(fake_catalog, f, ensure_ascii=False)

    with patch("src.crawler.DATA_DIR", tmp_path):
        mock_client = MagicMock()
        result = fetch_catalog(client=mock_client)
        assert result == fake_catalog
        mock_client.get.assert_not_called()


def test_fetch_catalog_from_network(tmp_path):
    html = """
    <ul>
      <li data-num="1"><a href="https://twkan.com/txt/20/29465">第1章</a></li>
    </ul>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    with patch("src.crawler.DATA_DIR", tmp_path):
        result = fetch_catalog(client=mock_client)
        assert len(result) == 1
        assert result[0]["num"] == 1
        assert result[0]["chapter_id"] == "29465"
        # 驗證快取檔案已寫入
        cache_file = tmp_path / "catalog.json"
        assert cache_file.exists()


def test_fetch_catalog_default_client(tmp_path):
    html = '<li data-num="1"><a href="/txt/20/1">第1章</a></li>'
    with patch("src.crawler.DATA_DIR", tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value = mock_client_instance
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_client_instance.get.return_value = mock_resp

            result = fetch_catalog()
            assert len(result) == 1
            mock_client_instance.close.assert_called_once()


def test_download_chapter_cached(tmp_path):
    chapter_info = {
        "num": 1,
        "title": "第1章 修真界歸來",
        "url": "https://twkan.com/txt/20/29465",
        "chapter_id": "29465",
    }
    cache_path = tmp_path / "00001_29465.json"
    cache_path.write_text(json.dumps({"content": "已快取內容"}), encoding="utf-8")

    mock_client = MagicMock()
    saved_path = download_chapter(mock_client, chapter_info, cache_dir=tmp_path)
    assert saved_path == cache_path
    mock_client.get.assert_not_called()


def test_download_chapter_success(tmp_path):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<div id="txtcontent0">第1章內文測試<br>第二行測試</div>'
    mock_resp.raise_for_status.return_value = None
    mock_client.get.return_value = mock_resp

    chapter_info = {
        "num": 1,
        "title": "第1章 修真界歸來",
        "url": "https://twkan.com/txt/20/29465",
        "chapter_id": "29465",
    }

    saved_path = download_chapter(mock_client, chapter_info, cache_dir=tmp_path)
    assert saved_path.exists()

    with open(saved_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["num"] == 1
    assert data["title"] == "第1章 修真界歸來"
    assert data["chapter_id"] == "29465"
    assert "第1章內文測試" in data["content"]
    assert "第二行測試" in data["content"]


def test_download_chapter_retry_success(tmp_path):
    mock_client = MagicMock()
    mock_fail_resp = MagicMock()
    mock_fail_resp.raise_for_status.side_effect = httpx.HTTPError("連線錯誤")

    mock_success_resp = MagicMock()
    mock_success_resp.raise_for_status.return_value = None
    mock_success_resp.text = '<div id="txtcontent0">成功重試</div>'

    mock_client.get.side_effect = [mock_fail_resp.raise_for_status.side_effect, mock_success_resp]

    chapter_info = {
        "num": 2,
        "title": "第2章 重試測試",
        "url": "https://twkan.com/txt/20/29466",
        "chapter_id": "29466",
    }

    with patch("time.sleep", return_value=None):
        saved_path = download_chapter(mock_client, chapter_info, cache_dir=tmp_path)
    assert saved_path.exists()
    assert mock_client.get.call_count == 2


def test_download_chapter_failure_raises(tmp_path):
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("無法連線")

    chapter_info = {
        "num": 3,
        "title": "第3章 失敗測試",
        "url": "https://twkan.com/txt/20/29467",
        "chapter_id": "29467",
    }

    with patch("time.sleep", return_value=None):
        with pytest.raises(RuntimeError, match="章節下載失敗"):
            download_chapter(mock_client, chapter_info, cache_dir=tmp_path)


def test_download_all_chapters(tmp_path):
    catalog = [
        {"num": 1, "title": "第1章", "url": "https://twkan.com/1", "chapter_id": "1"},
        {"num": 2, "title": "第2章", "url": "https://twkan.com/2", "chapter_id": "2"},
    ]

    hook_calls = []

    def mock_hook(chap, exc):
        hook_calls.append((chap["num"], exc))

    with patch("src.crawler.CHAPTERS_DIR", tmp_path):
        with patch("src.crawler.download_chapter") as mock_download:
            mock_download.side_effect = [tmp_path / "00001_1.json", RuntimeError("失敗")]
            download_all_chapters(catalog, max_workers=2, progress_hook=mock_hook)

    assert len(hook_calls) == 2
    hook_calls.sort(key=lambda x: x[0])
    assert hook_calls[0] == (1, None)
    assert hook_calls[1][0] == 2
    assert isinstance(hook_calls[1][1], RuntimeError)
