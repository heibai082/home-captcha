import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.model.models import Base

# 当在 NAS 运行且使用 Docker 时，映射目录默认为 ./data
DB_DIR = "./data"
# 如果目录不存在，自动创建（无论是 Windows 本地还是容器内部）
os.makedirs(DB_DIR, exist_ok=True)

# 采用纯异步的 aiosqlite 以保持 FastAPI 并发性能
DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

async def init_db():
    """首次运行时自动初始化创建 SQLite 数据库及其数据表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """配合 FastAPI 依赖注入，用于获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
