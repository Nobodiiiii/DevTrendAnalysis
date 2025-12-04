# backend/app/db/session.py
import sqlite3
from typing import Generator

from ..core.config import settings


def get_db() -> Generator[sqlite3.Connection, None, None]:
    if not settings.DB_PATH.exists():
        raise RuntimeError(f"Database file not found: {settings.DB_PATH}")

    # 加一个 timeout，避免短时间多个连接时立刻报错
    conn = sqlite3.connect(
        settings.DB_PATH,
        timeout=5.0,          # 等待最多 5 秒获得锁
        check_same_thread=False,  # 允许多线程访问（FastAPI 默认多线程）
    )
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()
