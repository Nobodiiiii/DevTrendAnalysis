# app/models/salary.py
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class PercentileSummary(BaseModel):
    mean: float
    p25: float
    median: float
    p75: float
    p90: float


class SalaryCountry(BaseModel):
    country: str
    median: float
    p75: float
    count: int


class SalaryBucket(BaseModel):
    label: str
    median: float
    average: float
    count: int


class RoleBenchmark(BaseModel):
    role: str
    median: float
    p75: float
    count: int


class SatisfactionBand(BaseModel):
    band: str
    median: float
    count: int


class SalaryCluster(BaseModel):
    cluster_id: int
    label: str
    center_comp: float
    center_exp: float
    size: int
    dominant_role: str | None = None
    dominant_country: str | None = None


class SalaryOverview(BaseModel):
    year: int | None = None
    total_samples: int
    currency_note: str
    updated_at: str | None = None
    distribution: PercentileSummary
    top_countries: List[SalaryCountry]
    experience_buckets: List[SalaryBucket]
    role_benchmarks: List[RoleBenchmark]
    satisfaction_bands: List[SatisfactionBand]
    clusters: List[SalaryCluster]


class MedianTrendPoint(BaseModel):
    year: int
    median: float
    p25: float | None = None
    p75: float | None = None
    p90: float | None = None
    samples: int


class SalaryTrendSeries(BaseModel):
    name: str
    points: List[MedianTrendPoint]
    dimension: str | None = None


class SalaryTimelineResponse(BaseModel):
    snapshots: List[SalaryOverview]
    overall_trend: List[MedianTrendPoint]
    country_trends: List[SalaryTrendSeries]
    role_trends: List[SalaryTrendSeries]
    experience_trends: List[SalaryTrendSeries]
