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
