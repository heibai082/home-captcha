import httpx
from app.db.session import AsyncSessionLocal
from app.model.models import GlobalConfig
from sqlalchemy import select
from app.service.log_service import record_log

async def dispatch_webhook(source: str, content: str, code: str):
    """
    将分析完的验证码、连同原始文本发送到指定的 Webhook 中
    适用钉钉机器人、企业微信应用机器人等
    """
    async with AsyncSessionLocal() as session:
        glob_query = await session.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
        glob = glob_query.scalar_one_or_none()
        
    if not glob or not glob.webhook_url:
        record_log("WARNING", "Webhook 推流", "成功捕捉到了验证码，但您尚未设置转发地址，数据被抛弃！")
        return
    
    target_url = glob.webhook_url
        
    # 企业微信和钉钉的通用 json 数据格式
    payload = {
        "msgtype": "text",
        "text": {
            "content": f"📨【宅家验证码】\n\n📌来源: {source}\n🔑验证码: {code}\n\n📝原文: {content}"
        }
    }
    
    # 支持网页配置统一代理，最新版 httpx (0.24+) 已经用 proxy='' 替代了原先的映射表
    proxy_url = glob.global_proxy if glob.global_proxy else None
        
    async with httpx.AsyncClient(proxy=proxy_url) as client:
        try:
            response = await client.post(target_url, json=payload, timeout=20.0)
            record_log("INFO", "外发触达", f"🚀 验证码已成功推送至您配置终端！服务器回传: {response.status_code}")
        except Exception as e:
            record_log("ERROR", "推流爆破", f"尝试进行 HTTP 投递时崩溃: {repr(e)}")
