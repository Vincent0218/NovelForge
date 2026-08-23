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


def test_clean_chapter_content_unicode_confusion_ads():
    """測試過濾各類 Unicode 混淆與句型變化的廣告段落。"""
    raw_html = """
    <div id="txtcontent0">
        　　聞言，宋藏鋒馬上拱手，壯著膽子說道「高人，要是有機會的話……」<br><br>
        本書首發 超順暢，🅣🅦🅚🅐🅝.🅒🅞🅜隨時看 ,提供給你無錯章節，無亂序章節的閱讀體驗<br><br>
        　　聽見這話，寧塵沒有回應他。<br><br>
        GOOGLE搜索TWKAN<br><br>
        （請記住 超便捷，₮₩₭₳₦.₵Ø₥隨時享 網站，觀看最快的章節更新）<br><br>
        記住首發網站域名𝕥𝕨𝕜𝕒𝕟.𝕔𝕠𝕞<br><br>
        　　男子只覺自己渾身仿佛被一股無形力量完全束縛，動彈不得。6⃣9⃣🆂🅷🆄🆇.🅲🅾🅼<br><br>
        　　寧塵回身看向穆冰竹「穆小姐，你自己下山去吧。」 .🅆.<br><br>
        　　片刻之後，寧塵從龐青雲口中得知了關於天門的信息。 🄲
    </div>
    """
    cleaned = clean_chapter_content(raw_html)
    assert "聞言，宋藏鋒馬上拱手" in cleaned
    assert "聽見這話，寧塵沒有回應他。" in cleaned
    assert "男子只覺自己渾身仿佛被一股無形力量完全束縛，動彈不得。" in cleaned
    assert "寧塵回身看向穆冰竹「穆小姐，你自己下山去吧。」" in cleaned
    assert "片刻之後，寧塵從龐青雲口中得知了關於天門的信息。" in cleaned
    assert "🅣🅦🅚🅐🅝" not in cleaned
    assert "6⃣9⃣🆂🅷🆄🆇" not in cleaned
    assert "🅲🅾🅼" not in cleaned
    assert ".🅆." not in cleaned
    assert "🅆" not in cleaned
    assert "GOOGLE搜索TWKAN" not in cleaned
    assert "₮₩₭₳₦" not in cleaned
    assert "𝕥𝕨𝕜𝕒𝕟" not in cleaned
    assert "🄲" not in cleaned



def test_strip_leading_title():
    """測試移除正文開頭重複出現的章節標題。"""
    from src.cleaner import strip_leading_title

    sample_content = "　　第2047章 九陰神蝶神車已經遠去，一瞬間不見了蹤影。\n\n　　賀平生差點就癱瘓在地上了。"
    stripped = strip_leading_title(sample_content, title="第2047章 九陰神蝶")
    assert stripped.startswith("　　神車已經遠去")

    sample_content2 = "　　第001章 撿個破盆“你叫賀平生？多大了？”\n\n　　一棟黑暗的狀若破廟。"
    stripped2 = strip_leading_title(sample_content2, title="第001章 撿個破盆")
    assert stripped2.startswith("　　“你叫賀平生？多大了？”")


def test_strip_author_tail_notes():
    """測試移除作者文末留言，並確保絕不誤刪正文劇情與對話。"""
    from src.cleaner import strip_author_tail_notes

    # 1. 正常作者求票與碎碎念（應被移除）
    content1 = "　　牙齒閃爍著冷光，似乎能殺人。\n\n　　求個三發，不求真的沒幾個人給……嗚嗚嗚……"
    cleaned1 = strip_author_tail_notes(content1)
    assert "求個三發" not in cleaned1
    assert "牙齒閃爍著冷光" in cleaned1

    content2 = "　　賀平生第一遍沒有看太懂，又看了幾遍。\n\n　　發炎消了差不多了，明日繼續三更。"
    cleaned2 = strip_author_tail_notes(content2)
    assert "發炎消了差不多了" not in cleaned2
    assert "賀平生第一遍沒有看太懂" in cleaned2

    # 2. 正文角色對話台詞（絕對不能誤刪）
    dialog_content = "　　賀平生看著遠方。\n\n　　“嗚嗚嗚嗚……”西湖真人痛苦的哭了起來，伏在賀平生腿上的身子，一抖一抖。"
    cleaned_dialog = strip_author_tail_notes(dialog_content)
    assert "“嗚嗚嗚嗚……”西湖真人痛苦的哭了起來" in cleaned_dialog



