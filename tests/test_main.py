"""CLI 主程式入口整合測試。"""
from unittest.mock import MagicMock, patch
import pytest


def test_main_flow(tmp_path):
    """測試 main 主流程，驗證目錄獲取、下載、TXT 與 EPUB 生成皆有被呼叫。"""
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


def test_main_progress_hook(tmp_path):
    """測試 download_all_chapters 的 progress_hook 在正常與錯誤狀態下的行為。"""
    from src.main import main

    fake_catalog = [
        {"num": 1, "title": "第1章 測試", "url": "https://twkan.com/txt/20/1", "chapter_id": "1"},
        {"num": 2, "title": "第2章 失敗", "url": "https://twkan.com/txt/20/2", "chapter_id": "2"},
    ]

    def fake_download_all(catalog, max_workers, progress_hook):
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
