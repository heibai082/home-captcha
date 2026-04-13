import re
from typing import Optional

def extract_code(text: str) -> Optional[str]:
    """
    智能化抽取文本中的验证码字符串
    """
    if not text:
        return None
        
    # 定义验证码常用的上下文关键字进行优先精确匹配
    keywords = ["验证码", "校验码", "动态密码", "安全码", "code", "verificatio"]
    
    # 启发式规则1：关键词左右 4 到 8 位的数字字母组合
    for kw in keywords:
        # 寻找诸如 ”您的验证码是 123456“ 或 ”Code: 12345“
        match = re.search(f"{kw}.*?([a-zA-Z0-9]{{4,8}})", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
            
        # 寻找诸如 ”123456 是您本次登录的验证码“
        match = re.search(f"([a-zA-Z0-9]{{4,8}}).*?{kw}", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    # 兜底规则：如果没有匹配到关键字，则提取文本中独立的、只有4到8位的纯数字
    # 例如包含破折号等边界：您的验证码为 - 8812 -
    matches = re.findall(r"\b(\d{4,8})\b", text)
    if matches:
        return matches[0]

    return None
