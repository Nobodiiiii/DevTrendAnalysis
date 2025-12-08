# app/api/deps.py
from __future__ import annotations

import sqlite3
from typing import Generator

from fastapi import Depends

from ..db.session import get_db


def get_db_dep(
    conn: sqlite3.Connection = Depends(get_db),
) -> Generator[sqlite3.Connection, None, None]:
    """
    作为统一的依赖暴露出去，方便以后扩展。
    现在只是简单转发 get_db。
    """
    return conn
