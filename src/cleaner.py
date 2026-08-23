"""章節內文清洗器模組。

負責解析小說章節的 HTML 原始碼，移除廣告、腳本與特定域名浮水印，
並將內文整理為標準縮排的純文字段落。
"""

import re
from bs4 import BeautifulSoup

# 常見浮水印與廣告正則規則
WATERMARK_PATTERNS = [
    r"【寫到這裡我希望讀者記一下我們域名.*?】",
    r"\(https?://[^\s)]+\)",
    r"twkan\.com",
    r"𝑡𝑤𝑘𝑎𝑛\.𝑐𝑜𝑚",
    r"台灣小說網",
]


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

    text = content_div.get_text()

    # 清理浮水印文字
    for pattern in WATERMARK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 清理多餘空白行與全形空白整理
    lines = []
    for line in text.splitlines():
        line = line.replace("\u2003", "").replace("&emsp;", "").strip()
        if line:
            lines.append("　　" + line)

    return "\n\n".join(lines)
