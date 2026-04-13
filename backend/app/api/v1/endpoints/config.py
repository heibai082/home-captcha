from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.model.models import GlobalConfig, EmailAccount, SystemLog
import asyncio
from app.service.imap_service import test_imap_connection_and_fetch_latest

router = APIRouter()

# Schema 定义前端发过来的请求包单体
class WebhookUpdate(BaseModel):
    target_url: Optional[str]
    global_proxy: Optional[str]

class EmailAccountCreate(BaseModel):
    email: str
    password: str
    imap_server: str
    imap_port: int = 993
    proxy_url: Optional[str] = ""
    is_active: bool = True

class EmailAccountOut(EmailAccountCreate):
    id: int

@router.get("/global")
async def get_global_config(db: AsyncSession = Depends(get_db)):
    """获取所有配置。如果第一次打开（即数据库为空），向库里自动注入占位数据防错"""
    result = await db.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
    glob = result.scalar_one_or_none()
    if not glob:
        glob = GlobalConfig(id=1, webhook_url="", global_proxy="")
        db.add(glob)
        await db.commit()
    return {"target_url": glob.webhook_url, "global_proxy": glob.global_proxy}

@router.post("/global")
async def update_global_config(data: WebhookUpdate, db: AsyncSession = Depends(get_db)):
    """前端点「保存配置」时发往该接口进行存储"""
    result = await db.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
    glob = result.scalar_one_or_none()
    if not glob:
        glob = GlobalConfig(id=1)
        db.add(glob)
    glob.webhook_url = data.target_url
    glob.global_proxy = data.global_proxy
    await db.commit()
    return {"status": "success", "msg": "基础配置已成功应用!"}

@router.post("/global/test")
async def test_global_webhook(db: AsyncSession = Depends(get_db)):
    """点击前端全局测试按钮时，扔条假数据去触发日志"""
    glob_query = await db.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
    glob = glob_query.scalar_one_or_none()
    
    if not glob or not glob.webhook_url:
        return {"status": "error", "msg": "老哥，您连推流神址都没填就点测试啦？"}
         
    from app.service.dispatcher_service import dispatch_webhook
    # 发送虚拟的模拟验证测试
    await dispatch_webhook("🛜 系统内网自测", "收到这条说明您的 Webhook 推送轨道无比畅通！\n恭喜入坑 V2.0 版 Home Captcha 😊", "TEST-8888")
    return {"status": "success", "msg": "一发入魂！虚拟探针已经发往 Webhook，如果不通请立刻查看下方的系统黑屏日志！"}

@router.get("/logs")
async def get_system_logs(db: AsyncSession = Depends(get_db)):
    """前端轮询提取过去生成的日志数据（按倒序排返回一百条）"""
    result = await db.execute(select(SystemLog).order_by(SystemLog.id.desc()).limit(100))
    logs = result.scalars().all()
    # Pydantic直接抛回给前端
    return logs

@router.get("/emails", response_model=List[EmailAccountOut])
async def list_emails(db: AsyncSession = Depends(get_db)):
    """获取当前已配置监听的所有邮箱"""
    result = await db.execute(select(EmailAccount))
    return result.scalars().all()

@router.post("/emails")
async def add_email(acc: EmailAccountCreate, db: AsyncSession = Depends(get_db)):
    """添加监控邮箱"""
    # TODO: 暂时不处理重复邮件地址异常捕获，后期可加强。
    new_acc = EmailAccount(**acc.model_dump())
    db.add(new_acc)
    await db.commit()
    return {"status": "success", "msg": f"邮箱 {acc.email} 已加入监控队列。"}

@router.delete("/emails/{email_id}")
async def delete_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == email_id))
    acc = result.scalar_one_or_none()
    if acc:
        await db.delete(acc)
        await db.commit()
    return {"status": "deleted"}

@router.put("/emails/{email_id}")
async def update_email(email_id: int, acc_update: EmailAccountCreate, db: AsyncSession = Depends(get_db)):
    """依据前端新覆盖的数据改写原本的旧邮箱条目配置"""
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == email_id))
    db_acc = result.scalar_one_or_none()
    if db_acc:
        db_acc.email = acc_update.email
        db_acc.password = acc_update.password
        db_acc.imap_server = acc_update.imap_server
        db_acc.imap_port = acc_update.imap_port
        db_acc.proxy_url = acc_update.proxy_url
        await db.commit()
    return {"status": "success"}

@router.get("/emails/{email_id}/test")
async def test_email_connection(email_id: int, db: AsyncSession = Depends(get_db)):
    """测试邮箱连接并抓取最新的验证码邮件"""
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == email_id))
    acc = result.scalar_one_or_none()
    if not acc:
        return {"status": "error", "msg": "找不到该账号配置。"}
        
    # 获取全局代理用于 fallback
    glob_query = await db.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
    glob = glob_query.scalar_one_or_none()
    global_proxy = glob.global_proxy if glob else None
    
    proxy_str = acc.proxy_url if acc.proxy_url else global_proxy
    
    # 把网络探测由于是阻塞式的丢进线程里执行
    res = await asyncio.to_thread(
        test_imap_connection_and_fetch_latest,
        acc.email, 
        acc.password, 
        acc.imap_server, 
        acc.imap_port, 
        proxy_str
    )
    return res
