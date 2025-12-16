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
LANG_MIN_WANT = 0.08   # 语言：至少 8% 想用
WEB_MIN_WANT = 0.08    # 框架：至少 8% 想用
DB_MIN_WANT = 0.05     # 数据库：至少 5% 想用

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


def _ensure_tables() -> Tuple[SparkSession, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame]:
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

def generate_advice(payload: Dict[str, Any]) -> Dict[str, str]:
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

    salary_lines: List[str] = []
    salary_lines.append(f"汇率口径：{FX_LABEL}（后端内部用 USD 计算，展示换算成人民币）")
    salary_lines.append(f"薪资分位对标回退：若样本量 n < {MIN_N} 自动回退到更粗粒度。")

    if bench is None:
        salary_lines.append("薪资基准未命中（Gold 可能未生成或数据异常）。")
    else:
        n = int(bench["n"])
        p25_usd, p50_usd, p75_usd, p90_usd = float(bench["p25"]), float(bench["p50"]), float(bench["p75"]), float(bench["p90"])

        salary_lines.append(
            f"**薪资对标（ConvertedCompYearly）**："
            f"P25≈{_fmt_cny_from_usd(p25_usd)}，"
            f"P50≈{_fmt_cny_from_usd(p50_usd)}，"
            f"P75≈{_fmt_cny_from_usd(p75_usd)}，"
            f"P90≈{_fmt_cny_from_usd(p90_usd)}（人民币/年）"
        )
        salary_lines.append(f"**对标粒度**：{level_used}；样本量 n={n}（可信度：{_confidence(n)}）")

        if is_market_ref:
            salary_lines.append("说明：你当前为学生，这里用“入门在职人群”的分位数做市场参考（非对你当前收入的判断）。")

        if salary_band:
            lo_cny, hi_cny = _parse_salary_band_cny(salary_band)
            salary_lines.append(f"你填写的薪资区间（人民币/年）：{salary_band}")
            if lo_cny is not None or hi_cny is not None:
                lo_usd = _cny_to_usd(lo_cny) if lo_cny is not None else None
                hi_usd = _cny_to_usd(hi_cny) if hi_cny is not None else None

                def _pos_hint() -> str:
                    if hi_usd is not None and hi_usd <= p25_usd:
                        return "该区间上沿偏低于 P25（更偏保守）。"
                    if lo_usd is not None and lo_usd >= p75_usd:
                        return "该区间下沿已接近/高于 P75（更偏进取）。"
                    if lo_usd is not None and hi_usd is not None:
                        if hi_usd <= p50_usd:
                            return "该区间主要落在 P50 以下。"
                        if lo_usd >= p50_usd:
                            return "该区间主要落在 P50 以上。"
                    return "该区间与 P50/P75 存在重叠，取决于项目深度与匹配度。"

                salary_lines.append(f"对齐提示：{_pos_hint()}")

    # ===== Tech trends (fallback cohort)
    sel_lang_set = set([s.strip() for s in sel_lang if str(s).strip()])
    sel_db_set = set([s.strip() for s in sel_db if str(s).strip()])
    sel_web_set = set([s.strip() for s in sel_web if str(s).strip()])

    lang_cohort, lang_lvl, lang_n = _trend_build_cohort_with_fallback(lang_df, wb, fam, min_n=MIN_N)
    db_cohort, db_lvl, db_n = _trend_build_cohort_with_fallback(db_df, wb, fam, min_n=MIN_N)
    web_cohort, web_lvl, web_n = _trend_build_cohort_with_fallback(web_df, wb, fam, min_n=MIN_N)

    # ===== Two-stage recommendations: mainstream + gap
    # language
    lang_main, lang_main_thr = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="mainstream"
    )
    lang_gap, lang_gap_thr = _trend_pick_recos(
        lang_cohort, sel_lang_set, 3, base_min_want_rate=LANG_MIN_WANT, mode="gap"
    )

    # database
    db_main, db_main_thr = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="mainstream"
    )
    db_gap, db_gap_thr = _trend_pick_recos(
        db_cohort, sel_db_set, 3, base_min_want_rate=DB_MIN_WANT, mode="gap"
    )

    # webframe
    web_main, web_main_thr = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="mainstream"
    )
    web_gap, web_gap_thr = _trend_pick_recos(
        web_cohort, sel_web_set, 3, base_min_want_rate=WEB_MIN_WANT, mode="gap"
    )

    chosen_lang = _trend_pick_chosen_popularity(lang_cohort, sel_lang_set, limit_n=3)
    chosen_db = _trend_pick_chosen_popularity(db_cohort, sel_db_set, limit_n=3)
    chosen_web = _trend_pick_chosen_popularity(web_cohort, sel_web_set, limit_n=3)

    # ===== Build stack text
    stack_lines: List[str] = []
    stack_lines.append("**开发栈建议（两段式：先主流地基，再潜力加分）**：")
    stack_lines.append(
        f"（栈建议回退：语言={lang_lvl}/n≈{lang_n}；数据库={db_lvl}/n≈{db_n}；框架={web_lvl}/n≈{web_n}）"
    )

    def _thr_note(base_thr: float, used_thr: float) -> str:
        if used_thr >= base_thr - 1e-9:
            return f"（want≥{base_thr:.0%}）"
        if used_thr <= 1e-9:
            return f"（want 门槛已放宽）"
        return f"（want≥{used_thr:.0%}，原阈值 {base_thr:.0%}）"

    # 语言
    if lang_main:
        stack_lines.append(f"\n语言 · 主流地基 {_thr_note(LANG_MIN_WANT, lang_main_thr)}")
        stack_lines.extend(lang_main)
    if lang_gap:
        stack_lines.append(f"\n语言 · 潜力加分 {_thr_note(LANG_MIN_WANT, lang_gap_thr)}")
        stack_lines.extend(lang_gap)

    # 数据库
    if db_main:
        stack_lines.append(f"\n数据库 · 主流地基 {_thr_note(DB_MIN_WANT, db_main_thr)}")
        stack_lines.extend(db_main)
    if db_gap:
        stack_lines.append(f"\n数据库 · 潜力加分 {_thr_note(DB_MIN_WANT, db_gap_thr)}")
        stack_lines.extend(db_gap)

    # 框架
    if web_main:
        stack_lines.append(f"\n框架/平台 · 主流地基 {_thr_note(WEB_MIN_WANT, web_main_thr)}")
        stack_lines.extend(web_main)
    if web_gap:
        stack_lines.append(f"\n框架/平台 · 潜力加分 {_thr_note(WEB_MIN_WANT, web_gap_thr)}")
        stack_lines.extend(web_gap)

    if not (lang_main or lang_gap or db_main or db_gap or web_main or web_gap):
        stack_lines.append(
            "\n（当前统计口径下没有稳定可推荐项：要么你已选覆盖了主要技术，要么 cohort 太分散。建议直接对齐目标岗位 JD，补齐 1 个主栈 + 1 个数据库 + 1 个框架的项目闭环。）"
        )

    have_lines: List[str] = []
    if chosen_lang or chosen_db or chosen_web:
        have_lines.append("\n**你已选择的栈在统计口径中的普及度（have_rate 参考）**：")
        if chosen_lang:
            have_lines.append("语言")
            have_lines.extend(chosen_lang)
        if chosen_db:
            have_lines.append("数据库")
            have_lines.extend(chosen_db)
        if chosen_web:
            have_lines.append("框架/平台")
            have_lines.extend(chosen_web)

    # ===== analysisNote
    analysis_parts: List[str] = []
    analysis_parts.extend(salary_lines)
    analysis_parts.append("")
    analysis_parts.extend(stack_lines)
    if have_lines:
        analysis_parts.extend(have_lines)

    # ===== aiSummary
    ai_parts: List[str] = []
    ai_parts.append("**下一步行动建议**：")

    if bench is not None:
        p50_usd = float(bench["p50"])
        p75_usd = float(bench["p75"])
        ai_parts.append(
            f"- 目标薪资建议（人民币/年，按 {FX_LABEL}）：先对齐 P50≈{_fmt_cny_from_usd(p50_usd)}，再冲刺 P75≈{_fmt_cny_from_usd(p75_usd)}。"
        )

    ai_parts.append("- 先把“主流地基”补齐成可讲的闭环项目（能解释：选型理由、权衡、上线结果）。")
    ai_parts.append("- 再挑 1 个“潜力加分”技术做深入（否则会变成到处沾一点但讲不深）。")
    ai_parts.append("- 简历/面试表达：用 STAR/问题-方案-结果讲清楚你解决过的具体问题，并量化结果。")

    return {
        "analysisNote": "\n".join([x for x in analysis_parts if x is not None]),
        "aiSummary": "\n".join(ai_parts),
    }
