"""章節內文清洗器測試模組。"""

from src.cleaner import clean_chapter_content


def test_clean_chapter_content_removes_ads_and_scripts():
    """測試移除廣告與 script 標籤以及浮水印文字。"""
    raw_html = """
    <div id="txtcontent0">
        &emsp;&emsp;青州市郊外，無名荒山。<br /><br />
        【寫到這裡我希望讀者記一下我們域名 台灣小說網超貼心，𝑡𝑤𝑘𝑎𝑛.𝑐𝑜𝑚超方便 】<br />
        <div class="txtad"><script>loadAdv(10,0);</script></div>
        &emsp;&emsp;「轟隆！」<br />
        突如其來的一聲巨響。
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    assert "青州市郊外，無名荒山。" in cleaned
    assert "「轟隆！」" in cleaned
    assert "突如其來的一聲巨響。" in cleaned
    assert "台灣小說網" not in cleaned
    assert "𝑡𝑤𝑘𝑎𝑛.𝑐𝑜𝑚" not in cleaned
    assert "loadAdv" not in cleaned


def test_clean_chapter_content_paragraph_formatting():
    """測試段落排版格式化，確認每段開頭有全形空白縮排且以雙換行分隔。"""
    raw_html = """
    <div id="txtcontent0">
        第一行內容。<br>
        <br>
        第二行內容。<br/>
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    expected = "　　第一行內容。\n\n　　第二行內容。"
    assert cleaned == expected


def test_clean_chapter_content_fallback_without_txtcontent0():
    """測試當 HTML 沒有 txtcontent0 時，能 fallback 解析整個 HTML 內文。"""
    raw_html = """
    <div>
        <p>沒有特定容器的一般段落。<br>第二句。</p>
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    assert "　　沒有特定容器的一般段落。" in cleaned
    assert "　　第二句。" in cleaned


def test_clean_chapter_content_empty_or_whitespace():
    """測試空 HTML 或僅包含空白/廣告時，回傳空字串。"""
    raw_html = """
    <div id="txtcontent0">
        <div class="txtad"><script>loadAdv(10,0);</script></div>
        &emsp;&emsp;
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    assert cleaned == ""
