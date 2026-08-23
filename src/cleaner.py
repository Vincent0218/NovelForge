"""章節內文清洗器模組。

負責解析小說章節的 HTML 原始碼，移除廣告、腳本與特定域名浮水印（包含 Unicode 混淆與變形字體），
並將內文整理為標準縮排的純文字段落。
"""

import re
import unicodedata
from bs4 import BeautifulSoup

# 廣告關鍵字黑名單（比對 Unicode 正規化後的小寫字串）
AD_KEYWORD_PATTERNS = [
    r"twkan",
    r"69shu",
    r"69書吧",
    r"台灣小說網",
    r"臺灣小説網",
    r"臺灣小說網",
    r"google搜索twkan",
    r"無錯章節",
    r"無亂序章節",
    r"章節更新",
]

# 廣告句型與宣傳語樣式正則
AD_SENTENCE_PATTERNS = [
    r"【.*?(?:域名|台灣|臺灣|本站|首發|超|記住|寫到|等你|任你|全網|小說網).*?】",
    r"[（\(].*?(?:請記住|記住|臺灣|台灣|觀看最快|章節更新|超方便|超實用|等你讀|任你選|隨時看|超貼心|超順暢|超給力|隨時享|超靠譜).*?[）\)]",
    r"本書(?:首發|由).*?(?:全網首發|無錯章節|閱讀體驗|超|任你|隨時|提供給你)",
    r"記住(?:首發|本站|網站)?域名.*",
    r"^(?:讀|找|追|看|伴)?(?:台灣|臺灣)(?:小說|好書)?.*?(?:超|任你|隨時|首選|神器|輕鬆讀|認準).*",
    r"^書庫(?:全|廣).*?(?:超|任你|隨時|選).*",
    r"^海量台灣小說.*",
    r"^藏書(?:全|廣).*",
]

# 段落末尾孤立特殊符號浮水印
TRAILING_WATERMARK_PATTERN = re.compile(r"[\s\u3000]*[🄲🄳🅂🅃🅄🅅🅆🅇🅈🅉\u24b6-\u24e9]+[\s\u3000]*$")


def normalize_text_for_ad_check(text: str) -> str:
    """將文字進行 Unicode NFKD 正規化並去除組合變音符號，以便比對混淆字元。"""
    norm = unicodedata.normalize("NFKD", text)
    # 移除 Combining Diacritical Marks 等附加符號
    norm = re.sub(r"[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]", "", norm)
    return norm


def is_ad_line(line: str) -> bool:
    """判斷該行段落是否為網站廣告或防盜導流浮水印。"""
    s = line.strip()
    if not s:
        return False

    norm = normalize_text_for_ad_check(s).lower()

    # 1. 檢查關鍵字命中
    for kw in AD_KEYWORD_PATTERNS:
        if re.search(kw, norm):
            return True

    # 2. 檢查廣告句型命中
    for pat in AD_SENTENCE_PATTERNS:
        if re.search(pat, s) or re.search(pat, norm):
            return True

    return False


def clean_text_lines(raw_text: str) -> str:
    """清洗純文字內容（段落行），移除廣告與整理縮排。"""
    lines = []
    for line in raw_text.splitlines():
        line = line.replace("\u2003", "").replace("&emsp;", "").strip()
        if not line:
            continue
        # 過濾廣告行
        if is_ad_line(line):
            continue
        # 移除行尾孤立浮水印符號
        line = TRAILING_WATERMARK_PATTERN.sub("", line)
        if line:
            lines.append("　　" + line)

    return "\n\n".join(lines)


def clean_chapter_content(html_str: str) -> str:
    """清洗小說章節 HTML 內容並回傳排版後的段落文字。

    Args:
        html_str: 章節 HTML 原始字串。

    Returns:
        整理完成的純文字內容，每段開頭縮排且以雙換行分隔。
    """
    soup = BeautifulSoup(html_str, "html.parser")
    content_div = soup.find("div", id="txtcontent0")
    if not content_div:
        # 若找不到特定容器，則 fallback 至整個 soup
        content_div = soup

    # 移除廣告容器與腳本標籤
    for unwanted in content_div.find_all(["script", "div"], class_=["txtad", "txtcenter"]):
        unwanted.decompose()
    for tag in content_div.find_all("script"):
        tag.decompose()

    # 將 <br> 標籤替換為換行符號
    for br in content_div.find_all("br"):
        br.replace_with("\n")

    raw_text = content_div.get_text()
    return clean_text_lines(raw_text)

