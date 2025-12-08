# app/core/config.py
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List


class Settings:
    """
    项目基础配置：
    - 数据库路径
    - CORS 允许的前端地址
    """

    def __init__(self) -> None:
        # 当前文件位置：root/backend/app/core/config.py
        # app_dir = root/backend/app
        app_dir = Path(__file__).resolve().parent.parent

        # 1) 优先用环境变量指定 DB 路径
        env_db_path = os.getenv("DEVTREND_DB_PATH")
        if env_db_path:
            self.DB_PATH = Path(env_db_path)
        else:
            # 2) 默认：root/data/devtrend.db
            project_root = app_dir.parent.parent  # root
            self.DB_PATH = project_root / "data" / "devtrend.db"

        # CORS 允许的前端域名（按需修改）
        self.BACKEND_CORS_ORIGINS: List[str] = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            # 生产环境加你的域名：
            # "https://xxx.yourdomain.com",
        ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
