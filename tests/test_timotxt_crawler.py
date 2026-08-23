"""提莫書屋爬蟲單元測試。"""

import json
from unittest.mock import MagicMock
from src.timotxt_crawler import (
    parse_timotxt_catalog,
    clean_timotxt_content,
    get_timotxt_chapter_cache_path,
    download_timotxt_chapter,
)


def test_parse_timotxt_catalog():
    html = """
    <ul>
      <li><a href="/0104529116/2.html">第002章 靈米</a></li>
      <li><a href="/0104529116/1.html">第001章 撿個破盆</a></li>
    </ul>
    """
    catalog = parse_timotxt_catalog(html)
    assert len(catalog) == 2
    assert catalog[0]["num"] == 1
    assert catalog[0]["title"] == "第001章 撿個破盆"
    assert catalog[1]["num"] == 2
    assert catalog[1]["title"] == "第002章 靈米"


def test_clean_timotxt_content():
    html = """
    <div class="content">
        <div class="gadBlock narrow"><ins class="clickforceads"></ins><script>init();</script></div>
        <p>第001章 撿個破盆“你뇽賀平눃？多꺶了？”</p>
        <p>一棟黑暗的狀若破廟一般的꺶殿中，赤裸著上半身的漢子看著眼前身高不足꾉尺的少뎃，粗聲粗氣的問道。</p>
        <p>溫馨提示: 網站即將改版, 請大家及時保存書架和閱讀記錄</p>
    </div>
    """
    cleaned = clean_timotxt_content(html)
    assert "你叫賀平生？多大了？" in cleaned
    assert "身高不足五尺的少年" in cleaned
    assert "溫馨提示" not in cleaned
    assert "clickforceads" not in cleaned
    assert "　　" in cleaned


def test_download_timotxt_chapter(tmp_path):
    mock_client = MagicMock()
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.text = '<div class="content"><p>你뇽賀平눃？</p></div>'

    chap_info = {"num": 1, "title": "第1章", "url": "https://www.timotxt.com/0104529116/1.html", "chapter_id": "1"}
    saved = download_timotxt_chapter(mock_client, chap_info, cache_dir=tmp_path)
    assert saved.exists()
    data = json.loads(saved.read_text(encoding="utf-8"))
    assert "你叫賀平生？" in data["content"]
