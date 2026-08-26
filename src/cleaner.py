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

# 行內與行尾特殊浮水印正則（包含 69shux.com、twkan.com 各種變體與 .🅆. 等孤立標記）
INLINE_69SHU_PATTERN = re.compile(
    r"6[\ufe0f\u20e3]*9[\ufe0f\u20e3]*[🆂sS][🅷hH][🆄uU][🆇xX]\.?[🅲cC][🅾oO][🅼mM]?", re.IGNORECASE
)
INLINE_TWKAN_PATTERN = re.compile(
    r"[🅣tT][🅦wW][🅚kK][🅐aA][🅝nN]\.?[🅒cC][🅞oO][🅜mM]?", re.IGNORECASE
)
INLINE_SYMBOL_WATERMARK_PATTERN = re.compile(
    r"[\s\u3000]*[.\u3002]*[🄲🄳🅂🅃🅄🅅🅆🅇🅈🅉\U0001f130-\U0001f18f\U0001d400-\U0001d7ff\u24b6-\u24e9][.\u3002]*[\s\u3000]*"
)


def clean_inline_watermarks(text: str) -> str:
    """清理段落中嵌入的網站域名浮水印（如 6⃣9⃣🆂🅷🆄🆇.🅲🅾🅼）與孤立特殊符號（如 .🅆.）。"""
    text = INLINE_69SHU_PATTERN.sub("", text)
    text = INLINE_TWKAN_PATTERN.sub("", text)
    text = INLINE_SYMBOL_WATERMARK_PATTERN.sub("", text)
    text = text.replace("\u20e3", "").replace("\ufe0f", "")
    return text.strip()


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


# 常見正常句末標點符號
TERMINAL_PUNCTUATIONS = ("。", "！", "？", "…", "”", "」", "』", "；", "—", "~", "～", "”", "’")


def merge_broken_paragraphs(paragraphs: list[str]) -> list[str]:
    """智慧縫合因廣告插入或原始碼換行錯誤而生硬切斷的句子與段落。

    例如：上一段結尾為「還是算」，下一段開頭為「了吧。」，自動縫合為「還是算了吧。」。
    """
    if not paragraphs:
        return paragraphs

    merged: list[str] = []
    for p in paragraphs:
        text = p.strip()
        if not text:
            continue

        clean_text = re.sub(r"^[　\s]+", "", text)
        if not merged:
            merged.append("　　" + clean_text)
            continue

        prev = merged[-1]
        prev_clean = re.sub(r"^[　\s]+", "", prev).rstrip()

        # 情況 1: 下一段只是一個或幾個閉合引號/標點 (例如 '」' 或 '。')
        if re.match(r"^[」”』\.\,\!\?，。！？]+$", clean_text):
            merged[-1] = prev.rstrip() + clean_text
            continue

        # 情況 2: 上一段末尾不是正常句末標點 (例如結尾是中文字、英文字母、逗號等)
        prev_ends_with_terminal = prev_clean.endswith(TERMINAL_PUNCTUATIONS)

        # 情況 3: 下一段開頭直接是閉合引號 (例如 '了吧。」')
        starts_with_close_quote = clean_text.startswith(("」", "”", "』"))

        should_merge = False
        if not prev_ends_with_terminal:
            should_merge = True
        elif starts_with_close_quote:
            should_merge = True

        if should_merge:
            merged[-1] = prev.rstrip() + clean_text
        else:
            merged.append("　　" + clean_text)

    return merged


def normalize_typography(text: str) -> str:
    """繁體中文排版與標點符號標準化。

    功能包含：
    1. 引號直角化與嵌套處理：“...” -> 「...」，內層引號轉為『...』
    2. 省略號規範化：將 ......、....、...、。。。 等標準化為 ……
    3. 破折號規範化：將 -- 或 --- 轉換為 ——
    4. 中文夾雜半形標點修復：修復句中半形逗號、問號、驚嘆號、冒號與分號
    """
    if not text:
        return text

    # 1. 畸形省略號標準化 (......, ...., ..., 。。。, 。。) -> ……
    text = re.sub(r"[.。]{3,}", "……", text)
    text = re.sub(r"…{3,}", "……", text)
    text = re.sub(r"(?<!…)…(?!…)", "……", text)

    # 2. 破折號標準化 (-- 或 ---) -> ——
    text = re.sub(r"-{2,}", "——", text)

    # 3. 中文夾雜半形標點修復
    text = re.sub(r"([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee]),", r"\1，", text)
    text = re.sub(r",([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee])", r"，\1", text)
    text = re.sub(r"([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee])\?", r"\1？", text)
    text = re.sub(r"\?([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee])", r"？\1", text)
    text = re.sub(r"([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee])!", r"\1！", text)
    text = re.sub(r"!([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee])", r"！\1", text)
    text = re.sub(r"([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee]):", r"\1：", text)
    text = re.sub(r"([\u4e00-\u9fa5\u3000-\u303f\uff01-\uffee]);", r"\1；", text)

    # 4. 引號繁體直角化 (“ ” 轉 「 」) 與嵌套引號 (『 』)
    chars = []
    for ch in text:
        if ch in ("“", '"'):
            chars.append("「")
        elif ch in ("”",):
            chars.append("」")
        else:
            chars.append(ch)

    res = "".join(chars)

    stack = 0
    nested_chars = []
    for ch in res:
        if ch == "「":
            if stack == 0:
                nested_chars.append("「")
            else:
                nested_chars.append("『")
            stack += 1
        elif ch == "」":
            stack = max(0, stack - 1)
            if stack == 0:
                nested_chars.append("」")
            else:
                nested_chars.append("』")
        else:
            nested_chars.append(ch)

    return "".join(nested_chars)


# 殘留 HTML 標籤與斷行字樣正則
HTML_BR_CLEANUP_PATTERN = re.compile(r"<\s*br\s*/?\s*>|&lt;\s*br\s*/?\s*&gt;", re.IGNORECASE)
OTHER_HTML_TAG_PATTERN = re.compile(
    r"</?[a-zA-Z0-9]+(?:\s+[^>]*)?>|&lt;/?(?:p|div|span|strong|em|b|i|font)[^&]*&gt;", re.IGNORECASE
)


def clean_text_lines(raw_text: str) -> str:
    """清洗純文字內容（段落行），移除廣告、清理浮水印、過濾殘留 HTML 標籤、標準化排版與智慧縫合異常斷行。"""
    # 1. 先將字面 <br> 與 &lt;br&gt; 轉為換行符號，並移除其他殘留 HTML 標籤
    raw_text = HTML_BR_CLEANUP_PATTERN.sub("\n", raw_text)
    raw_text = OTHER_HTML_TAG_PATTERN.sub("", raw_text)

    raw_paragraphs = []
    for line in raw_text.splitlines():
        line = line.replace("\u2003", "").replace("&emsp;", "").strip()
        if not line:
            continue
        # 過濾整行廣告
        if is_ad_line(line):
            continue
        # 清理行內/行尾嵌入之浮水印符號
        line = clean_inline_watermarks(line)
        # 排版與標點標準化
        line = normalize_typography(line)
        if line:
            raw_paragraphs.append(re.sub(r"^[　\s]+", "", line))

    # 智慧縫合異常斷行
    merged_paragraphs = merge_broken_paragraphs(raw_paragraphs)
    return "\n\n".join(merged_paragraphs)






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


def strip_leading_title(content: str, title: str = "") -> str:
    """去除正文開頭重複的章節標題。

    Args:
        content: 格式化後的章節內容。
        title: 當前章節標題（例如：'第2047章 九陰神蝶'）。

    Returns:
        移除開頭重複標題後的正文。
    """
    lines = content.split("\n\n")
    if not lines:
        return content

    first = lines[0].strip()
    first_clean = re.sub(r"^[　\s]+", "", first)

    if title:
        num_m = re.search(r"\d+", title)
        name_m = re.sub(r"^第\s*\d+\s*章\s*", "", title).strip()
        if num_m:
            num_val = int(num_m.group(0))
            if name_m:
                pat = rf"^第\s*0*{num_val}\s*章\s*{re.escape(name_m)}[\s,，]*"
                first_clean = re.sub(pat, "", first_clean)
            pat_num = rf"^第\s*0*{num_val}\s*章[\s,，]*"
            first_clean = re.sub(pat_num, "", first_clean)

    # 通用剝離正則
    first_clean = re.sub(r"^第\s*\d+\s*章(?:\s+[^\s“\"「\n]{1,20})?[\s,，]*", "", first_clean)
    first_clean = first_clean.strip()

    if first_clean:
        lines[0] = "　　" + first_clean
    else:
        lines = lines[1:]

    return "\n\n".join(lines)


AUTHOR_NOTE_PATTERNS = [
    # 括號公告
    r"^[【\[〔].*(?:更|存稿|請假|打賞|發電|作者|老家|過年|月票).*?[】\]〕]$",
    # 求發電、求打賞、求三發、求好評
    r"(?:求個|求一下|求點)?(?:免費的)?(?:為愛發電|用愛發電|發電|發點|三發|三連|打賞|賞賜|月票|推薦票|五星好評|好評|電電)",
    # 諸位衣食父母 / 臭爹爹們
    r"(?:諸位衣食父母|各位衣食父母|臭爹爹們)",
    # 今日X更 / 爆更 / 加更說明 / 沒存稿
    r"(?:今日|明日|接下來|說好的|答應本月|答應你們的)?\s*(?:[0-9一二三四五六七八九十]+更|爆更|加更)\s*(?:送上|奉上|不易|開始|結束|了|求)",
    r"(?:沒存稿了|暫時三更|調整為\d+更|臨時加一更|作者有話說|繼續三更|繼續\d+更|明日繼續[一二三四五六七八九十\d]+更)",
    r"(?:發炎消了|請假欠的\d+章|新的一年，我想日[二三]更|我是寫仙俠類最苦逼的了)",
]


def is_author_tail_note(paragraph: str) -> bool:
    """判斷段落是否為作者文末求票、請假、加更或作者有話說等非正文留言。

    嚴格安全機制：若段落以對話引號開頭或字數過長，一律視為小說正文，避免誤刪。
    """
    text = paragraph.strip()
    if not text:
        return False
    # 嚴格防誤刪：開頭為對話引號一律不刪
    if text.startswith(("“", "”", "「", "『", '"')):
        return False
    # 長度限制：作者短留言通常小於 180 字
    if len(text) > 180:
        return False

    for pat in AUTHOR_NOTE_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def strip_author_tail_notes(content: str) -> str:
    """移除文章末尾 1~2 段內的作者求票、碎碎念、請假公告等無關文字。"""
    paragraphs = content.split("\n\n")
    if not paragraphs:
        return content

    # 檢查最後 2 段
    while len(paragraphs) > 1 and is_author_tail_note(paragraphs[-1]):
        paragraphs.pop()

    return "\n\n".join(paragraphs)


def renumber_chapter_title(raw_title: str, target_num: int) -> str:
    """將章節標題中的章號數字標準化為目標序號，修復作者打錯或跳號問題。

    範例：
        renumber_chapter_title("第256章 吳開山", 296) -> "第296章 吳開山"
        renumber_chapter_title("第001章 撿個破盆", 1) -> "第001章 撿個破盆"
        renumber_chapter_title("第2716章 風暴將至", 2514) -> "第2514章 風暴將至"
    """
    raw_title = raw_title.strip()
    match = re.search(r"第\s*(\d+)\s*章(?:\s*(.*))?$", raw_title)
    if match:
        orig_digits_str = match.group(1)
        name = (match.group(2) or "").strip()
        # 若原本有 3 位數零填充（如 001），則保持長度填充，否則使用一般整數
        if len(orig_digits_str) == 3:
            num_str = f"{target_num:03d}"
        else:
            num_str = str(target_num)
        return f"第{num_str}章 {name}".strip() if name else f"第{num_str}章"

    return f"第{target_num}章 {raw_title}"




