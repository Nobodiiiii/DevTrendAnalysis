# backend/app/services/salary_service.py
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from ..models.salary import (
    ClusterMetricsSummary,
    ClusterMetricsYearly,
    MedianTrendPoint,
    PercentileSummary,
    RoleBenchmark,
    SalaryBucket,
    SalaryCluster,
    SalaryCountry,
    SalaryOverview,
    SalaryTimelineResponse,
    SalaryTrendSeries,
    SatisfactionBand,
)

CACHE_MISSING_MSG = (
    "Cached salary data is missing. Run data_processing/static/generate_salary_insights.py first."
)
SNAPSHOT_YEARS = (2016, 2021, 2025)

# 聚类指标文件路径
CLUSTER_METRICS_DIR = Path(__file__).resolve().parents[2] / "logs"


def _available_years(conn: sqlite3.Connection) -> List[int]:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT year FROM salary_overview_yearly_cache ORDER BY year ASC")
    return [int(r["year"]) for r in cur.fetchall()]


def _resolve_year(conn: sqlite3.Connection, year: int | None) -> int:
    if year is not None:
        return year
    years = _available_years(conn)
    if not years:
        raise RuntimeError(CACHE_MISSING_MSG)
    return years[-1]


def _fetch_overview(
    conn: sqlite3.Connection, year: int | None = None
) -> tuple[sqlite3.Row, PercentileSummary, int]:
    cur = conn.cursor()
    target_year = None

    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS latest_year FROM salary_overview_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["latest_year"]) if row and row["latest_year"] is not None else None

    if target_year is not None:
        cur.execute(
            """
            SELECT year, total_samples, mean, p25, median, p75, p90, currency_note, updated_at
            FROM salary_overview_yearly_cache
            WHERE year = ?
            """,
            (target_year,),
        )
        row = cur.fetchone()
    else:
        # Fallback to legacy single snapshot cache
        cur.execute(
            """
            SELECT total_samples, mean, p25, median, p75, p90, currency_note, updated_at
            FROM salary_overview_cache
            WHERE id = 1
            """
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError(CACHE_MISSING_MSG)

    distribution = PercentileSummary(
        mean=float(row["mean"]),
        p25=float(row["p25"]),
        median=float(row["median"]),
        p75=float(row["p75"]),
        p90=float(row["p90"]),
    )
    resolved_year = target_year if target_year is not None else year
    return row, distribution, resolved_year


def _fetch_countries(
    conn: sqlite3.Connection, year: int | None = None, limit: int = 8
) -> List[SalaryCountry]:
    cur = conn.cursor()
    target_year = None
    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS y FROM salary_country_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["y"]) if row and row["y"] is not None else None

    rows = []
    if target_year is not None:
        cur.execute(
            """
            SELECT country, median, p75, sample_count
            FROM salary_country_yearly_cache
            WHERE year = ?
            ORDER BY median DESC
            LIMIT ?
            """,
            (target_year, limit),
        )
        rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            SELECT country, median, p75, sample_count
            FROM salary_country_cache
            ORDER BY median DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

    return [
        SalaryCountry(
            country=r["country"],
            median=float(r["median"]),
            p75=float(r["p75"]),
            count=int(r["sample_count"]),
        )
        for r in rows
    ]


def _fetch_experience(conn: sqlite3.Connection, year: int | None = None) -> List[SalaryBucket]:
    cur = conn.cursor()
    target_year = None
    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS y FROM salary_experience_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["y"]) if row and row["y"] is not None else None

    rows = []
    if target_year is not None:
        cur.execute(
            """
            SELECT label, median, average, sample_count
            FROM salary_experience_yearly_cache
            WHERE year = ?
            ORDER BY lower_bound ASC
            """,
            (target_year,),
        )
        rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            SELECT label, median, average, sample_count
            FROM salary_experience_cache
            ORDER BY lower_bound ASC
            """
        )
        rows = cur.fetchall()

    return [
        SalaryBucket(
            label=r["label"],
            median=float(r["median"]),
            average=float(r["average"]),
            count=int(r["sample_count"]),
        )
        for r in rows
    ]


def _fetch_roles(
    conn: sqlite3.Connection, year: int | None = None, limit: int = 8
) -> List[RoleBenchmark]:
    cur = conn.cursor()
    target_year = None
    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS y FROM salary_role_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["y"]) if row and row["y"] is not None else None

    rows = []
    if target_year is not None:
        cur.execute(
            """
            SELECT role, median, p75, sample_count
            FROM salary_role_yearly_cache
            WHERE year = ?
            ORDER BY median DESC, sample_count DESC
            LIMIT ?
            """,
            (target_year, limit),
        )
        rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            SELECT role, median, p75, sample_count
            FROM salary_role_cache
            ORDER BY median DESC, sample_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

    return [
        RoleBenchmark(
            role=r["role"],
            median=float(r["median"]),
            p75=float(r["p75"]),
            count=int(r["sample_count"]),
        )
        for r in rows
    ]


def _fetch_satisfaction(conn: sqlite3.Connection, year: int | None = None) -> List[SatisfactionBand]:
    cur = conn.cursor()
    target_year = None
    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS y FROM salary_satisfaction_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["y"]) if row and row["y"] is not None else None

    rows = []
    if target_year is not None:
        cur.execute(
            """
            SELECT band, median, sample_count
            FROM salary_satisfaction_yearly_cache
            WHERE year = ?
            ORDER BY lower_bound DESC
            """,
            (target_year,),
        )
        rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            SELECT band, median, sample_count
            FROM salary_satisfaction_cache
            ORDER BY lower_bound DESC
            """
        )
        rows = cur.fetchall()

    return [
        SatisfactionBand(
            band=r["band"],
            median=float(r["median"]),
            count=int(r["sample_count"]),
        )
        for r in rows
    ]


def _fetch_clusters(conn: sqlite3.Connection, year: int | None = None) -> List[SalaryCluster]:
    cur = conn.cursor()
    target_year = None
    if year is not None:
        target_year = year
    else:
        cur.execute("SELECT MAX(year) AS y FROM salary_cluster_yearly_cache")
        row = cur.fetchone()
        target_year = int(row["y"]) if row and row["y"] is not None else None

    rows = []
    if target_year is not None:
        cur.execute(
            """
            SELECT cluster_id, label, center_comp, center_exp, size, dominant_role, dominant_country
            FROM salary_cluster_yearly_cache
            WHERE year = ?
            ORDER BY center_comp DESC
            """,
            (target_year,),
        )
        rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            SELECT cluster_id, label, center_comp, center_exp, size, dominant_role, dominant_country
            FROM salary_cluster_cache
            ORDER BY center_comp DESC
            """
        )
        rows = cur.fetchall()

    return [
        SalaryCluster(
            cluster_id=int(r["cluster_id"]),
            label=r["label"],
            center_comp=float(r["center_comp"]),
            center_exp=float(r["center_exp"]),
            size=int(r["size"]),
            dominant_role=r["dominant_role"],
            dominant_country=r["dominant_country"],
        )
        for r in rows
    ]


def build_salary_overview(conn: sqlite3.Connection, year: int | None = None) -> SalaryOverview:
    overview_row, distribution, resolved_year = _fetch_overview(conn, year)

    return SalaryOverview(
        year=resolved_year,
        total_samples=int(overview_row["total_samples"]),
        currency_note=str(overview_row["currency_note"]),
        updated_at=str(overview_row["updated_at"]),
        distribution=distribution,
        top_countries=_fetch_countries(conn, year=resolved_year),
        experience_buckets=_fetch_experience(conn, year=resolved_year),
        role_benchmarks=_fetch_roles(conn, year=resolved_year),
        satisfaction_bands=_fetch_satisfaction(conn, year=resolved_year),
        clusters=_fetch_clusters(conn, year=resolved_year),
    )


def _fetch_overall_trend(conn: sqlite3.Connection) -> List[MedianTrendPoint]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT year, median, p25, p75, p90, total_samples
        FROM salary_overview_yearly_cache
        ORDER BY year ASC
        """
    )
    return [
        MedianTrendPoint(
            year=int(r["year"]),
            median=float(r["median"]),
            p25=float(r["p25"]),
            p75=float(r["p75"]),
            p90=float(r["p90"]),
            samples=int(r["total_samples"]),
        )
        for r in cur.fetchall()
    ]


def _top_keys(conn: sqlite3.Connection, table: str, column: str, limit: int) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT {column} AS key_name, SUM(sample_count) AS total_samples
        FROM {table}
        GROUP BY {column}
        ORDER BY total_samples DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [r["key_name"] for r in cur.fetchall() if r["key_name"]]


def _fetch_series(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    keys: List[str],
    dimension: str,
) -> List[SalaryTrendSeries]:
    cur = conn.cursor()
    series: List[SalaryTrendSeries] = []
    for key in keys:
        cur.execute(
            f"""
            SELECT year, median, sample_count
            FROM {table}
            WHERE {column} = ?
            ORDER BY year ASC
            """,
            (key,),
        )
        points = [
            MedianTrendPoint(
                year=int(r["year"]),
                median=float(r["median"]),
                samples=int(r["sample_count"]),
                p25=None,
                p75=None,
                p90=None,
            )
            for r in cur.fetchall()
        ]
        if points:
            series.append(
                SalaryTrendSeries(
                    name=key,
                    points=points,
                    dimension=dimension,
                )
            )
    return series


def _experience_keys(conn: sqlite3.Connection, limit: int = 5) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT label
        FROM salary_experience_yearly_cache
        GROUP BY label
        ORDER BY MIN(lower_bound) ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [r["label"] for r in cur.fetchall()]


def _load_cluster_metrics() -> Optional[ClusterMetricsSummary]:
    """加载聚类质量指标摘要"""
    summary_path = CLUSTER_METRICS_DIR / "cluster_metrics_summary.json"
    if not summary_path.exists():
        return None

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        yearly_metrics = [
            ClusterMetricsYearly(
                year=m.get("year"),
                n_clusters=m.get("n_clusters", 0),
                n_samples=m.get("n_samples", 0),
                inertia=m.get("inertia", 0.0),
                silhouette_score=m.get("silhouette_score"),
                davies_bouldin_index=m.get("davies_bouldin_index"),
            )
            for m in data.get("yearly_metrics", [])
        ]

        return ClusterMetricsSummary(
            generated_at=data.get("generated_at"),
            total_years=data.get("total_years", 0),
            avg_silhouette_score=data.get("avg_silhouette_score"),
            avg_davies_bouldin_index=data.get("avg_davies_bouldin_index"),
            quality_assessment=data.get("quality_assessment"),
            yearly_metrics=yearly_metrics,
            interpretation=data.get("interpretation"),
        )
    except Exception:
        return None


def build_salary_timeline(conn: sqlite3.Connection) -> SalaryTimelineResponse:
    years = _available_years(conn)
    if not years:
        raise RuntimeError(CACHE_MISSING_MSG)

    snapshot_years = [year for year in SNAPSHOT_YEARS if year in years]
    if not snapshot_years:
        snapshot_years = [years[-1]]

    snapshots = [build_salary_overview(conn, year=year) for year in snapshot_years]

    overall_trend = _fetch_overall_trend(conn)
    country_trends = _fetch_series(
        conn,
        "salary_country_yearly_cache",
        "country",
        _top_keys(conn, "salary_country_yearly_cache", "country", 6),
        "country",
    )
    role_trends = _fetch_series(
        conn,
        "salary_role_yearly_cache",
        "role",
        _top_keys(conn, "salary_role_yearly_cache", "role", 6),
        "role",
    )
    experience_trends = _fetch_series(
        conn,
        "salary_experience_yearly_cache",
        "label",
        _experience_keys(conn, limit=6),
        "experience",
    )

    # 加载聚类质量指标
    cluster_metrics = _load_cluster_metrics()

    return SalaryTimelineResponse(
        snapshots=snapshots,
        overall_trend=overall_trend,
        country_trends=country_trends,
        role_trends=role_trends,
        experience_trends=experience_trends,
        cluster_metrics=cluster_metrics,
    )
