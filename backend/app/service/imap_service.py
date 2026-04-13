import asyncio
import imaplib
import email
from email.header import decode_header
import socks
import ssl
from app.core.config import settings
from app.service.extractor_service import extract_code
from app.service.dispatcher_service import dispatch_webhook

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
    print("📧 后台邮箱监听服务已启动...")
    while True:
        for account in settings.emails:
            # 使用针对单一账户的单独代理，否则尝试使用全局代理
            proxy_str = account.proxy_url if account.proxy_url else (settings.proxy.url if settings.proxy else None)
            # 因为 IMAP 连接是阻塞式的（非异步），交给事件循环的安全线程执行
            await asyncio.to_thread(check_single_account, account, proxy_str)
            
        await asyncio.sleep(20)  # 每次轮询休息间隔秒数

def check_single_account(account, proxy_str: str):
    try:
        proxy_cfg = parse_proxy(proxy_str)
        
        # 判断如果存在代理则运用带代理的 IMAP 客户端
        if proxy_cfg:
            client = ProxyIMAP4SSL(account.imap_server, account.imap_port, proxy_cfg[0], proxy_cfg[1], proxy_cfg[2])
        else:
            client = imaplib.IMAP4_SSL(account.imap_server, account.imap_port)
            
        client.login(account.email, account.password)
        client.select('INBOX')
        
        # 搜索 UNSEEN 状态即 "未读" 邮件
        status, response = client.search(None, 'UNSEEN')
        if status != 'OK':
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
                # 只有找得出验证码才发送（因为同步上下文中没办法直接 await dispatch_webhook，这里使用事件循环抛出）
                subject = get_header(msg_obj, "Subject")
                loop = asyncio.get_event_loop()
                loop.create_task(dispatch_webhook(f"📧邮箱 ({account.email}) -> {subject}", content, code))
                
                # 收下这封邮件并标记为已读了，避免重复。你可以在测试期间注掉这行
                client.store(num, '+FLAGS', '\\Seen')
        
        client.logout()
    except Exception as e:
        print(f"[{account.email}] IMAP 巡检出错或超时（如果在群晖/NAS 连谷歌超时请检查您的代理）: {e}")

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
