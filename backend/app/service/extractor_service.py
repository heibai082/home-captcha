import re
from typing import Optional

def extract_code(text: str) -> Optional[str]:
    """
    智能化抽取文本中的验证码字符串，绝对免疫 HTML 污染
    """
    if not text:
        return None
        
    # 强制驱逐任何疑似残留的 HTML 标签 (<xxx>) 防止将其内的小写类型名作为验证码提取出
    text_clean = re.sub(r'<[^>]+>', ' ', text)
        
    # 定义验证码常用的上下文关键字进行优先精确匹配
    keywords = ["验证码", "校验码", "动态密码", "安全码", "code", "verificatio", "code is"]
    
    # 规则 1：最高优先级 -> 寻觅关键字附近的纯数字 (4~8位)
    for kw in keywords:
        match = re.search(f"{kw}.*?([0-9]{{4,8}})", text_clean, re.IGNORECASE)
        if match:
            return match.group(1)
            
    # 规则 1 附录：寻找如 123-456 形式 (Google 偏好)
    for kw in keywords:
        match = re.search(f"{kw}.*?([0-9]{{3,4}}-[0-9]{{3,4}})", text_clean, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # 规则 2：寻找字母与数字的混合型组合 (Steam 等偏好)
    for kw in keywords:
        matches = re.findall(f"{kw}.*?([a-zA-Z0-9]{{4,8}})", text_clean, re.IGNORECASE)
        for m in matches:
            if m.islower() and m.isalpha():
                # 如果这个紧跟的 4-8 个字符全都是纯字母且全是小写（如 strong, span, href 等干扰次）直接拦截丢弃
                continue 
            return m.upper()

    # 兜底：不考虑关键字，在整篇纯净文本里随便找一坨落单的 4-8 位数字强行提取
    matches = re.findall(r"\b(\d{4,8})\b", text_clean)
    if matches:
        return matches[0]

    return None
