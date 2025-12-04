# app/models/trend.py
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class YearPoint(BaseModel):
    year: int
    have_ratio: float
    want_ratio: float
    have_count: int
    want_count: int
    base_count: int


class ItemTrend(BaseModel):
    item: str
    points: List[YearPoint]


class TrendResponse(BaseModel):
    dimension: str
    items: List[ItemTrend]
