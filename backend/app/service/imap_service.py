import asyncio
import imaplib
import email
from email.header import decode_header
import socks
import ssl
from app.service.extractor_service import extract_code
from app.service.dispatcher_service import dispatch_webhook
from app.db.session import AsyncSessionLocal
from app.model.models import EmailAccount, GlobalConfig
from sqlalchemy import select
from app.service.log_service import record_log

# 重写标准库原生的 IMAP4_SSL ，使其内部创建的 socket 连接走独立代理，而不污染全局
class ProxyIMAP4SSL(imaplib.IMAP4_SSL):
    def __init__(self, host, port, proxy_type, proxy_addr, proxy_port, **kwargs):
        self._proxy_type = proxy_type
        self._proxy_addr = proxy_addr
        self._proxy_port = proxy_port
        super().__init__(host, port, **kwargs)

    def _create_socket(self, timeout=None):
        sock = socks.socksocket()
        # 让只属于当前连接的 socket 使用指定代理
        sock.set_proxy(self._proxy_type, self._proxy_addr, self._proxy_port)
        sock.settimeout(self.sock_timeout if hasattr(self, 'sock_timeout') else timeout)
        sock.connect((self.host, self.port))
        return sock

def parse_proxy(proxy_url: str):
    """分析配置好的代理字符串转换为底层协议参数 (如 socks5://IP:port 或 http://)"""
    if not proxy_url:
        return None
    try:
        scheme, rest = proxy_url.split("://", 1)
        host, port = rest.split(":", 1)
        port = int(port)
        scheme = scheme.lower()
        if scheme in ("socks5", "socks5h"):
             return (socks.SOCKS5, host, port)
        elif scheme in ("socks4", "socks4a"):
             return (socks.SOCKS4, host, port)
        elif scheme in ("http", "https"):
             return (socks.HTTP, host, port)
    except Exception as e:
        print(f"代理配置格式错误 {proxy_url}，将尝试直连。")
    return None

async def poll_emails_background():
    """在后台不间断运转的任务：轮询检查配置的所有邮箱有没有新邮件"""
    record_log("INFO", "守护中心", "📧 后台轮询主线引擎已启动，时刻帮您蹲点")
    while True:
        try:
            # 每次循环都开启一个独立且短暂的查询以确保读取的是网页上的最新配置
            async with AsyncSessionLocal() as session:
                glob_query = await session.execute(select(GlobalConfig).where(GlobalConfig.id == 1))
                glob = glob_query.scalar_one_or_none()
                global_proxy = glob.global_proxy if glob else None

                # 获取给新线程回送用的强引用主循环
                main_loop = asyncio.get_running_loop()

                # 仅查询启用的邮箱
                accounts_query = await session.execute(select(EmailAccount).where(EmailAccount.is_active == True))
                accounts = accounts_query.scalars().all()

                for account in accounts:
                    # 单一账户特定代理优先于全局代理
                    proxy_str = account.proxy_url if account.proxy_url else global_proxy
                    
                    # 将主界面的大循环丢进独立的工作线程以防止任何形式的 IO 假死
                    await asyncio.to_thread(check_single_account, main_loop, account.email, account.password, account.imap_server, account.imap_port, proxy_str)
        except Exception as e:
            record_log("WARNING", "DB 同步", f"后台循环探测引擎读取配置受阻: {e}")
            
        await asyncio.sleep(20)  # 每次轮询休息间隔秒数

def check_single_account(main_loop, email_addr: str, password: str, imap_server: str, imap_port: int, proxy_str: str):
    try:
        proxy_cfg = parse_proxy(proxy_str)
        
        # 判断如果存在代理则运用带代理的 IMAP 客户端
        if proxy_cfg:
            client = ProxyIMAP4SSL(imap_server, imap_port, proxy_cfg[0], proxy_cfg[1], proxy_cfg[2])
        else:
            client = imaplib.IMAP4_SSL(imap_server, imap_port)
            
        client.login(email_addr, password)
        client.select('INBOX')
        
        # 搜索 UNSEEN 状态即 "未读" 邮件
        status, response = client.search(None, 'UNSEEN')
        if status != 'OK':
            client.logout()
            return
            
        unread_msg_nums = response[0].split()
        for num in unread_msg_nums:
            res, data = client.fetch(num, '(RFC822)')
            if res != 'OK':
                continue
                
            raw_email = data[0][1]
            msg_obj = email.message_from_bytes(raw_email)
            
            content = extract_email_text(msg_obj)
            code = extract_code(content)
            
            if code:
                # 只有找得出验证码才发送（由于我们剥离在独立的背景线程中，所以只能强切回主线程投递 Webhook）
                subject = get_header(msg_obj, "Subject")
                asyncio.run_coroutine_threadsafe(
                    dispatch_webhook(f"📧邮箱 ({email_addr}) -> {subject}", content, code), 
                    main_loop
                )
                
                # 收下这封邮件并标记为已读了，避免重复
                client.store(num, '+FLAGS', '\\Seen')
        
        client.logout()
    except Exception as e:
        record_log("ERROR", "收信链路", f"[{email_addr}] 握手或解包彻底失败（网络不通/代理死链接）: {e}")

def extract_email_text(msg) -> str:
    """提取纯文本或将 HTML 里的文字抽出来"""
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            # 跳过附件
            if part.get('Content-Disposition') and 'attachment' in str(part.get('Content-Disposition')):
                continue
            if ctype == 'text/plain':
                try:
                    content += part.get_payload(decode=True).decode()
                except:
                    pass
    else:
        try:
            content += msg.get_payload(decode=True).decode()
        except:
            pass
    return content

def get_header(msg, header_name):
    """防止读取出来的标题带有很多乱码字符等"""
    value = msg.get(header_name, "")
    if not value: return ""
    
    decoded = decode_header(value)
    text_content = ""
    for string_byte, charset in decoded:
        if isinstance(string_byte, bytes):
            text_content += string_byte.decode(charset or 'utf-8', errors="ignore")
        else:
             text_content += string_byte
    return text_content

def test_imap_connection_and_fetch_latest(email_addr: str, password: str, imap_server: str, imap_port: int, proxy_str: str):
    """
    用于前台手动测试特定邮箱的连通性并尝试找出最近的一条验证码邮件
    """
    try:
        proxy_cfg = parse_proxy(proxy_str)
        if proxy_cfg:
            client = ProxyIMAP4SSL(imap_server, imap_port, proxy_cfg[0], proxy_cfg[1], proxy_cfg[2])
        else:
            client = imaplib.IMAP4_SSL(imap_server, imap_port)
            
        client.login(email_addr, password)
        client.select('INBOX')
        
        # 获取所有的邮件ID，不用限定未读的
        status, response = client.search(None, 'ALL')
        if status != 'OK':
            client.logout()
            return {"status": "success", "msg": "连接成功，但您邮箱里没有任何邮件。"}
            
        msg_nums = response[0].split()
        # 取倒数 10 封最新邮件进行扫描，减轻负担
        recent_nums = reversed(msg_nums[-10:])
        
        for num in recent_nums:
            res, data = client.fetch(num, '(RFC822)')
            if res != 'OK': continue
                
            raw_email = data[0][1]
            msg_obj = email.message_from_bytes(raw_email)
            
            content = extract_email_text(msg_obj)
            code = extract_code(content)
            
            if code:
                # 找到带有验证码的最近一封
                date_str = get_header(msg_obj, "Date")
                subject = get_header(msg_obj, "Subject")
                client.logout()
                return {
                    "status": "success", 
                    "msg": "网络连通测试完美成功！且成功命中历史验证码。", 
                    "data": {"code": code, "date": date_str, "subject": subject}
                }
        
        client.logout()
        return {"status": "success", "msg": "登入测试成功！但在最新的10封邮件里没有提取出符合规则的验证码。"}
        
    except Exception as e:
        return {"status": "error", "msg": f"连接或提取失败，请检查账号密码、授权码或代理状态哦: {str(e)}"}
