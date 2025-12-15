from typing import Dict, Any, List
from pyspark.sql import SparkSession, functions as F

GOLD_BENCH_BASE = "hdfs:///advice/gold/2025/salary_benchmark_base"
GOLD_UPLIFT_BASE = "hdfs:///advice/gold/2025/uplift_to_p75_base"

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

def employment_std(profile_type: str) -> str:
    if profile_type == "professional":
        return "employed"
    if profile_type == "student":
        return "student"
    return "unknown"

def workexp_bin(years: Any) -> str:
    try:
        y = int(str(years).strip())
    except Exception:
        return "unknown"
    if y <= 1: return "0-1"
    if 2 <= y <= 3: return "2-3"
    if 4 <= y <= 6: return "4-6"
    if 7 <= y <= 10: return "7-10"
    if 11 <= y <= 15: return "11-15"
    return "16+"

def devtype_family_from_payload(payload: Dict[str, Any]) -> str:
    pt = payload.get("profileType", "")
    if pt == "student":
        track = payload.get("studentProfile", {}).get("expectedTrack", "")
    else:
        track = payload.get("proProfile", {}).get("track", "")
    return TRACK_TO_FAMILY.get(track, "other")

def pick_uplift(rows: List[dict]) -> List[str]:
    # n_high 太小的不输出，避免误导
    cand = [r for r in rows if (r.get("n_high") or 0) >= 30]
    cand.sort(key=lambda r: r.get("uplift", 0.0), reverse=True)
    lines = []
    for r in cand[:3]:
        lines.append(f"- 高薪组更常见：{r['feature_name']} = {r['feature_value']}（uplift {r['uplift']:+.1%}）")
    return lines

def generate_analysis_note(payload: Dict[str, Any]) -> Dict[str, str]:
    spark = SparkSession.builder.appName("advice-generate-analysis").getOrCreate()

    emp = employment_std(payload.get("profileType", ""))
    fam = devtype_family_from_payload(payload)
    if payload.get("profileType") == "professional":
        wb = workexp_bin(payload.get("proProfile", {}).get("years"))
    else:
        wb = "0-1"

    # 学生不做薪资对标（避免误导）
    if emp != "employed":
        spark.stop()
        return {
            "analysisNote": "当前身份为学生/非在职，我们不做薪资分位对标（避免误导）。建议优先补齐：项目作品、可证明的技术深度、以及目标方向的核心栈。",
            "aiSummary": ""
        }

    bench = spark.read.parquet(GOLD_BENCH_BASE)

    row = (
        bench.where(
            (F.col("employment_std") == "employed") &
            (F.col("workexp_bin") == wb) &
            (F.col("devtype_family") == fam)
        ).limit(1).collect()
    )

    # 回退：devtype_family -> other
    if not row:
        row = (
            bench.where(
                (F.col("employment_std") == "employed") &
                (F.col("workexp_bin") == wb) &
                (F.col("devtype_family") == "other")
            ).limit(1).collect()
        )

    # 回退：workexp_bin unknown or miss -> 合并到 4-10（你也可以换成 other 逻辑）
    if not row and wb == "unknown":
        row = (
            bench.where(
                (F.col("employment_std") == "employed") &
                (F.col("workexp_bin") == "4-6") &
                (F.col("devtype_family") == fam)
            ).limit(1).collect()
        )

    if not row:
        spark.stop()
        return {"analysisNote": "基准表未命中（可能 Gold 还没生成或 cohort 太稀）。请检查 gold 生成是否成功。", "aiSummary": ""}

    r = row[0].asDict()
    n = int(r["n"])
    p25, p50, p75, p90 = float(r["p25"]), float(r["p50"]), float(r["p75"]), float(r["p90"])

    confidence = "高" if n >= N_STRONG else ("中" if n >= N_OK else "低")

    # uplift（可选输出）
    uplift = spark.read.parquet(GOLD_UPLIFT_BASE)
    upl_rows = (
        uplift.where(
            (F.col("employment_std") == "employed") &
            (F.col("workexp_bin") == wb) &
            (F.col("devtype_family") == fam)
        ).collect()
    )
    upl_lines = pick_uplift([x.asDict() for x in upl_rows])

    lines = []
    lines.append(f"**对标人群（cohort）**：Employment=employed，WorkExp={wb}，DevType={fam}")
    lines.append(f"**样本量**：n={n}（可信度：{confidence}）")
    lines.append(f"**年薪分位数（ConvertedCompYearly）**：P25≈{p25:,.0f}，P50≈{p50:,.0f}，P75≈{p75:,.0f}，P90≈{p90:,.0f}")

    if upl_lines:
        lines.append("\n**进入 P75 人群更常见的特征（证据型）**：")
        lines.extend(upl_lines)

    spark.stop()
    return {"analysisNote": "\n".join(lines), "aiSummary": ""}

# 允许你在命令行本地测试：python3 generate_analysis_note.py
if __name__ == "__main__":
    demo_payload = {
        "profileType": "professional",
        "proProfile": {"years": "3", "track": "后端开发"},
        "studentProfile": {},
        "techStack": {"languages": ["Python"], "databases": ["PostgreSQL"], "webframes": ["FastAPI"]},
        "otherInfo": {"consentShare": "yes", "isTruthful": "true", "note": ""}
    }
    print(generate_analysis_note(demo_payload)["analysisNote"])
