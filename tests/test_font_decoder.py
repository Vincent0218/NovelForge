"""字體解密模組單元測試。"""

from src.font_decoder import TIMOTXT_FONT_MAP, decode_timotxt_text


def test_font_decoder_mapping_count():
    """驗證提莫書屋字體混淆對照表包含完整 149 個字符。"""
    assert len(TIMOTXT_FONT_MAP) == 149


def test_font_decoder_decoding():
    """驗證解密字串中的混淆字元。"""
    raw_sample = "你뇽賀平눃？多꺶了？身高不足꾉尺，今年굛눁歲，놆個꾉行靈根！"
    decoded = decode_timotxt_text(raw_sample)
    assert decoded == "你叫賀平生？多大了？身高不足五尺，今年十四歲，是個五行靈根！"


def test_font_decoder_empty():
    """驗證空字串處理。"""
    assert decode_timotxt_text("") == ""
