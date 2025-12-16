"""
Pre-compute salary analytics to speed up API responses.
- Normalises salary-related columns from survey_results_20XX (2012-2025, skipping
  low-quality 2015) into a longitudinal table.
- Builds yearly caches for overview, geo, experience, role, satisfaction and clustering
  so the API can serve multi-year insights quickly.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence

import numpy as np
from sklearn.cluster import KMeans

CACHE_NOTE = (
    "Values are kept in survey-reported (mostly USD-converted) currencies; "
    "use them for relative comparisons, not cross-country absolute pay bands."
)

YEAR_CONFIG: Dict[int, Dict[str, str | None]] = {
    2012: {
        "table": "survey_results_2012",
        "country": "What Country or Region do you live in?",
        "comp": "Including bonus, what is your annual compensation in USD?",
        "devtype": "Which of the following best describes your occupation?",
        "exp": "How many years of IT/Programming experience do you have?",
        "jobsat": None,
    },
    2013: {
        "table": "survey_results_2013",
        "country": "What Country or Region do you live in?",
        "comp": "Including bonus, what is your annual compensation in USD?",
        "devtype": "Which of the following best describes your occupation?",
        "exp": "How many years of IT/Programming experience do you have?",
        "jobsat": None,
    },
    2014: {
        "table": "survey_results_2014",
        "country": "What Country do you live in?",
        "comp": "Including bonus, what is your annual compensation in USD?",
        "devtype": "Which of the following best describes your occupation?",
        "exp": "How many years of IT/Programming experience do you have?",
        "jobsat": None,
    },
    2016: {
        "table": "survey_results_2016",
        "country": "country",
        "comp": "salary_midpoint",
        "devtype": "occupation",
        "exp": None,
        "jobsat": None,
    },
    2017: {
        "table": "survey_results_2017",
        "country": "Country",
        "comp": "Salary",
        "devtype": "DeveloperType",
        "exp": "YearsProgram",
        "jobsat": "JobSatisfaction",
    },
    2018: {
        "table": "survey_results_2018",
        "country": "Country",
        "comp": "ConvertedSalary",
        "devtype": "DevType",
        "exp": "YearsCodingProf",
        "jobsat": "JobSatisfaction",
    },
    2019: {
        "table": "survey_results_2019",
        "country": "Country",
        "comp": "ConvertedComp",
        "devtype": "DevType",
        "exp": "YearsCodePro",
        "jobsat": "JobSat",
    },
    2020: {
        "table": "survey_results_2020",
        "country": "Country",
        "comp": "ConvertedComp",
        "devtype": "DevType",
        "exp": "YearsCodePro",
        "jobsat": "JobSat",
    },
    2021: {
        "table": "survey_results_2021",
        "country": "Country",
        "comp": "ConvertedCompYearly",
        "devtype": "DevType",
        "exp": "YearsCodePro",
        "jobsat": None,
    },
    2022: {
        "table": "survey_results_2022",
        "country": "Country",
        "comp": "ConvertedCompYearly",
        "devtype": "DevType",
        "exp": "WorkExp",
        "jobsat": None,
    },
    2023: {
        "table": "survey_results_2023",
        "country": "Country",
        "comp": "ConvertedCompYearly",
        "devtype": "DevType",
        "exp": "WorkExp",
        "jobsat": None,
    },
    2024: {
        "table": "survey_results_2024",
        "country": "Country",
        "comp": "ConvertedCompYearly",
        "devtype": "DevType",
        "exp": "WorkExp",
        "jobsat": "JobSat",
    },
    2025: {
        "table": "survey_results_2025",
        "country": "Country",
        "comp": "ConvertedCompYearly",
        "devtype": "DevType",
        "exp": "WorkExp",
        "jobsat": "JobSat",
    },
}

SNAPSHOT_YEARS = (2016, 2021, 2025)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def get_connection() -> sqlite3.Connection:
    here = Path(__file__).resolve()
    project_root = here.parents[2]
    db_path = project_root / "data" / "devtrend.db"
    print(f"Using database at {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_overview_cache (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_samples INTEGER NOT NULL,
            mean REAL NOT NULL,
            p25 REAL NOT NULL,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            p90 REAL NOT NULL,
            currency_note TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_country_cache (
            country TEXT PRIMARY KEY,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            sample_count INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_experience_cache (
            label TEXT PRIMARY KEY,
            lower_bound REAL,
            upper_bound REAL,
            median REAL NOT NULL,
            average REAL NOT NULL,
            sample_count INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_role_cache (
            role TEXT PRIMARY KEY,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            sample_count INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_satisfaction_cache (
            band TEXT PRIMARY KEY,
            lower_bound REAL NOT NULL,
            upper_bound REAL NOT NULL,
            median REAL NOT NULL,
            sample_count INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_cluster_cache (
            cluster_id INTEGER PRIMARY KEY,
            label TEXT NOT NULL,
            center_comp REAL NOT NULL,
            center_exp REAL NOT NULL,
            size INTEGER NOT NULL,
            dominant_role TEXT,
            dominant_country TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_longitudinal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            country TEXT,
            work_exp REAL,
            dev_type TEXT,
            job_sat REAL,
            comp REAL NOT NULL
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_salary_longitudinal_year ON salary_longitudinal (year)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_salary_longitudinal_country ON salary_longitudinal (country)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_overview_yearly_cache (
            year INTEGER PRIMARY KEY,
            total_samples INTEGER NOT NULL,
            mean REAL NOT NULL,
            p25 REAL NOT NULL,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            p90 REAL NOT NULL,
            currency_note TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_country_yearly_cache (
            year INTEGER NOT NULL,
            country TEXT NOT NULL,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            PRIMARY KEY (year, country)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_experience_yearly_cache (
            year INTEGER NOT NULL,
            label TEXT NOT NULL,
            lower_bound REAL,
            upper_bound REAL,
            median REAL NOT NULL,
            average REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            PRIMARY KEY (year, label)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_role_yearly_cache (
            year INTEGER NOT NULL,
            role TEXT NOT NULL,
            median REAL NOT NULL,
            p75 REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            PRIMARY KEY (year, role)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_satisfaction_yearly_cache (
            year INTEGER NOT NULL,
            band TEXT NOT NULL,
            lower_bound REAL NOT NULL,
            upper_bound REAL NOT NULL,
            median REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            PRIMARY KEY (year, band)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_cluster_yearly_cache (
            year INTEGER NOT NULL,
            cluster_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            center_comp REAL NOT NULL,
            center_exp REAL NOT NULL,
            size INTEGER NOT NULL,
            dominant_role TEXT,
            dominant_country TEXT,
            PRIMARY KEY (year, cluster_id)
        )
        """
    )

    conn.commit()


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, q))


def clean_country(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = str(raw).strip()
    lower = normalized.lower()
    banned_tokens = ("taiwan",)
    if any(token in lower for token in banned_tokens):
        return None
    return normalized


def normalize_comp(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if float(value) > 0 else None

    text = str(value).strip()
    if not text or text.lower() == "response":
        return None
    cleaned = text.replace(",", "").replace("$", "")

    range_match = re.match(r"([<>]?)\\s*(\\d+(?:\\.\\d+)?)\\s*(?:-|to|–)\\s*(\\d+(?:\\.\\d+)?)", cleaned)
    if range_match:
        low = float(range_match.group(2))
        high = float(range_match.group(3))
        return (low + high) / 2

    single_match = re.match(r"([<>]?)\\s*(\\d+(?:\\.\\d+)?)", cleaned)
    if single_match:
        val = float(single_match.group(2))
        if single_match.group(1) == "<":
            return val * 0.8
        if single_match.group(1) == ">":
            return val * 1.1
        return val

    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_experience(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if float(raw) >= 0 else None

    text = str(raw).strip()
    if not text:
        return None
    lower = text.lower()

    if "less than 1" in lower:
        return 0.5
    if "more than" in lower:
        m = re.search(r"(\\d+)", lower)
        if m:
            return float(m.group(1)) + 1.0
    plus_match = re.match(r"(\\d+(?:\\.\\d+)?)\\+", lower)
    if plus_match:
        return float(plus_match.group(1)) + 1.0

    range_match = re.match(r"(\\d+(?:\\.\\d+)?)\\s*(?:-|to|–)\\s*(\\d+(?:\\.\\d+)?)", lower.replace(",", ""))
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return (low + high) / 2

    try:
        return float(lower)
    except ValueError:
        return None


SAT_ORDER = [
    "extremely dissatisfied",
    "very dissatisfied",
    "moderately dissatisfied",
    "slightly dissatisfied",
    "neither satisfied nor dissatisfied",
    "slightly satisfied",
    "moderately satisfied",
    "very satisfied",
    "extremely satisfied",
]


def normalize_job_sat(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if not text:
        return None
    lower = text.lower()

    if lower.isdigit():
        return float(lower)

    if lower in SAT_ORDER:
        idx = SAT_ORDER.index(lower)
        if len(SAT_ORDER) > 1:
            return idx / (len(SAT_ORDER) - 1) * 10
        return float(idx)

    return None


def load_year_rows(conn: sqlite3.Connection, year: int, cfg: Dict[str, str | None]) -> List[Dict[str, object]]:
    table = cfg["table"]
    country_col = quote_ident(str(cfg["country"]))
    comp_col = quote_ident(str(cfg["comp"]))

    selects = [f"{country_col} AS country", f"{comp_col} AS comp"]
    if cfg.get("devtype"):
        selects.append(f"{quote_ident(str(cfg['devtype']))} AS dev_type")
    if cfg.get("exp"):
        selects.append(f"{quote_ident(str(cfg['exp']))} AS work_exp_raw")
    if cfg.get("jobsat"):
        selects.append(f"{quote_ident(str(cfg['jobsat']))} AS job_sat_raw")

    sql = f"SELECT {', '.join(selects)} FROM {table}"
    cur = conn.execute(sql)

    normalized: List[Dict[str, object]] = []
    dropped = 0

    def _row_val(r: sqlite3.Row, key: str) -> object | None:
        return r[key] if key in r.keys() else None

    for row in cur.fetchall():
        comp_val = normalize_comp(_row_val(row, "comp"))
        if comp_val is None or comp_val <= 0:
            dropped += 1
            continue

        country = clean_country(_row_val(row, "country"))
        if not country:
            dropped += 1
            continue

        record: Dict[str, object] = {
            "country": country,
            "comp": comp_val,
            "dev_type": _row_val(row, "dev_type") or "",
        }

        if "work_exp_raw" in row.keys() and _row_val(row, "work_exp_raw") is not None:
            record["work_exp"] = normalize_experience(_row_val(row, "work_exp_raw"))
        else:
            record["work_exp"] = None

        if "job_sat_raw" in row.keys() and _row_val(row, "job_sat_raw") is not None:
            record["job_sat"] = normalize_job_sat(_row_val(row, "job_sat_raw"))
        else:
            record["job_sat"] = normalize_job_sat(_row_val(row, "job_sat"))

        normalized.append(record)

    print(f"Year {year}: loaded {len(normalized):,} salary rows; dropped {dropped:,}.")
    return normalized


def write_longitudinal(conn: sqlite3.Connection, rows_by_year: Dict[int, List[Dict[str, object]]]) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM salary_longitudinal")
    records: List[tuple] = []
    for year, rows in rows_by_year.items():
        for row in rows:
            records.append(
                (
                    year,
                    row.get("country"),
                    row.get("work_exp"),
                    row.get("dev_type"),
                    row.get("job_sat"),
                    row["comp"],
                )
            )

    cur.executemany(
        """
        INSERT INTO salary_longitudinal
            (year, country, work_exp, dev_type, job_sat, comp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    conn.commit()
    print(f"Wrote salary_longitudinal with {len(records):,} rows")


def build_overview(conn: sqlite3.Connection, rows: List[Dict[str, object]], year: int | None = None) -> None:
    salaries = [float(r["comp"]) for r in rows if r.get("comp") is not None]
    overview = {
        "total_samples": len(salaries),
        "mean": float(mean(salaries)) if salaries else 0.0,
        "p25": percentile(salaries, 25),
        "median": percentile(salaries, 50),
        "p75": percentile(salaries, 75),
        "p90": percentile(salaries, 90),
        "currency_note": CACHE_NOTE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    cur = conn.cursor()
    if year is None:
        cur.execute("DELETE FROM salary_overview_cache")
        cur.execute(
            """
            INSERT INTO salary_overview_cache
                (id, total_samples, mean, p25, median, p75, p90, currency_note, updated_at)
            VALUES (1, :total_samples, :mean, :p25, :median, :p75, :p90, :currency_note, :updated_at)
            """,
            overview,
        )
        print("Wrote salary_overview_cache")
    else:
        cur.execute("DELETE FROM salary_overview_yearly_cache WHERE year = ?", (year,))
        cur.execute(
            """
            INSERT INTO salary_overview_yearly_cache
                (year, total_samples, mean, p25, median, p75, p90, currency_note, updated_at)
            VALUES (:year, :total_samples, :mean, :p25, :median, :p75, :p90, :currency_note, :updated_at)
            """,
            {**overview, "year": year},
        )
        print(f"Wrote salary_overview_yearly_cache for {year}")

    conn.commit()


def build_countries(
    conn: sqlite3.Connection,
    rows: List[Dict[str, object]],
    min_count: int = 50,
    limit: int = 20,
    year: int | None = None,
) -> None:
    bucket: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        country = row.get("country")
        comp = row.get("comp")
        if not country or comp is None:
            continue
        bucket[country].append(float(comp))

    items = []
    for country, values in bucket.items():
        if len(values) < min_count:
            continue
        items.append(
            (
                country,
                percentile(values, 50),
                percentile(values, 75),
                len(values),
            )
        )

    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:limit]

    cur = conn.cursor()
    if year is None:
        cur.execute("DELETE FROM salary_country_cache")
        cur.executemany(
            """
            INSERT INTO salary_country_cache (country, median, p75, sample_count)
            VALUES (?, ?, ?, ?)
            """,
            items,
        )
        print(f"Wrote salary_country_cache with {len(items)} rows")
    else:
        cur.execute("DELETE FROM salary_country_yearly_cache WHERE year = ?", (year,))
        cur.executemany(
            """
            INSERT INTO salary_country_yearly_cache (year, country, median, p75, sample_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(year, *row) for row in items],
        )
        print(f"Wrote salary_country_yearly_cache for {year} with {len(items)} rows")
    conn.commit()


def build_experience(conn: sqlite3.Connection, rows: List[Dict[str, object]], year: int | None = None) -> None:
    buckets: List[tuple[str, float, float | None]] = [
        ("0-2 yrs", 0.0, 2.0),
        ("2-5 yrs", 2.0, 5.0),
        ("5-10 yrs", 5.0, 10.0),
        ("10-15 yrs", 10.0, 15.0),
        ("15+ yrs", 15.0, None),
    ]
    bucket_values: Dict[str, List[float]] = {label: [] for label, _, _ in buckets}

    for row in rows:
        exp = row.get("work_exp")
        comp = row.get("comp")
        if exp is None or comp is None:
            continue
        for label, lower, upper in buckets:
            if upper is None and exp >= lower:
                bucket_values[label].append(float(comp))
                break
            if upper is not None and lower <= exp < upper:
                bucket_values[label].append(float(comp))
                break

    records = []
    for label, lower, upper in buckets:
        values = bucket_values[label]
        if not values:
            continue
        records.append(
            (
                label,
                lower,
                upper,
                percentile(values, 50),
                float(mean(values)),
                len(values),
            )
        )

    cur = conn.cursor()
    if year is None:
        cur.execute("DELETE FROM salary_experience_cache")
        cur.executemany(
            """
            INSERT INTO salary_experience_cache
                (label, lower_bound, upper_bound, median, average, sample_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        print(f"Wrote salary_experience_cache with {len(records)} rows")
    else:
        cur.execute("DELETE FROM salary_experience_yearly_cache WHERE year = ?", (year,))
        cur.executemany(
            """
            INSERT INTO salary_experience_yearly_cache
                (year, label, lower_bound, upper_bound, median, average, sample_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(year, *r) for r in records],
        )
        print(f"Wrote salary_experience_yearly_cache for {year} with {len(records)} rows")
    conn.commit()


def build_roles(
    conn: sqlite3.Connection,
    rows: List[Dict[str, object]],
    min_count: int = 120,
    limit: int = 20,
    year: int | None = None,
) -> None:
    role_bucket: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        comp = row.get("comp")
        raw_roles = row.get("dev_type") or ""
        if comp is None:
            continue
        for part in raw_roles.split(";"):
            role = part.strip()
            if not role:
                continue
            role_bucket[role].append(float(comp))

    items = []
    for role, values in role_bucket.items():
        if len(values) < min_count:
            continue
        items.append((role, percentile(values, 50), percentile(values, 75), len(values)))

    items.sort(key=lambda x: (x[1], x[3]), reverse=True)
    items = items[:limit]

    cur = conn.cursor()
    if year is None:
        cur.execute("DELETE FROM salary_role_cache")
        cur.executemany(
            """
            INSERT INTO salary_role_cache (role, median, p75, sample_count)
            VALUES (?, ?, ?, ?)
            """,
            items,
        )
        print(f"Wrote salary_role_cache with {len(items)} rows")
    else:
        cur.execute("DELETE FROM salary_role_yearly_cache WHERE year = ?", (year,))
        cur.executemany(
            """
            INSERT INTO salary_role_yearly_cache (year, role, median, p75, sample_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(year, *r) for r in items],
        )
        print(f"Wrote salary_role_yearly_cache for {year} with {len(items)} rows")
    conn.commit()


def build_satisfaction(conn: sqlite3.Connection, rows: List[Dict[str, object]], year: int | None = None) -> None:
    bands: List[tuple[str, float, float]] = [
        ("9-10 high satisfaction", 9.0, 11.0),
        ("7-8 medium satisfaction", 7.0, 9.0),
        ("<7 lower satisfaction", -1.0, 7.0),
    ]
    bucket: Dict[str, List[float]] = {label: [] for label, _, _ in bands}

    for row in rows:
        score = row.get("job_sat")
        comp = row.get("comp")
        if score is None or comp is None:
            continue
        for label, lower, upper in bands:
            if lower <= score < upper:
                bucket[label].append(float(comp))
                break

    records = []
    for label, lower, upper in bands:
        values = bucket[label]
        if not values:
            continue
        records.append((label, lower, upper, percentile(values, 50), len(values)))

    cur = conn.cursor()
    if year is None:
        cur.execute("DELETE FROM salary_satisfaction_cache")
        cur.executemany(
            """
            INSERT INTO salary_satisfaction_cache (band, lower_bound, upper_bound, median, sample_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            records,
        )
        print(f"Wrote salary_satisfaction_cache with {len(records)} rows")
    else:
        cur.execute("DELETE FROM salary_satisfaction_yearly_cache WHERE year = ?", (year,))
        cur.executemany(
            """
            INSERT INTO salary_satisfaction_yearly_cache
                (year, band, lower_bound, upper_bound, median, sample_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(year, *r) for r in records],
        )
        print(f"Wrote salary_satisfaction_yearly_cache for {year} with {len(records)} rows")
    conn.commit()


def _cluster_label(center_exp: float, center_comp: float, global_median: float) -> str:
    if center_exp < 3:
        prefix = "Early"
    elif center_exp < 8:
        prefix = "Mid"
    else:
        prefix = "Senior"
    pay_tag = "high" if center_comp >= global_median else "core"
    return f"{prefix} {pay_tag} cluster"


def build_clusters(conn: sqlite3.Connection, rows: List[Dict[str, object]], year: int | None = None) -> None:
    samples = []
    meta = []
    for row in rows:
        exp = row.get("work_exp")
        comp = row.get("comp")
        country = row.get("country") or ""
        dev_type = row.get("dev_type") or ""
        if exp is None or comp is None:
            continue
        samples.append([exp, np.log1p(comp)])
        meta.append((exp, comp, country, dev_type))

    cur = conn.cursor()
    target_table = "salary_cluster_cache" if year is None else "salary_cluster_yearly_cache"

    if len(samples) < 40:
        print(f"Not enough samples for clustering ({len(samples)} rows); clearing {target_table}.")
        if year is None:
            cur.execute("DELETE FROM salary_cluster_cache")
        else:
            cur.execute("DELETE FROM salary_cluster_yearly_cache WHERE year = ?", (year,))
        conn.commit()
        return

    n_clusters = 4
    if len(samples) < 120:
        n_clusters = 3
    if len(samples) < 80:
        n_clusters = 2

    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = model.fit_predict(np.array(samples))

    cluster_members: Dict[int, List[int]] = defaultdict(list)
    for idx, lbl in enumerate(labels):
        cluster_members[int(lbl)].append(idx)

    comp_values = [m[1] for m in meta]
    global_median = percentile(comp_values, 50)

    records = []
    for cid, indices in cluster_members.items():
        comp_list = [meta[i][1] for i in indices]
        exp_list = [meta[i][0] for i in indices if meta[i][0] is not None]
        roles: Counter[str] = Counter()
        countries: Counter[str] = Counter()
        for i in indices:
            role_parts = (meta[i][3] or "").split(";")
            for part in role_parts:
                role = part.strip()
                if role:
                    roles[role] += 1
            country = meta[i][2].strip()
            if country:
                countries[country] += 1

        center_comp = float(mean(comp_list)) if comp_list else 0.0
        center_exp = float(mean(exp_list)) if exp_list else 0.0
        dominant_role = roles.most_common(1)[0][0] if roles else None
        dominant_country = countries.most_common(1)[0][0] if countries else None
        label = _cluster_label(center_exp, center_comp, global_median)

        records.append(
            (
                cid,
                label,
                center_comp,
                center_exp,
                len(indices),
                dominant_role,
                dominant_country,
            )
        )

    records.sort(key=lambda x: x[2], reverse=True)

    if year is None:
        cur.execute("DELETE FROM salary_cluster_cache")
        cur.executemany(
            """
            INSERT INTO salary_cluster_cache
                (cluster_id, label, center_comp, center_exp, size, dominant_role, dominant_country)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
    else:
        cur.execute("DELETE FROM salary_cluster_yearly_cache WHERE year = ?", (year,))
        cur.executemany(
            """
            INSERT INTO salary_cluster_yearly_cache
                (year, cluster_id, label, center_comp, center_exp, size, dominant_role, dominant_country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(year, *r) for r in records],
        )

    conn.commit()
    print(f"Wrote {target_table} with {len(records)} clusters for year {year or 'latest'}")


def build_yearly_caches(conn: sqlite3.Connection, rows_by_year: Dict[int, List[Dict[str, object]]]) -> None:
    for year, rows in sorted(rows_by_year.items()):
        print(f"Building yearly caches for {year} ...")
        build_overview(conn, rows, year=year)
        build_countries(conn, rows, year=year)
        build_experience(conn, rows, year=year)
        build_roles(conn, rows, year=year)
        build_satisfaction(conn, rows, year=year)
        build_clusters(conn, rows, year=year)


def main() -> None:
    conn = get_connection()
    ensure_tables(conn)

    rows_by_year: Dict[int, List[Dict[str, object]]] = {}
    for year, cfg in YEAR_CONFIG.items():
        try:
            rows = load_year_rows(conn, year, cfg)
        except sqlite3.Error as exc:
            print(f"Skip {year} due to SQL error: {exc}")
            continue
        if rows:
            rows_by_year[year] = rows

    if not rows_by_year:
        print("No salary rows available after filtering; nothing to cache.")
        return

    write_longitudinal(conn, rows_by_year)

    latest_year = max(rows_by_year.keys())
    build_overview(conn, rows_by_year[latest_year])
    build_countries(conn, rows_by_year[latest_year])
    build_experience(conn, rows_by_year[latest_year])
    build_roles(conn, rows_by_year[latest_year])
    build_satisfaction(conn, rows_by_year[latest_year])
    build_clusters(conn, rows_by_year[latest_year])

    build_yearly_caches(conn, rows_by_year)
    print("Salary preprocessing finished.")


if __name__ == "__main__":
    main()
