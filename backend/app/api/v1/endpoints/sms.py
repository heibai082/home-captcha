from fastapi import APIRouter, BackgroundTasks
from app.schema.sms import SmsPayload
from app.service.extractor_service import extract_code
from app.service.dispatcher_service import dispatch_webhook

# 建立短信短信端点路由
router = APIRouter()

@router.post("/receive")
async def receive_sms(payload: SmsPayload, background_tasks: BackgroundTasks):
    """
    开放的短信 Webhook 接收端点。
    适用于使用诸如 SmsForwarder 等应用把验证码推送到这里。
    """
    # 提取内容中的验证码
    code = extract_code(payload.content)
    if code:
        # 成功提取，为了让请求尽快返回不堵塞，放入背景任务调度执行发送
        background_tasks.add_task(
            dispatch_webhook, 
            source=f"📱手机 ({payload.from_number})", 
            content=payload.content, 
            code=code
        )
        return {"code": 0, "msg": "验证码成功提取，正在后台转发中。"}
    
    # 里面没含有验证码，静默忽略
    return {"code": 200, "msg": "原文内没找到有效的验证码组合，忽略推送。"}
