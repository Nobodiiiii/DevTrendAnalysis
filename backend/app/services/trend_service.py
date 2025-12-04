# app/services/trend_service.py
from __future__ import annotations

from typing import Dict, List

import sqlite3

from ..models.trend import ItemTrend, YearPoint

# 维度到汇总表名的映射
DIMENSION_TABLES: Dict[str, str] = {
    "language": "language_usage_trend",
    "database": "database_usage_trend",
    "platform": "platform_usage_trend",
    "webframe": "webframe_usage_trend",
    "misctech": "misctech_usage_trend",
    "toolstech": "toolstech_usage_trend",
    "collabtools": "collabtools_usage_trend",
}


def validate_dimension(dimension: str) -> str:
    dim = dimension.lower()
    if dim not in DIMENSION_TABLES:
        raise ValueError(
            f"Invalid dimension: {dim}. "
            f"Must be one of {list(DIMENSION_TABLES.keys())}"
        )
    return dim


def get_top_items_for_dimension(
    conn: sqlite3.Connection,
    table_name: str,
    limit: int,
) -> List[str]:
    """
    若前端没有指定 items，则：
    取该维度最近一年 have_count 排名前 limit 的 item 作为默认展示对象。
    """
    cur = conn.cursor()

    # 最近年份
    cur.execute(f"SELECT MAX(year) AS max_year FROM {table_name}")
    row = cur.fetchone()
    if not row or row["max_year"] is None:
        return []

    last_year = row["max_year"]

    # 按最近一年 have_count 排序
    cur.execute(
        f"""
        SELECT item
        FROM {table_name}
        WHERE year = ?
        ORDER BY have_count DESC
        LIMIT ?
        """,
        (last_year, limit),
    )
    return [r["item"] for r in cur.fetchall()]


def get_trends_for_items(
    conn: sqlite3.Connection,
    table_name: str,
    items: List[str],
) -> List[ItemTrend]:
    """
    针对给定的 item 列表，从汇总表中取出各年数据，并计算 have_ratio / want_ratio。
    """
    if not items:
        return []

    placeholders = ",".join("?" for _ in items)
    sql = f"""
        SELECT year, item, have_count, want_count, base_count
        FROM {table_name}
        WHERE item IN ({placeholders})
        ORDER BY item ASC, year ASC
    """
    cur = conn.cursor()
    cur.execute(sql, items)

    data_by_item: Dict[str, List[YearPoint]] = {}

    for row in cur.fetchall():
        year = row["year"]
        item = row["item"]
        have_count = row["have_count"]
        want_count = row["want_count"]
        base_count = row["base_count"]

        if base_count and base_count > 0:
            have_ratio = have_count / base_count
            want_ratio = want_count / base_count
        else:
            have_ratio = 0.0
            want_ratio = 0.0

        point = YearPoint(
            year=year,
            have_ratio=have_ratio,
            want_ratio=want_ratio,
            have_count=have_count,
            want_count=want_count,
            base_count=base_count,
        )
        data_by_item.setdefault(item, []).append(point)

    trends: List[ItemTrend] = []
    for item_name, points in data_by_item.items():
        trends.append(ItemTrend(item=item_name, points=points))

    return trends
