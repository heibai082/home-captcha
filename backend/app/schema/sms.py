from pydantic import BaseModel
from typing import Optional

class SmsPayload(BaseModel):
    """
    用于接收类似「短信转发器(SmsForwarder)」App的请求。
    您可以根据在App内设置的请求模板字段进行调整。
    示例预设了常用的手机和内容字段。
    """
    from_number: str
    content: str
    timestamp: Optional[str] = None
