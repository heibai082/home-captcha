import yaml
import os
from pydantic import BaseModel
from typing import List, Optional

class EmailSettings(BaseModel):
    email: str
    password: str
    imap_server: str
    imap_port: int = 993
    proxy_url: Optional[str] = ""

class WebhookSettings(BaseModel):
    target_url: str

class ProxySettings(BaseModel):
    url: Optional[str] = ""

class AppSettings(BaseModel):
    webhook: WebhookSettings
    proxy: Optional[ProxySettings] = None
    emails: List[EmailSettings] = []

def load_config(config_path: str = "config.yaml") -> AppSettings:
    """加载 YAML 配置文件映射到 Pydantic 模型"""
    # 优先查找根目录（容器运行时映射位置），若找不到看是否在上一级
    if not os.path.exists(config_path) and os.path.exists(f"../{config_path}"):
        config_path = f"../{config_path}"
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not data:
                return AppSettings(webhook=WebhookSettings(target_url=""))
            return AppSettings(**data)
    except FileNotFoundError:
        print(f"Warning: Configuration file {config_path} not found. Please create one.")
        return AppSettings(webhook=WebhookSettings(target_url=""))
    except Exception as e:
        print(f"Error parse config: {e}")
        return AppSettings(webhook=WebhookSettings(target_url=""))

# 全局单例配置实例
settings = load_config()
