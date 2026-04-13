from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.model.models import GlobalConfig, EmailAccount

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
