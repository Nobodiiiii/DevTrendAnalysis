from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame, functions as F

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

# =========================
# Global knobs
# =========================

# ✅ FX：USD 内部计算，CNY 展示
FX_USD_TO_CNY = 7.06
FX_LABEL = f"1 USD ≈ {FX_USD_TO_CNY} CNY"

# ✅ 回退阈值：低于该 n 自动回退到更粗粒度（薪资 & 栈建议共用）
MIN_N = 200

# ✅ “绝对需求门槛”——防止小众项被 gap 顶上来
# 你可以后面调参：想更“稳”就提高，想更“探索”就降低
LANG_MIN_WANT = 0.08  # 语言：至少 8% 想用
WEB_MIN_WANT = 0.08  # 框架：至少 8% 想用
DB_MIN_WANT = 0.05  # 数据库：至少 5% 想用

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


def _ensure_tables() -> Tuple[
    SparkSession, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame]:
    global _spark, _bench_l1, _bench_l2, _bench_l3, _bench_l4
    global _lang_trend_df, _db_trend_df, _web_trend_df

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

    return _spark, _bench_l1, _bench_l2, _bench_l3, _bench_l4, _lang_trend_df, _db_trend_df, _web_trend_df


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
) -> Tuple[List[str], float]:
    """
    两种推荐：
      - mainstream: 按 want_rate 排（先补主流地基）
      - gap: 按 gap 排（潜力加分，但仍受 want_rate 门槛约束）
    为避免空结果：min_want_rate 会按 RELAX_FACTORS 自动降档。
    返回：lines, used_min_want_rate
    """
    if cohort_df is None:
        return [], base_min_want_rate

    df = cohort_df
    if selected_set:
        df = df.where(~F.col("tech").isin(list(selected_set)))

    # 逐级放宽阈值，直到拿到结果
    for factor in RELAX_FACTORS:
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
            return out, thr

    return [], base_min_want_rate


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
    _, bench_l1, bench_l2, bench_l3, bench_l4, lang_df, db_df, web_df = _ensure_tables()

    tech = payload.get("techStack", {}) or {}
    sel_lang = tech.get("languages", []) or []
    sel_db = tech.get("databases", []) or []
    sel_web = tech.get("webframes", []) or []

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

    lang_cohort, lang_lvl, lang_n = _trend_build_cohort_with_fallback(lang_df, wb, fam, min_n=MIN_N)
    db_cohort, db_lvl, db_n = _trend_build_cohort_with_fallback(db_df, wb, fam, min_n=MIN_N)
    web_cohort, web_lvl, web_n = _trend_build_cohort_with_fallback(web_df, wb, fam, min_n=MIN_N)

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
    # language
    lang_main_lines, lang_main_thr = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="mainstream"
    )
    lang_gap_lines, lang_gap_thr = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="gap"
    )

    # database
    db_main_lines, db_main_thr = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="mainstream"
    )
    db_gap_lines, db_gap_thr = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="gap"
    )

    # webframe
    web_main_lines, web_main_thr = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="mainstream"
    )
    web_gap_lines, web_gap_thr = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="gap"
    )

    chosen_lang_lines = _trend_pick_chosen_popularity(lang_cohort, sel_lang_set, limit_n=3)
    chosen_db_lines = _trend_pick_chosen_popularity(db_cohort, sel_db_set, limit_n=3)
    chosen_web_lines = _trend_pick_chosen_popularity(web_cohort, sel_web_set, limit_n=3)

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

    # 构建技术栈数据结构
    tech_data = {
        "cohort": {
            "workexpBin": wb,
            "devtypeFamily": fam,
            "levels": {
                "language": lang_lvl,
                "database": db_lvl,
                "webframe": web_lvl
            },
            "nUsed": {
                "language": int(lang_n),
                "database": int(db_n),
                "webframe": int(web_n)
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
    }

    # 返回纯数据结构
    return {
        "userProfile": {
            "profileType": profile_type,
            "workexpBin": wb,
            "devtypeFamily": fam,
            "track": track if profile_type == "student" else (payload.get("proProfile", {}) or {}).get("track", ""),
        },
        "salary": salary_data,
        "tech": tech_data,
    }
