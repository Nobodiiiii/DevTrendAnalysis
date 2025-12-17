# app/api/routes/salary.py
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from ...models.salary import SalaryOverview, SalaryTimelineResponse
from ...services.salary_service import build_salary_overview, build_salary_timeline
from ..deps import get_db_dep

router = APIRouter(
    prefix="/salary",
    tags=["salary"],
)


@router.get("/overview", response_model=SalaryOverview)
def get_salary_overview(
    year: int
    | None = Query(
        default=None,
        description="Optional survey year to read salary cache from",
        ge=2012,
        le=2025,
    ),
    conn: sqlite3.Connection = Depends(get_db_dep),
) -> SalaryOverview:
    try:
        return build_salary_overview(conn, year=year)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/timeline", response_model=SalaryTimelineResponse)
def get_salary_timeline(
    conn: sqlite3.Connection = Depends(get_db_dep),
) -> SalaryTimelineResponse:
    try:
        return build_salary_timeline(conn)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
