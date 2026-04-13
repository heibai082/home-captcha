import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1.endpoints import sms
from app.service.imap_service import poll_emails_background

# FastAPI 生命周期管控，用于伴随系统拉起邮箱监听任务
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 服务启动时开始运转 IMAP 获取。将其丢在后台 Event Loop 并发执行。
    imap_task = asyncio.create_task(poll_emails_background())
    yield
    # 接收到停止信号，取消该后台循环
    imap_task.cancel()

app = FastAPI(
    title="宅家验证码 (Home Captcha)",
    description="自动收集多个来源终端（短信/邮箱）发送过来的验证码，然后分发给指定 Webhook 窗口。",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载路由模块
# 比如此处的 url 将变成 /api/v1/sms/receive
app.include_router(sms.router, prefix="/api/v1/sms", tags=["SMS Receive"])

@app.get("/health")
async def check_health():
    """最基本的健康检查"""
    return {"status": "ok", "service": "Home Captcha is running."}
