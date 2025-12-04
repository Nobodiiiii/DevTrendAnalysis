# app/api/routes/trends.py
from __future__ import annotations

from typing import List, Optional

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from ...models.trend import TrendResponse
from ...services.trend_service import (
    DIMENSION_TABLES,
    get_top_items_for_dimension,
    get_trends_for_items,
    validate_dimension,
)
from ..deps import get_db_dep

router = APIRouter(
    prefix="/trends",
    tags=["trends"],
)


@router.get("/{dimension}", response_model=TrendResponse)
def get_trends(
    dimension: str,
    items: Optional[List[str]] = Query(
        default=None,
        description="要查看的技术名称，如 ?items=Python&items=JavaScript",
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=50,
        description="当未指定 items 时，使用最近一年 have_count 排名前 limit 的 item",
    ),
    conn: sqlite3.Connection = Depends(get_db_dep),
):
    # 1. 校验 dimension
    try:
        dim = validate_dimension(dimension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    table_name = DIMENSION_TABLES[dim]

    # 2. 决定最终要查询的 items 列表
    if items and len(items) > 0:
        target_items = items
    else:
        target_items = get_top_items_for_dimension(conn, table_name, limit)
        if not target_items:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for dimension: {dim}",
            )

    # 3. 查询并计算趋势
    trends = get_trends_for_items(conn, table_name, target_items)
    if not trends:
        raise HTTPException(
            status_code=404,
            detail=f"No trend data found for items: {target_items}",
        )

    return TrendResponse(dimension=dim, items=trends)
