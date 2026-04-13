import sqlite3
import os
from datetime import datetime
import logging

# 使用系统高亮包接管原有的 print，避免黑盒，符合《代码约束协议》
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("home_captcha")

# NOTE: 获取与主应用同一个真实的数据库目录。
# 修正路径计算：__file__ 在 /app/app/service 下，向上两层即为 /app/app，再拼 ../data 则为 /app/data/app.db 刚好落在持久化卷里！
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/app.db"))

def record_log(level: str, source: str, message: str):
    """
    兼具 Python 原生 Logging 与 SQLite 永久落盘的一体化方法。
    HACK: 为保证所有协程和多线程能在任何状况下即时反馈抛错而不受引擎阻塞影响，直接用微小原生驱动同步写入。
    """
    logger_method = logger.error if level == "ERROR" else (logger.warning if level == "WARNING" else logger.info)
    logger_method(f"[{source}] {message}")
    
    try:
        # 为了防错（比如在最开始建库之前被调用），如果捕捉任意抛出则直接放弃落盘记录
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO system_logs (level, source, message, created_at) VALUES (?, ?, ?, ?)",
                       (level, source, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception:
        pass
