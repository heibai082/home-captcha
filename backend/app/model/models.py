from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean
from typing import Optional

Base = declarative_base()

class GlobalConfig(Base):
    __tablename__ = "global_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    global_proxy: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class EmailAccount(Base):
    __tablename__ = "email_accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    imap_server: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    proxy_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class SystemLog(Base):
    """全局操作与故障拦截审计归档表"""
    __tablename__ = "system_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
