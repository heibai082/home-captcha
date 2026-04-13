import asyncio
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.v1.endpoints import sms, config
from app.service.imap_service import poll_emails_background
from app.db.session import init_db

# FastAPI 生命周期管控，用于伴随系统拉起邮箱监听任务及初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 强制尝试建一遍 SQLite 表，无感建库
    await init_db()
    
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
# 比如此处接收手机短信息的接口就是 /api/v1/sms/receive
app.include_router(sms.router, prefix="/api/v1/sms", tags=["SMS Receive"])

# 此处是前端面板用来拉取和操作数据库配置的接口
app.include_router(config.router, prefix="/api/v1/config", tags=["API config"])

@app.get("/health")
async def check_health():
    """最基本的健康检查"""
    return {"status": "ok", "service": "Home Captcha is running."}

# ================================
# 以下为前端 React 网页的“寄生”挂载代码
# ================================
STATIC_DIR = os.path.join(os.path.dirname(__file__), "../static")
os.makedirs(os.path.join(STATIC_DIR, "assets"), exist_ok=True)

# 强制保障目录下有个兜底的 html 防止第一下没放好前端包报错
if not os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    with open(os.path.join(STATIC_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html><body><h2>Frontend is building... please wait.</h2></body></html>")

app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """这属于单页应用(SPA)的基操：不管您在这套本地网址后输入什么，统统丢给 React 的 index.html 处理路由"""
    # 过滤掉真实的纯 API 请求，避免其被劫持给网页
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API Not Found")
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
