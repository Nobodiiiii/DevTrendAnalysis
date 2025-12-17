from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame, functions as F

GOLD_BENCH_BASE = "hdfs:///advice/gold/2025/salary_benchmark_base"
GOLD_UPLIFT_BASE = "hdfs:///advice/gold/2025/uplift_to_p75_base"
GOLD_TREND_LANG = "hdfs:///advice/gold/2025/tech_trends_language"
GOLD_TREND_DB = "hdfs:///advice/gold/2025/tech_trends_database"
GOLD_TREND_WEB = "hdfs:///advice/gold/2025/tech_trends_webframe"

# ✅ 简单汇率：后端用 USD 处理，输出统一换算成人民币展示
FX_USD_TO_CNY = 7.06  # 你可改成配置项/表
FX_LABEL = f"1 USD ≈ {FX_USD_TO_CNY} CNY"

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

_lock = threading.Lock()
_spark: Optional[SparkSession] = None
_bench_df: Optional[DataFrame] = None
_uplift_df: Optional[DataFrame] = None
_lang_trend_df: Optional[DataFrame] = None
_db_trend_df: Optional[DataFrame] = None
_web_trend_df: Optional[DataFrame] = None


def _ensure_tables() -> Tuple[SparkSession, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame]:
    global _spark, _bench_df, _uplift_df, _lang_trend_df, _db_trend_df, _web_trend_df

    with _lock:
        if _spark is None:
            _spark = SparkSession.builder.appName("devtrend-advice-service").getOrCreate()

        if _bench_df is None:
            _bench_df = _spark.read.parquet(GOLD_BENCH_BASE).cache()
        if _uplift_df is None:
            _uplift_df = _spark.read.parquet(GOLD_UPLIFT_BASE).cache()

        if _lang_trend_df is None:
            _lang_trend_df = _spark.read.parquet(GOLD_TREND_LANG).cache()
        if _db_trend_df is None:
            _db_trend_df = _spark.read.parquet(GOLD_TREND_DB).cache()
        if _web_trend_df is None:
            _web_trend_df = _spark.read.parquet(GOLD_TREND_WEB).cache()

    return _spark, _bench_df, _uplift_df, _lang_trend_df, _db_trend_df, _web_trend_df


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
    # 人民币整数展示
    return f"¥{_usd_to_cny(x_usd):,.0f}"


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

    # 统一横杠：– —
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

    # 兜底：提取第一个数字万
    m_any = re.search(r"(\d+)\s*万", b)
    if m_any:
        v = float(m_any.group(1)) * 10000
        return v, None

    return None, None


def _cny_to_usd(x_cny: float) -> float:
    return float(x_cny) / FX_USD_TO_CNY


def _pick_uplift_lines(rows: List[Dict[str, Any]]) -> List[str]:
    cand = [r for r in rows if (r.get("n_high") or 0) >= 30]
    cand.sort(key=lambda r: r.get("uplift", 0.0), reverse=True)
    out = []
    for r in cand[:3]:
        out.append(f"- 高薪组更常见：{r['feature_name']} = {r['feature_value']}（uplift {r['uplift']:+.1%}）")
    return out


def _bench_lookup(bench_df: DataFrame, emp: str, wb: str, fam: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    row = (
        bench_df.where(
            (F.col("employment_std") == emp)
            & (F.col("workexp_bin") == wb)
            & (F.col("devtype_family") == fam)
        )
        .limit(1)
        .collect()
    )
    if row:
        return row[0].asDict(), False

    row = (
        bench_df.where(
            (F.col("employment_std") == emp)
            & (F.col("workexp_bin") == wb)
            & (F.col("devtype_family") == "other")
        )
        .limit(1)
        .collect()
    )
    if row:
        return row[0].asDict(), True

    if wb == "unknown":
        row = (
            bench_df.where(
                (F.col("employment_std") == emp)
                & (F.col("workexp_bin") == "4-6")
                & (F.col("devtype_family") == fam)
            )
            .limit(1)
            .collect()
        )
        if row:
            return row[0].asDict(), True

    return None, True


def _trend_reco(
    trend_df: DataFrame,
    wb: str,
    fam: str,
    selected: List[str],
    top_k: int = 3,
    min_n: int = 80,
) -> Tuple[List[str], List[str]]:
    selected_set = set([s.strip() for s in selected if str(s).strip()])

    cohort = trend_df.where(
        (F.col("workexp_bin") == wb) & (F.col("devtype_family") == fam) & (F.col("n") >= min_n)
    )

    reco_rows = (
        cohort.where(~F.col("tech").isin(list(selected_set)) if selected_set else F.lit(True))
        .orderBy(F.col("gap").desc(), F.col("want_rate").desc())
        .limit(top_k)
        .collect()
    )

    reco_lines = []
    for r in reco_rows:
        d = r.asDict()
        reco_lines.append(
            f"- {d['tech']}（gap {float(d['gap']):+.1%}，want {float(d['want_rate']):.1%} vs have {float(d['have_rate']):.1%}）"
        )

    chosen_lines = []
    if selected_set:
        chosen_rows = (
            cohort.where(F.col("tech").isin(list(selected_set)))
            .orderBy(F.col("have_rate").desc())
            .limit(3)
            .collect()
        )
        for r in chosen_rows:
            d = r.asDict()
            chosen_lines.append(f"- {d['tech']}（在该 cohort 中 have≈{float(d['have_rate']):.1%}）")

    return reco_lines, chosen_lines


def generate_advice(payload: Dict[str, Any]) -> Dict[str, str]:
    _, bench_df, uplift_df, lang_df, db_df, web_df = _ensure_tables()

    tech = payload.get("techStack", {}) or {}
    sel_lang = tech.get("languages", []) or []
    sel_db = tech.get("databases", []) or []
    sel_web = tech.get("webframes", []) or []

    profile_type = payload.get("profileType", "")

    if profile_type == "student":
        track = (payload.get("studentProfile", {}) or {}).get("expectedTrack", "")
        fam = TRACK_TO_FAMILY.get(track, "other")
        wb = "0-1"
        emp = "employed"  # 市场参考人群
        is_market_ref = True
        salary_band = (payload.get("studentProfile", {}) or {}).get("expectedSalaryBand", "")
    else:
        pro = payload.get("proProfile", {}) or {}
        fam = TRACK_TO_FAMILY.get(pro.get("track", ""), "other")
        wb = _workexp_bin(pro.get("years", ""))
        emp = "employed"
        is_market_ref = False
        salary_band = pro.get("salaryBand", "")

    bench, fallback_used = _bench_lookup(bench_df, emp, wb, fam)

    # ===== Salary (USD internal, CNY display)
    salary_lines: List[str] = []
    salary_lines.append(f"汇率口径：{FX_LABEL}（后端内部用 USD 计算，前端展示换算后的人民币）")

    if bench is None:
        salary_lines.append("薪资基准未命中（Gold 可能未生成或 cohort 太稀）。")
    else:
        n = int(bench["n"])
        p25_usd, p50_usd, p75_usd, p90_usd = float(bench["p25"]), float(bench["p50"]), float(bench["p75"]), float(bench["p90"])

        salary_lines.append(
            "**薪资对标（ConvertedCompYearly）**："
            f"P25≈{_fmt_cny_from_usd(p25_usd)}，"
            f"P50≈{_fmt_cny_from_usd(p50_usd)}，"
            f"P75≈{_fmt_cny_from_usd(p75_usd)}，"
            f"P90≈{_fmt_cny_from_usd(p90_usd)}（人民币/年）"
        )
        salary_lines.append(
            f"**对标人群（cohort）**：Employment=employed，WorkExp={wb}，DevType={fam}"
            + ("（已回退）" if fallback_used else "")
        )
        salary_lines.append(f"**样本量**：n={n}（可信度：{_confidence(n)}）")
        if is_market_ref:
            salary_lines.append("说明：你当前为学生，这里用“入门在职人群”的分位数做市场参考（非对你当前收入的判断）。")

        # 把你前端的人民币 band 粗略转成 USD 去做对齐提示
        if salary_band:
            lo_cny, hi_cny = _parse_salary_band_cny(salary_band)
            salary_lines.append(f"你填写的薪资区间（人民币/年）：{salary_band}")
            if lo_cny is not None or hi_cny is not None:
                lo_usd = _cny_to_usd(lo_cny) if lo_cny is not None else None
                hi_usd = _cny_to_usd(hi_cny) if hi_cny is not None else None

                # 仅用于提示：区间与分位数关系
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

    # ===== Uplift (证据型)
    uplift_lines: List[str] = []
    if bench is not None:
        upl_rows = (
            uplift_df.where(
                (F.col("employment_std") == emp) &
                (F.col("workexp_bin") == wb) &
                (F.col("devtype_family") == fam)
            ).collect()
        )
        picked = _pick_uplift_lines([x.asDict() for x in upl_rows])
        if picked:
            uplift_lines.append("**进入 P75 人群更常见的特征（证据型）**：")
            uplift_lines.extend(picked)
        else:
            uplift_lines.append("**P75 特征差异**：当前 cohort 的高薪样本较少或差异不稳定，先以“可量化项目深度/技术闭环”作为主增量。")

    # ===== Stack suggestion (gap-driven)
    reco_lang, chosen_lang = _trend_reco(lang_df, wb, fam, sel_lang, top_k=3)
    reco_db, chosen_db = _trend_reco(db_df, wb, fam, sel_db, top_k=3)
    reco_web, chosen_web = _trend_reco(web_df, wb, fam, sel_web, top_k=3)

    stack_lines: List[str] = []
    stack_lines.append("**开发栈建议（基于 Have/Want 缺口 gap）**：")

    if reco_lang:
        stack_lines.append("\n语言（建议补齐）")
        stack_lines.extend(reco_lang)
    if reco_db:
        stack_lines.append("\n数据库（建议补齐）")
        stack_lines.extend(reco_db)
    if reco_web:
        stack_lines.append("\n框架/平台（建议补齐）")
        stack_lines.extend(reco_web)

    have_lines: List[str] = []
    if chosen_lang or chosen_db or chosen_web:
        have_lines.append("\n**你已选择的栈在对标人群中的普及度（have_rate 参考）**：")
        if chosen_lang:
            have_lines.append("语言")
            have_lines.extend(chosen_lang)
        if chosen_db:
            have_lines.append("数据库")
            have_lines.extend(chosen_db)
        if chosen_web:
            have_lines.append("框架/平台")
            have_lines.extend(chosen_web)

    # ===== analysisNote (CNY display)
    analysis_parts: List[str] = []
    analysis_parts.extend(salary_lines)
    if uplift_lines:
        analysis_parts.append("")
        analysis_parts.extend(uplift_lines)
    analysis_parts.append("")
    analysis_parts.extend(stack_lines)
    if have_lines:
        analysis_parts.extend(have_lines)

    # ===== aiSummary (actionable, CNY display)
    ai_parts: List[str] = []
    ai_parts.append("**下一步行动建议**：")
    if bench is not None:
        p50_usd = float(bench["p50"])
        p75_usd = float(bench["p75"])
        ai_parts.append(
            f"- 目标薪资建议（人民币/年，按 {FX_LABEL} 换算）："
            f"先对齐 P50≈{_fmt_cny_from_usd(p50_usd)}，再冲刺 P75≈{_fmt_cny_from_usd(p75_usd)}。"
        )
    ai_parts.append("- 用“一个可展示的项目闭环”去承载你要补的 gap 技术：需求→设计→实现→上线/复盘→量化指标。")
    ai_parts.append("- 简历/面试表达：讲清楚选型理由、权衡（性能/稳定性/成本）、以及你解决过的具体问题。")
    if reco_lang or reco_db or reco_web:
        ai_parts.append("- 优先级：先补 gap 最大且与你目标方向最贴近的 1-2 项，不要平均用力。")

    return {
        "analysisNote": "\n".join([x for x in analysis_parts if x is not None]),
        "aiSummary": "\n".join(ai_parts),
    }
