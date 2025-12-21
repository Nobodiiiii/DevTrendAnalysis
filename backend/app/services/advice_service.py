from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame, functions as F

# =========================
# Metrics output directory
# =========================
METRICS_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(METRICS_OUTPUT_DIR, exist_ok=True)

# Gold 元数据路径
GOLD_METADATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "gold_metadata", "gold_2025_metadata.json")

# 缓存 Gold 元数据
_gold_metadata: Optional[Dict[str, Any]] = None
_gold_metadata_loaded: bool = False


def _load_gold_metadata() -> Optional[Dict[str, Any]]:
    """加载 Gold 表构建时生成的元数据"""
    global _gold_metadata, _gold_metadata_loaded
    if _gold_metadata_loaded:
        return _gold_metadata
    try:
        if os.path.exists(GOLD_METADATA_PATH):
            with open(GOLD_METADATA_PATH, "r", encoding="utf-8") as f:
                _gold_metadata = json.load(f)
        else:
            _gold_metadata = None
    except Exception:
        _gold_metadata = None
    _gold_metadata_loaded = True
    return _gold_metadata


def _save_metrics_to_file(metrics: Dict[str, Any]) -> str:
    """将指标保存到本地文件，返回文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"advice_metrics_{timestamp}.json"
    filepath = os.path.join(METRICS_OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    return filepath

# =========================
# HDFS Gold paths (2025)
# =========================

# ✅ salary benchmark rollups (fallback levels)
GOLD_BENCH_L1 = "hdfs://localhost:9000/advice/gold/2025/salary_benchmark_lvl1_emp_wb_dt"
GOLD_BENCH_L2 = "hdfs://localhost:9000/advice/gold/2025/salary_benchmark_lvl2_emp_wb"
GOLD_BENCH_L3 = "hdfs://localhost:9000/advice/gold/2025/salary_benchmark_lvl3_emp_dt"
GOLD_BENCH_L4 = "hdfs://localhost:9000/advice/gold/2025/salary_benchmark_lvl4_emp_all"

# ✅ tech trends
GOLD_TREND_LANG = "hdfs://localhost:9000/advice/gold/2025/tech_trends_language"
GOLD_TREND_DB = "hdfs://localhost:9000/advice/gold/2025/tech_trends_database"
GOLD_TREND_WEB = "hdfs://localhost:9000/advice/gold/2025/tech_trends_webframe"
GOLD_TREND_PLATFORM = "hdfs://localhost:9000/advice/gold/2025/tech_trends_platform"

# ✅ tech trends by salary tier (high/mid/low)
GOLD_TREND_LANG_BY_SALARY = "hdfs://localhost:9000/advice/gold/2025/tech_trends_language_by_salary"
GOLD_TREND_DB_BY_SALARY = "hdfs://localhost:9000/advice/gold/2025/tech_trends_database_by_salary"
GOLD_TREND_WEB_BY_SALARY = "hdfs://localhost:9000/advice/gold/2025/tech_trends_webframe_by_salary"
GOLD_TREND_PLATFORM_BY_SALARY = "hdfs://localhost:9000/advice/gold/2025/tech_trends_platform_by_salary"

# =========================
# Global knobs
# =========================

# ✅ FX：USD 内部计算，CNY 展示
FX_USD_TO_CNY = 7.06
FX_LABEL = f"1 USD ≈ {FX_USD_TO_CNY} CNY"

# ✅ 回退阈值：低于该 n 自动回退到更粗粒度（薪资 & 栈建议共用）
MIN_N = 200

# ✅ "绝对需求门槛"——防止小众项被 gap 顶上来
# 你可以后面调参：想更"稳"就提高，想更"探索"就降低
LANG_MIN_WANT = 0.08  # 语言：至少 8% 想用
WEB_MIN_WANT = 0.08  # 框架：至少 8% 想用
DB_MIN_WANT = 0.05  # 数据库：至少 5% 想用
PLATFORM_MIN_WANT = 0.08  # 平台/工具：至少 8% 想用

# “如果门槛下没有可推荐项”，自动降档的梯度（不至于空）
RELAX_FACTORS = [1.0, 0.6, 0.3, 0.0]

# 仅用于“可信度”展示
N_STRONG = 200
N_OK = 80

TRACK_TO_FAMILY = {
    "前端开发": "frontend",
    "后端开发": "backend",
    "全栈开发": "fullstack",
    "测试 / QA": "qa",
    "数据工程": "data_ml",
    "算法 / AI": "data_ml",
    "移动端开发": "mobile",
    "DevOps / SRE": "devops_cloud_sre",
    "暂未确定": "other",
}

# ✅ 经验层级进阶映射
WORKEXP_ADVANCEMENT = {
    "0-1": "2-3",
    "2-3": "4-6",
    "4-6": "7-10",
    "7-10": "11-15",
    "11-15": "16+",
    "16+": None,  # 最高层级，无进阶
}

# ✅ 进阶推荐阈值
ADV_MIN_LIFT = 0.03  # 进阶人群 have_rate 至少比当前高 3%
ADV_MIN_TARGET_HAVE = 0.08  # 进阶人群 have_rate 至少 8%

# ✅ 高薪技术差异推荐阈值
SALARY_TIER_MIN_DIFF = 0.03  # 高薪人群 have_rate 比低薪人群至少高 3%
SALARY_TIER_MIN_HIGH_HAVE = 0.10  # 高薪人群 have_rate 至少 10%

# =========================
# Spark cache
# =========================

_lock = threading.Lock()
_spark: Optional[SparkSession] = None

_bench_l1: Optional[DataFrame] = None
_bench_l2: Optional[DataFrame] = None
_bench_l3: Optional[DataFrame] = None
_bench_l4: Optional[DataFrame] = None

_lang_trend_df: Optional[DataFrame] = None
_db_trend_df: Optional[DataFrame] = None
_web_trend_df: Optional[DataFrame] = None
_platform_trend_df: Optional[DataFrame] = None

# ✅ 按薪资分层的技术趋势表缓存
_lang_salary_tier_df: Optional[DataFrame] = None
_db_salary_tier_df: Optional[DataFrame] = None
_web_salary_tier_df: Optional[DataFrame] = None
_platform_salary_tier_df: Optional[DataFrame] = None


def _ensure_tables() -> Tuple[
    SparkSession, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame,
    DataFrame, DataFrame, DataFrame, DataFrame]:
    """
    返回：
    spark, bench_l1, bench_l2, bench_l3, bench_l4,
    lang_df, db_df, web_df, platform_df,
    lang_salary_tier_df, db_salary_tier_df, web_salary_tier_df, platform_salary_tier_df
    """
    global _spark, _bench_l1, _bench_l2, _bench_l3, _bench_l4
    global _lang_trend_df, _db_trend_df, _web_trend_df, _platform_trend_df
    global _lang_salary_tier_df, _db_salary_tier_df, _web_salary_tier_df, _platform_salary_tier_df

    with _lock:
        if _spark is None:
            _spark = SparkSession.builder.appName("devtrend-advice-service").getOrCreate()

        if _bench_l1 is None:
            _bench_l1 = _spark.read.parquet(GOLD_BENCH_L1).cache()
        if _bench_l2 is None:
            _bench_l2 = _spark.read.parquet(GOLD_BENCH_L2).cache()
        if _bench_l3 is None:
            _bench_l3 = _spark.read.parquet(GOLD_BENCH_L3).cache()
        if _bench_l4 is None:
            _bench_l4 = _spark.read.parquet(GOLD_BENCH_L4).cache()

        if _lang_trend_df is None:
            _lang_trend_df = _spark.read.parquet(GOLD_TREND_LANG).cache()
        if _db_trend_df is None:
            _db_trend_df = _spark.read.parquet(GOLD_TREND_DB).cache()
        if _web_trend_df is None:
            _web_trend_df = _spark.read.parquet(GOLD_TREND_WEB).cache()
        if _platform_trend_df is None:
            _platform_trend_df = _spark.read.parquet(GOLD_TREND_PLATFORM).cache()

        # ✅ 按薪资分层的技术趋势表
        if _lang_salary_tier_df is None:
            try:
                _lang_salary_tier_df = _spark.read.parquet(GOLD_TREND_LANG_BY_SALARY).cache()
            except Exception:
                _lang_salary_tier_df = None
        if _db_salary_tier_df is None:
            try:
                _db_salary_tier_df = _spark.read.parquet(GOLD_TREND_DB_BY_SALARY).cache()
            except Exception:
                _db_salary_tier_df = None
        if _web_salary_tier_df is None:
            try:
                _web_salary_tier_df = _spark.read.parquet(GOLD_TREND_WEB_BY_SALARY).cache()
            except Exception:
                _web_salary_tier_df = None
        if _platform_salary_tier_df is None:
            try:
                _platform_salary_tier_df = _spark.read.parquet(GOLD_TREND_PLATFORM_BY_SALARY).cache()
            except Exception:
                _platform_salary_tier_df = None

    return (_spark, _bench_l1, _bench_l2, _bench_l3, _bench_l4,
            _lang_trend_df, _db_trend_df, _web_trend_df, _platform_trend_df,
            _lang_salary_tier_df, _db_salary_tier_df, _web_salary_tier_df, _platform_salary_tier_df)


# =========================
# Helpers
# =========================

def _workexp_bin(years: Any) -> str:
    try:
        y = int(str(years).strip())
    except Exception:
        return "unknown"
    if y <= 1:
        return "0-1"
    if 2 <= y <= 3:
        return "2-3"
    if 4 <= y <= 6:
        return "4-6"
    if 7 <= y <= 10:
        return "7-10"
    if 11 <= y <= 15:
        return "11-15"
    return "16+"


def _confidence(n: int) -> str:
    if n >= N_STRONG:
        return "高"
    if n >= N_OK:
        return "中"
    return "低"


def _usd_to_cny(x_usd: float) -> float:
    return float(x_usd) * FX_USD_TO_CNY


def _fmt_cny_from_usd(x_usd: float) -> str:
    return f"¥{_usd_to_cny(x_usd):,.0f}"


def _cny_to_usd(x_cny: float) -> float:
    return float(x_cny) / FX_USD_TO_CNY


def _parse_salary_band_cny(band: str) -> Tuple[Optional[float], Optional[float]]:
    """
    解析你前端的人民币区间文案：
      '< 20 万 / 年' => (None, 200000)
      '20–30 万 / 年' => (200000, 300000)
      '> 80 万 / 年' => (800000, None)
      '暂不透露' => (None, None)
    """
    b = (band or "").strip()
    if not b or b == "暂不透露":
        return None, None

    b = b.replace("—", "–").replace("-", "–")

    m_lt = re.search(r"<\s*(\d+)\s*万", b)
    if m_lt:
        return None, float(m_lt.group(1)) * 10000

    m_gt = re.search(r">\s*(\d+)\s*万", b)
    if m_gt:
        return float(m_gt.group(1)) * 10000, None

    m_range = re.search(r"(\d+)\s*–\s*(\d+)\s*万", b)
    if m_range:
        lo = float(m_range.group(1)) * 10000
        hi = float(m_range.group(2)) * 10000
        return lo, hi

    m_any = re.search(r"(\d+)\s*万", b)
    if m_any:
        v = float(m_any.group(1)) * 10000
        return v, None

    return None, None


# =========================
# Salary benchmark fallback
# =========================

def _bench_lookup_with_fallback(
        bench_l1: DataFrame,
        bench_l2: DataFrame,
        bench_l3: DataFrame,
        bench_l4: DataFrame,
        emp: str,
        wb: str,
        fam: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    回退顺序（直到命中且 n >= MIN_N；否则继续回退）：
      L1: emp + wb + fam
      L2: emp + wb
      L3: emp + fam
      L4: emp
    返回：(row_dict_or_none, level_used)
    """
    best: Optional[Dict[str, Any]] = None

    # L1
    r1 = (
        bench_l1.where(
            (F.col("employment_std") == emp) &
            (F.col("workexp_bin") == wb) &
            (F.col("devtype_family") == fam)
        ).limit(1).collect()
    )
    if r1:
        d = r1[0].asDict()
        best = d
        if int(d["n"]) >= MIN_N:
            return d, "L1(emp+workexp+devtype)"

    # L2
    r2 = (
        bench_l2.where(
            (F.col("employment_std") == emp) &
            (F.col("workexp_bin") == wb)
        ).limit(1).collect()
    )
    if r2:
        d = r2[0].asDict()
        if best is None or int(d["n"]) > int(best["n"]):
            best = d
        if int(d["n"]) >= MIN_N:
            return d, "L2(emp+workexp)"

    # L3
    r3 = (
        bench_l3.where(
            (F.col("employment_std") == emp) &
            (F.col("devtype_family") == fam)
        ).limit(1).collect()
    )
    if r3:
        d = r3[0].asDict()
        if best is None or int(d["n"]) > int(best["n"]):
            best = d
        if int(d["n"]) >= MIN_N:
            return d, "L3(emp+devtype)"

    # L4
    r4 = bench_l4.where(F.col("employment_std") == emp).limit(1).collect()
    if r4:
        d = r4[0].asDict()
        return d, "L4(emp)"

    return best, "L?(fallback_failed)"


# =========================
# Trend fallback (avoid “disappear”)
# =========================

def _trend_cohort_n_total(filter_df: DataFrame, distinct_keys: List[str]) -> int:
    """
    trend_df 每个 tech 行都有 n（重复），不能 sum(n)。
    正确：按 cohort key 去重后再 sum(n)。
    """
    row = (
        filter_df.select(*distinct_keys, "n")
        .dropDuplicates(distinct_keys)
        .agg(F.sum("n").alias("n_total"))
        .collect()
    )
    if not row:
        return 0
    return int(row[0]["n_total"] or 0)


def _trend_rollup(base_df: DataFrame, n_total: int) -> DataFrame:
    """
    将多个 cohort 汇总成一个更粗粒度 cohort：
    - 先用 have_rate*n、want_rate*n 估算计数
    - 再按 tech 汇总
    - 最后重新算 have_rate/want_rate/gap
    """
    rolled = (
        base_df.withColumn("have_cnt_est", F.col("have_rate") * F.col("n"))
        .withColumn("want_cnt_est", F.col("want_rate") * F.col("n"))
        .groupBy("tech")
        .agg(
            F.sum("have_cnt_est").alias("have_cnt"),
            F.sum("want_cnt_est").alias("want_cnt"),
        )
        .withColumn("n", F.lit(int(n_total)))
        .withColumn("have_rate", F.col("have_cnt") / F.col("n"))
        .withColumn("want_rate", F.col("want_cnt") / F.col("n"))
        .withColumn("gap", F.col("want_rate") - F.col("have_rate"))
        .select("tech", "n", "have_rate", "want_rate", "gap")
    )
    return rolled


def _trend_build_cohort_with_fallback(
        trend_df: DataFrame,
        wb: str,
        fam: str,
        min_n: int = MIN_N,
) -> Tuple[Optional[DataFrame], str, int]:
    """
    回退顺序：
      T1: workexp_bin + devtype_family
      T2: workexp_bin
      T3: devtype_family
      T4: global
    返回：cohort_df(tech,n,have_rate,want_rate,gap), level_used, n_used
    """
    # ---------- T1 ----------
    t1 = trend_df.where((F.col("workexp_bin") == wb) & (F.col("devtype_family") == fam))
    n1 = _trend_cohort_n_total(t1, ["workexp_bin", "devtype_family"])
    if n1 >= min_n:
        return t1.select("tech", "n", "have_rate", "want_rate", "gap"), "T1(workexp+devtype)", n1

    # ---------- T2 ----------
    t2 = trend_df.where(F.col("workexp_bin") == wb)
    n2 = _trend_cohort_n_total(t2, ["workexp_bin", "devtype_family"])
    if n2 >= min_n:
        return _trend_rollup(t2, n2), "T2(workexp)", n2

    # ---------- T3 ----------
    t3 = trend_df.where(F.col("devtype_family") == fam)
    n3 = _trend_cohort_n_total(t3, ["workexp_bin", "devtype_family"])
    if n3 >= min_n:
        return _trend_rollup(t3, n3), "T3(devtype)", n3

    # ---------- T4 ----------
    t4 = trend_df
    n4 = _trend_cohort_n_total(t4, ["workexp_bin", "devtype_family"])
    if n4 > 0:
        return _trend_rollup(t4, n4), "T4(global)", n4

    return None, "T?(no_data)", 0


def _trend_pick_recos(
        cohort_df: DataFrame,
        selected_set: set,
        top_k: int,
        *,
        base_min_want_rate: float,
        mode: str,  # "mainstream" | "gap"
) -> Tuple[List[str], float, Dict[str, Any]]:
    """
    两种推荐：
      - mainstream: 按 want_rate 排（先补主流地基）
      - gap: 按 gap 排（潜力加分，但仍受 want_rate 门槛约束）
    为避免空结果：min_want_rate 会按 RELAX_FACTORS 自动降档。
    返回：lines, used_min_want_rate, metrics
    """
    metrics = {
        "mode": mode,
        "base_threshold": base_min_want_rate,
        "used_threshold": base_min_want_rate,
        "relax_steps": 0,
        "candidate_pool_size": 0,
        "final_reco_count": 0,
        "selected_excluded": len(selected_set),
    }

    if cohort_df is None:
        metrics["status"] = "no_cohort_data"
        return [], base_min_want_rate, metrics

    df = cohort_df
    # 统计候选池大小（排除已选）
    total_candidates = df.count() if df is not None else 0
    if selected_set:
        df = df.where(~F.col("tech").isin(list(selected_set)))
    candidates_after_exclude = df.count() if df is not None else 0
    metrics["total_tech_count"] = total_candidates
    metrics["candidate_pool_size"] = candidates_after_exclude

    # 逐级放宽阈值，直到拿到结果
    for step, factor in enumerate(RELAX_FACTORS):
        thr = float(base_min_want_rate) * float(factor)
        cand = df.where(F.col("want_rate") >= F.lit(thr))

        if mode == "mainstream":
            cand = cand.orderBy(F.col("want_rate").desc(), F.col("have_rate").desc())
        else:
            cand = cand.orderBy(F.col("gap").desc(), F.col("want_rate").desc())

        rows = cand.limit(top_k).collect()
        if rows:
            out: List[str] = []
            for r in rows:
                d = r.asDict()
                out.append(
                    f"- {d['tech']}（gap {float(d['gap']):+.1%}，want {float(d['want_rate']):.1%} vs have {float(d['have_rate']):.1%}）"
                )
            metrics["used_threshold"] = thr
            metrics["relax_steps"] = step
            metrics["final_reco_count"] = len(out)
            metrics["status"] = "success"
            return out, thr, metrics

    metrics["status"] = "no_results_after_relax"
    return [], base_min_want_rate, metrics


def _trend_pick_chosen_popularity(
        cohort_df: DataFrame,
        selected_set: set,
        limit_n: int = 3,
) -> List[str]:
    if cohort_df is None or not selected_set:
        return []
    rows = (
        cohort_df.where(F.col("tech").isin(list(selected_set)))
        .orderBy(F.col("have_rate").desc())
        .limit(limit_n)
        .collect()
    )
    out: List[str] = []
    for r in rows:
        d = r.asDict()
        out.append(f"- {d['tech']}（在该统计口径中 have≈{float(d['have_rate']):.1%}）")
    return out


# =========================
# Main API function
# =========================

def generate_advice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成职业建议数据（纯数据返回，不生成文本）
    前端将使用返回的结构化数据生成用户友好的文本
    """
    (_, bench_l1, bench_l2, bench_l3, bench_l4, lang_df, db_df, web_df, platform_df,
     lang_salary_tier_df, db_salary_tier_df, web_salary_tier_df, platform_salary_tier_df) = _ensure_tables()

    tech = payload.get("techStack", {}) or {}
    sel_lang = tech.get("languages", []) or []
    sel_db = tech.get("databases", []) or []
    sel_web = tech.get("webframes", []) or []
    sel_platform = tech.get("platforms", []) or []

    profile_type = payload.get("profileType", "")

    # cohort inputs
    if profile_type == "student":
        track = (payload.get("studentProfile", {}) or {}).get("expectedTrack", "")
        fam = TRACK_TO_FAMILY.get(track, "other")
        wb = "0-1"
        emp = "employed"
        is_market_ref = True
        salary_band = (payload.get("studentProfile", {}) or {}).get("expectedSalaryBand", "")
    else:
        pro = payload.get("proProfile", {}) or {}
        fam = TRACK_TO_FAMILY.get(pro.get("track", ""), "other")
        wb = _workexp_bin(pro.get("years", ""))
        emp = "employed"
        is_market_ref = False
        salary_band = pro.get("salaryBand", "")

    # ===== Salary benchmark (fallback)
    bench, level_used = _bench_lookup_with_fallback(bench_l1, bench_l2, bench_l3, bench_l4, emp, wb, fam)

    # 构建薪资数据结构
    salary_data: Optional[Dict[str, Any]] = None
    if bench is not None:
        n = int(bench["n"])
        p25_usd, p50_usd, p75_usd, p90_usd = float(bench["p25"]), float(bench["p50"]), float(bench["p75"]), float(bench["p90"])

        # 解析用户薪资区间
        user_salary_band_data: Optional[Dict[str, Any]] = None
        if salary_band:
            lo_cny, hi_cny = _parse_salary_band_cny(salary_band)
            user_salary_band_data = {
                "text": salary_band,
                "loCny": lo_cny,
                "hiCny": hi_cny,
                "loUsd": _cny_to_usd(lo_cny) if lo_cny is not None else None,
                "hiUsd": _cny_to_usd(hi_cny) if hi_cny is not None else None,
            }

        salary_data = {
            "currency": "CNY",
            "fx": FX_LABEL,
            "level": level_used,
            "n": n,
            "confidence": _confidence(n),
            "minN": MIN_N,
            "isMarketRef": is_market_ref,
            "p25Usd": p25_usd,
            "p50Usd": p50_usd,
            "p75Usd": p75_usd,
            "p90Usd": p90_usd,
            "p25": _usd_to_cny(p25_usd),
            "p50": _usd_to_cny(p50_usd),
            "p75": _usd_to_cny(p75_usd),
            "p90": _usd_to_cny(p90_usd),
            "userSalaryBand": user_salary_band_data,
        }

    # ===== Tech trends (fallback cohort)
    sel_lang_set = set([s.strip() for s in sel_lang if str(s).strip()])
    sel_db_set = set([s.strip() for s in sel_db if str(s).strip()])
    sel_web_set = set([s.strip() for s in sel_web if str(s).strip()])
    sel_platform_set = set([s.strip() for s in sel_platform if str(s).strip()])

    lang_cohort, lang_lvl, lang_n = _trend_build_cohort_with_fallback(lang_df, wb, fam, min_n=MIN_N)
    db_cohort, db_lvl, db_n = _trend_build_cohort_with_fallback(db_df, wb, fam, min_n=MIN_N)
    web_cohort, web_lvl, web_n = _trend_build_cohort_with_fallback(web_df, wb, fam, min_n=MIN_N)
    platform_cohort, platform_lvl, platform_n = _trend_build_cohort_with_fallback(platform_df, wb, fam, min_n=MIN_N)

    # ===== 辅助函数：将文本行解析为结构化数据
    def _parse_reco_line(line: str) -> Optional[Dict[str, Any]]:
        # - React（gap +12.3%，want 30.0% vs have 17.7%）
        s = (line or "").strip().lstrip("-").strip()
        m = re.search(r"^(.*?)（gap\s*([+\-]?\d+(?:\.\d+)?)%.*?want\s*(\d+(?:\.\d+)?)%\s*vs\s*have\s*(\d+(?:\.\d+)?)%）$", s)
        if not m:
            return None
        tech = m.group(1).strip()
        gap = float(m.group(2)) / 100.0
        want = float(m.group(3)) / 100.0
        have = float(m.group(4)) / 100.0
        return {"tech": tech, "gap": gap, "want": want, "have": have}

    def _parse_have_line(line: str) -> Optional[Dict[str, Any]]:
        # - Python（在该统计口径中 have≈12.3%）
        s = (line or "").strip().lstrip("-").strip()
        m = re.search(r"^(.*?)（在该统计口径中 have≈(\d+(?:\.\d+)?)%）$", s)
        if not m:
            return None
        return {"tech": m.group(1).strip(), "have": float(m.group(2)) / 100.0}

    # ===== Two-stage recommendations: mainstream + gap
    # 收集推荐系统指标
    reco_metrics = {}

    # language
    lang_main_lines, lang_main_thr, lang_main_metrics = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="mainstream"
    )
    lang_gap_lines, lang_gap_thr, lang_gap_metrics = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="gap"
    )
    reco_metrics["language"] = {"mainstream": lang_main_metrics, "gap": lang_gap_metrics}

    # database
    db_main_lines, db_main_thr, db_main_metrics = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="mainstream"
    )
    db_gap_lines, db_gap_thr, db_gap_metrics = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="gap"
    )
    reco_metrics["database"] = {"mainstream": db_main_metrics, "gap": db_gap_metrics}

    # webframe
    web_main_lines, web_main_thr, web_main_metrics = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="mainstream"
    )
    web_gap_lines, web_gap_thr, web_gap_metrics = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="gap"
    )
    reco_metrics["webframe"] = {"mainstream": web_main_metrics, "gap": web_gap_metrics}

    # platform
    platform_main_lines, platform_main_thr, platform_main_metrics = _trend_pick_recos(
        platform_cohort, sel_platform_set, 3, base_min_want_rate=PLATFORM_MIN_WANT, mode="mainstream"
    )
    platform_gap_lines, platform_gap_thr, platform_gap_metrics = _trend_pick_recos(
        platform_cohort, sel_platform_set, 3, base_min_want_rate=PLATFORM_MIN_WANT, mode="gap"
    )
    reco_metrics["platform"] = {"mainstream": platform_main_metrics, "gap": platform_gap_metrics}

    chosen_lang_lines = _trend_pick_chosen_popularity(lang_cohort, sel_lang_set, limit_n=3)
    chosen_db_lines = _trend_pick_chosen_popularity(db_cohort, sel_db_set, limit_n=3)
    chosen_web_lines = _trend_pick_chosen_popularity(web_cohort, sel_web_set, limit_n=3)
    chosen_platform_lines = _trend_pick_chosen_popularity(platform_cohort, sel_platform_set, limit_n=3)

    # 解析为结构化数据
    lang_main_items = [x for x in (_parse_reco_line(l) for l in (lang_main_lines or [])) if x]
    lang_gap_items = [x for x in (_parse_reco_line(l) for l in (lang_gap_lines or [])) if x]
    chosen_lang_items = [x for x in (_parse_have_line(l) for l in (chosen_lang_lines or [])) if x]

    db_main_items = [x for x in (_parse_reco_line(l) for l in (db_main_lines or [])) if x]
    db_gap_items = [x for x in (_parse_reco_line(l) for l in (db_gap_lines or [])) if x]
    chosen_db_items = [x for x in (_parse_have_line(l) for l in (chosen_db_lines or [])) if x]

    web_main_items = [x for x in (_parse_reco_line(l) for l in (web_main_lines or [])) if x]
    web_gap_items = [x for x in (_parse_reco_line(l) for l in (web_gap_lines or [])) if x]
    chosen_web_items = [x for x in (_parse_have_line(l) for l in (chosen_web_lines or [])) if x]

    platform_main_items = [x for x in (_parse_reco_line(l) for l in (platform_main_lines or [])) if x]
    platform_gap_items = [x for x in (_parse_reco_line(l) for l in (platform_gap_lines or [])) if x]
    chosen_platform_items = [x for x in (_parse_have_line(l) for l in (chosen_platform_lines or [])) if x]

    # 构建技术栈数据结构
    tech_data = {
        "cohort": {
            "workexpBin": wb,
            "devtypeFamily": fam,
            "levels": {
                "language": lang_lvl,
                "database": db_lvl,
                "webframe": web_lvl,
                "platform": platform_lvl
            },
            "nUsed": {
                "language": int(lang_n),
                "database": int(db_n),
                "webframe": int(web_n),
                "platform": int(platform_n)
            },
        },
        "thresholds": {
            "language": {
                "baseMinWant": LANG_MIN_WANT,
                "mainstreamUsedThr": lang_main_thr,
                "gapUsedThr": lang_gap_thr,
            },
            "database": {
                "baseMinWant": DB_MIN_WANT,
                "mainstreamUsedThr": db_main_thr,
                "gapUsedThr": db_gap_thr,
            },
            "webframe": {
                "baseMinWant": WEB_MIN_WANT,
                "mainstreamUsedThr": web_main_thr,
                "gapUsedThr": web_gap_thr,
            },
            "platform": {
                "baseMinWant": PLATFORM_MIN_WANT,
                "mainstreamUsedThr": platform_main_thr,
                "gapUsedThr": platform_gap_thr,
            },
        },
        "language": {
            "mainstream": lang_main_items,
            "gap": lang_gap_items,
            "chosen": chosen_lang_items,
        },
        "database": {
            "mainstream": db_main_items,
            "gap": db_gap_items,
            "chosen": chosen_db_items,
        },
        "webframe": {
            "mainstream": web_main_items,
            "gap": web_gap_items,
            "chosen": chosen_web_items,
        },
        "platform": {
            "mainstream": platform_main_items,
            "gap": platform_gap_items,
            "chosen": chosen_platform_items,
        },
    }

    # ===== 进阶建议：查询进阶人群的技术画像
    advancement_data: Optional[Dict[str, Any]] = None
    advancement_metrics: Dict[str, Any] = {"available": False}
    target_wb = WORKEXP_ADVANCEMENT.get(wb)

    if target_wb is not None:
        # 查询进阶人群的技术趋势
        adv_lang_cohort, adv_lang_lvl, adv_lang_n = _trend_build_cohort_with_fallback(
            lang_df, target_wb, fam, min_n=MIN_N
        )
        adv_db_cohort, adv_db_lvl, adv_db_n = _trend_build_cohort_with_fallback(
            db_df, target_wb, fam, min_n=MIN_N
        )
        adv_web_cohort, adv_web_lvl, adv_web_n = _trend_build_cohort_with_fallback(
            web_df, target_wb, fam, min_n=MIN_N
        )
        adv_platform_cohort, adv_platform_lvl, adv_platform_n = _trend_build_cohort_with_fallback(
            platform_df, target_wb, fam, min_n=MIN_N
        )

        def _compute_advancement_items(
            current_cohort: Optional[DataFrame],
            target_cohort: Optional[DataFrame],
            selected_set: set,
            top_k: int = 2,
        ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
            """计算进阶增益：找出进阶人群中更普及但用户未选的技术
            返回：(推荐项列表, 指标)
            """
            metrics = {
                "total_target_tech": 0,
                "candidates_after_exclude": 0,
                "candidates_above_threshold": 0,
                "final_reco_count": 0,
                "avg_lift": 0.0,
            }

            if current_cohort is None or target_cohort is None:
                metrics["status"] = "no_cohort_data"
                return [], metrics

            # 获取当前人群和进阶人群的 have_rate
            current_rows = current_cohort.select("tech", "have_rate").collect()
            target_rows = target_cohort.select("tech", "have_rate").collect()

            current_map = {r["tech"]: float(r["have_rate"]) for r in current_rows}
            target_map = {r["tech"]: float(r["have_rate"]) for r in target_rows}

            metrics["total_target_tech"] = len(target_map)

            # 计算增益
            candidates = []
            excluded_count = 0
            for tech, target_have in target_map.items():
                # 跳过用户已选的技术
                if tech in selected_set:
                    excluded_count += 1
                    continue
                # 进阶人群 have_rate 必须达到最低门槛
                if target_have < ADV_MIN_TARGET_HAVE:
                    continue
                current_have = current_map.get(tech, 0.0)
                lift = target_have - current_have
                # 增益必须达到最低门槛
                if lift < ADV_MIN_LIFT:
                    continue
                candidates.append({
                    "tech": tech,
                    "currentHave": current_have,
                    "targetHave": target_have,
                    "lift": lift,
                })

            metrics["candidates_after_exclude"] = len(target_map) - excluded_count
            metrics["candidates_above_threshold"] = len(candidates)

            # 按增益降序排序，取 top_k
            candidates.sort(key=lambda x: x["lift"], reverse=True)
            result = candidates[:top_k]

            metrics["final_reco_count"] = len(result)
            if result:
                metrics["avg_lift"] = sum(c["lift"] for c in result) / len(result)
            metrics["status"] = "success"

            return result, metrics

        adv_lang_items, adv_lang_metrics = _compute_advancement_items(lang_cohort, adv_lang_cohort, sel_lang_set, top_k=2)
        adv_db_items, adv_db_metrics = _compute_advancement_items(db_cohort, adv_db_cohort, sel_db_set, top_k=2)
        adv_web_items, adv_web_metrics = _compute_advancement_items(web_cohort, adv_web_cohort, sel_web_set, top_k=2)
        adv_platform_items, adv_platform_metrics = _compute_advancement_items(platform_cohort, adv_platform_cohort, sel_platform_set, top_k=2)

        # 只有当有推荐项时才返回进阶数据
        has_any_advancement = bool(adv_lang_items or adv_db_items or adv_web_items or adv_platform_items)

        advancement_data = {
            "currentLevel": wb,
            "targetLevel": target_wb,
            "available": has_any_advancement,
            "language": adv_lang_items,
            "database": adv_db_items,
            "webframe": adv_web_items,
            "platform": adv_platform_items,
        }

        advancement_metrics = {
            "available": True,
            "currentLevel": wb,
            "targetLevel": target_wb,
            "language": adv_lang_metrics,
            "database": adv_db_metrics,
            "webframe": adv_web_metrics,
            "platform": adv_platform_metrics,
        }

    # ===== 高薪vs低薪技术差异分析
    salary_tier_tech_data: Optional[Dict[str, Any]] = None
    salary_tier_metrics: Dict[str, Any] = {"available": False}

    def _compute_salary_tier_diff(
        tier_df: Optional[DataFrame],
        fam: str,
        selected_set: set,
        top_k: int = 3,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        计算高薪人群vs低薪人群的技术差异
        返回：(用户缺失的推荐技术列表, 用户已有的技术列表, 指标)
        """
        metrics = {
            "available": False,
            "total_high_tech": 0,
            "total_low_tech": 0,
            "candidates_above_threshold": 0,
            "user_missing_count": 0,
            "user_has_count": 0,
            "avg_diff": 0.0,
        }

        if tier_df is None:
            metrics["reason"] = "数据表未加载"
            return [], [], metrics

        # 按 devtype_family 筛选
        filtered = tier_df.where(F.col("devtype_family") == fam)

        # 获取高薪人群和低薪人群的技术数据
        high_rows = filtered.where(F.col("salary_tier") == "high").select("tech", "have_rate", "n").collect()
        low_rows = filtered.where(F.col("salary_tier") == "low").select("tech", "have_rate", "n").collect()

        fallback_used = False
        if not high_rows or not low_rows:
            # 尝试回退到全局数据
            fallback_used = True
            filtered = tier_df
            high_rows = filtered.where(F.col("salary_tier") == "high").select("tech", "have_rate", "n").collect()
            low_rows = filtered.where(F.col("salary_tier") == "low").select("tech", "have_rate", "n").collect()

            if not high_rows or not low_rows:
                metrics["reason"] = "高薪或低薪人群数据不足"
                return [], [], metrics

        high_map = {r["tech"]: float(r["have_rate"]) for r in high_rows}
        low_map = {r["tech"]: float(r["have_rate"]) for r in low_rows}

        metrics["total_high_tech"] = len(high_map)
        metrics["total_low_tech"] = len(low_map)
        metrics["fallback_to_global"] = fallback_used

        # 获取样本量信息
        high_n = int(high_rows[0]["n"]) if high_rows else 0
        low_n = int(low_rows[0]["n"]) if low_rows else 0
        metrics["highN"] = high_n
        metrics["lowN"] = low_n

        # 计算差异：高薪人群 have_rate 比低薪人群高的技术
        candidates = []
        for tech, high_have in high_map.items():
            low_have = low_map.get(tech, 0.0)
            diff = high_have - low_have

            # 筛选条件：
            # 1. 高薪人群 have_rate 达到门槛
            # 2. 差异达到门槛
            # 3. 用户未选择该技术
            if high_have >= SALARY_TIER_MIN_HIGH_HAVE and diff >= SALARY_TIER_MIN_DIFF:
                candidates.append({
                    "tech": tech,
                    "highHave": high_have,
                    "lowHave": low_have,
                    "diff": diff,
                    "userHas": tech in selected_set,
                })

        metrics["candidates_above_threshold"] = len(candidates)

        # 按差异降序排序
        candidates.sort(key=lambda x: x["diff"], reverse=True)

        # 分离用户已有和未有的技术
        user_missing = [c for c in candidates if not c["userHas"]][:top_k]
        user_has = [c for c in candidates if c["userHas"]][:top_k]

        metrics["user_missing_count"] = len(user_missing)
        metrics["user_has_count"] = len(user_has)
        if candidates:
            metrics["avg_diff"] = sum(c["diff"] for c in candidates) / len(candidates)
        metrics["available"] = True
        metrics["devtypeFamily"] = fam

        return user_missing, user_has, metrics

    # 只有当薪资分层表存在时才计算
    if lang_salary_tier_df is not None or db_salary_tier_df is not None or web_salary_tier_df is not None or platform_salary_tier_df is not None:
        lang_missing, lang_has, lang_tier_metrics = _compute_salary_tier_diff(
            lang_salary_tier_df, fam, sel_lang_set, top_k=3
        ) if lang_salary_tier_df is not None else ([], [], {"available": False})

        db_missing, db_has, db_tier_metrics = _compute_salary_tier_diff(
            db_salary_tier_df, fam, sel_db_set, top_k=3
        ) if db_salary_tier_df is not None else ([], [], {"available": False})

        web_missing, web_has, web_tier_metrics = _compute_salary_tier_diff(
            web_salary_tier_df, fam, sel_web_set, top_k=3
        ) if web_salary_tier_df is not None else ([], [], {"available": False})

        platform_missing, platform_has, platform_tier_metrics = _compute_salary_tier_diff(
            platform_salary_tier_df, fam, sel_platform_set, top_k=3
        ) if platform_salary_tier_df is not None else ([], [], {"available": False})

        has_any_diff = bool(lang_missing or db_missing or web_missing or platform_missing)

        salary_tier_tech_data = {
            "available": has_any_diff,
            "devtypeFamily": fam,
            "language": {
                "missing": lang_missing,
                "has": lang_has,
                "meta": lang_tier_metrics,
            },
            "database": {
                "missing": db_missing,
                "has": db_has,
                "meta": db_tier_metrics,
            },
            "webframe": {
                "missing": web_missing,
                "has": web_has,
                "meta": web_tier_metrics,
            },
            "platform": {
                "missing": platform_missing,
                "has": platform_has,
                "meta": platform_tier_metrics,
            },
        }

        salary_tier_metrics = {
            "available": True,
            "language": lang_tier_metrics,
            "database": db_tier_metrics,
            "webframe": web_tier_metrics,
            "platform": platform_tier_metrics,
        }

    # ===== 汇总所有指标
    all_metrics = {
        "timestamp": datetime.now().isoformat(),
        "userProfile": {
            "profileType": profile_type,
            "workexpBin": wb,
            "devtypeFamily": fam,
        },
        "salaryBenchmark": {
            "level": level_used,
            "sampleSize": int(bench["n"]) if bench else 0,
            "confidence": _confidence(int(bench["n"])) if bench else "无数据",
        },
        "trendCohort": {
            "language": {"level": lang_lvl, "sampleSize": int(lang_n)},
            "database": {"level": db_lvl, "sampleSize": int(db_n)},
            "webframe": {"level": web_lvl, "sampleSize": int(web_n)},
            "platform": {"level": platform_lvl, "sampleSize": int(platform_n)},
        },
        "recommendation": reco_metrics,
        "advancement": advancement_metrics,
        "salaryTierDiff": salary_tier_metrics,
    }

    # 保存指标到本地文件
    metrics_file = _save_metrics_to_file(all_metrics)

    # 加载 Gold 元数据
    gold_metadata = _load_gold_metadata()

    # 返回纯数据结构（包含指标）
    return {
        "userProfile": {
            "profileType": profile_type,
            "workexpBin": wb,
            "devtypeFamily": fam,
            "track": track if profile_type == "student" else (payload.get("proProfile", {}) or {}).get("track", ""),
        },
        "salary": salary_data,
        "tech": tech_data,
        "advancement": advancement_data,
        "salaryTierTech": salary_tier_tech_data,
        "metrics": all_metrics,
        "metricsFile": metrics_file,
        "goldMetadata": gold_metadata,
    }
