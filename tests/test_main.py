"""CLI 主程式入口整合測試。"""
from unittest.mock import MagicMock, patch
import pytest


def test_main_flow(tmp_path):
    """測試 main 預設流程（我都元嬰期了，你跟我說開學？），驗證目錄獲取、下載、TXT 與 EPUB 生成皆有被呼叫。"""
    from src.main import main

    fake_catalog = [
        {"num": 1, "title": "第1章 測試", "url": "https://twkan.com/txt/20/1", "chapter_id": "1"}
    ]
    
    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with patch("src.main.fetch_catalog", return_value=fake_catalog) as mock_catalog, \
         patch("src.main.download_all_chapters") as mock_download, \
         patch("src.main.get_chapter_cache_path", return_value=mock_path), \
         patch("src.main.build_txt") as mock_txt, \
         patch("src.main.build_epub") as mock_epub, \
         patch("src.main.OUTPUT_DIR", tmp_path):
        
        main([])
        
        mock_catalog.assert_called_once()
        mock_download.assert_called_once()
        mock_txt.assert_called_once()
        mock_epub.assert_called_once()


def test_main_list_option(capsys):
    """測試 --list 參數能列印支援的小說清單。"""
    from src.main import main

    main(["--list"])
    captured = capsys.readouterr()
    assert "我都元嬰期了，你跟我說開學？" in captured.out
    assert "聚寶仙盆" in captured.out
    assert "twkan" in captured.out
    assert "timotxt" in captured.out


def test_main_timotxt_routing(tmp_path):
    """測試 --book 0104529116 能正確路由至 timotxt 爬蟲。"""
    from src.main import main

    fake_catalog = [
        {"num": 1, "title": "第1章 撿個破盆", "url": "https://www.timotxt.com/0104529116/1.html", "chapter_id": "1"}
    ]
    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with patch("src.main.fetch_timotxt_catalog", return_value=fake_catalog) as mock_timotxt_cat, \
         patch("src.main.download_all_timotxt_chapters") as mock_timotxt_dl, \
         patch("src.main.get_timotxt_chapter_cache_path", return_value=mock_path), \
         patch("src.main.build_txt") as mock_txt, \
         patch("src.main.build_epub") as mock_epub, \
         patch("src.main.OUTPUT_DIR", tmp_path):

        main(["--book", "0104529116"])

        mock_timotxt_cat.assert_called_once()
        mock_timotxt_dl.assert_called_once()
        mock_txt.assert_called_once()
        mock_epub.assert_called_once()


def test_download_timotxt_wrapper(tmp_path):
    """測試 src.download_timotxt 腳本能否正常轉發至 main。"""
    from src.download_timotxt import main as timotxt_main

    fake_catalog = [
        {"num": 1, "title": "第1章 撿個破盆", "url": "https://www.timotxt.com/0104529116/1.html", "chapter_id": "1"}
    ]
    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with patch("src.main.fetch_timotxt_catalog", return_value=fake_catalog) as mock_timotxt_cat, \
         patch("src.main.download_all_timotxt_chapters") as mock_timotxt_dl, \
         patch("src.main.get_timotxt_chapter_cache_path", return_value=mock_path), \
         patch("src.main.build_txt"), \
         patch("src.main.build_epub"), \
         patch("src.main.OUTPUT_DIR", tmp_path):

        timotxt_main([])

        mock_timotxt_cat.assert_called_once()
        mock_timotxt_dl.assert_called_once()


def test_main_progress_hook(tmp_path):
    """測試 download_all_chapters 的 progress_hook 在正常與錯誤狀態下的行為。"""
    from src.main import main

    fake_catalog = [
        {"num": 1, "title": "第1章 測試", "url": "https://twkan.com/txt/20/1", "chapter_id": "1"},
        {"num": 2, "title": "第2章 失敗", "url": "https://twkan.com/txt/20/2", "chapter_id": "2"},
    ]

    def fake_download_all(catalog, max_workers, progress_hook, cache_dir=None):
        # 模擬呼叫 hook
        if progress_hook:
            progress_hook(catalog[0], None)
            progress_hook(catalog[1], Exception("下載失敗模擬"))

    mock_path = MagicMock()
    mock_path.exists.return_value = False

    with patch("src.main.fetch_catalog", return_value=fake_catalog), \
         patch("src.main.download_all_chapters", side_effect=fake_download_all), \
         patch("src.main.get_chapter_cache_path", return_value=mock_path), \
         patch("src.main.build_txt"), \
         patch("src.main.build_epub"), \
         patch("src.main.tqdm") as mock_tqdm_module, \
         patch("src.main.time.sleep", return_value=None), \
         patch("src.main.OUTPUT_DIR", tmp_path):
        
        mock_pbar = MagicMock()
        mock_tqdm_module.return_value.__enter__.return_value = mock_pbar
        
        with pytest.raises(RuntimeError, match="尚有"):
            main([])
        
        # 驗證 tqdm.write 有記錄錯誤
        assert mock_tqdm_module.write.called
        assert any("下載失敗模擬" in str(call) for call in mock_tqdm_module.write.call_args_list)
