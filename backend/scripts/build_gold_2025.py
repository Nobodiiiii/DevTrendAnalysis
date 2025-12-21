import json
from datetime import datetime
from pyspark.sql import SparkSession, functions as F

SILVER_RAW = "hdfs:///advice/silver/survey_results_2025_raw"
SILVER_CLEAN = "hdfs:///advice/silver/survey_results_2025_clean"

# ✅ salary benchmark rollups (fallback levels)
GOLD_BENCH_L1 = "hdfs:///advice/gold/2025/salary_benchmark_lvl1_emp_wb_dt"
GOLD_BENCH_L2 = "hdfs:///advice/gold/2025/salary_benchmark_lvl2_emp_wb"
GOLD_BENCH_L3 = "hdfs:///advice/gold/2025/salary_benchmark_lvl3_emp_dt"
GOLD_BENCH_L4 = "hdfs:///advice/gold/2025/salary_benchmark_lvl4_emp_all"

# ✅ tech trends
GOLD_TREND_LANG = "hdfs:///advice/gold/2025/tech_trends_language"
GOLD_TREND_DB = "hdfs:///advice/gold/2025/tech_trends_database"
GOLD_TREND_WEB = "hdfs:///advice/gold/2025/tech_trends_webframe"
GOLD_TREND_PLATFORM = "hdfs:///advice/gold/2025/tech_trends_platform"

# ✅ tech trends by salary tier (high/mid/low)
GOLD_TREND_LANG_BY_SALARY = "hdfs:///advice/gold/2025/tech_trends_language_by_salary"
GOLD_TREND_DB_BY_SALARY = "hdfs:///advice/gold/2025/tech_trends_database_by_salary"
GOLD_TREND_WEB_BY_SALARY = "hdfs:///advice/gold/2025/tech_trends_webframe_by_salary"
GOLD_TREND_PLATFORM_BY_SALARY = "hdfs:///advice/gold/2025/tech_trends_platform_by_salary"

spark = SparkSession.builder.appName("advice-build-gold-2025").getOrCreate()

raw = spark.read.parquet(SILVER_RAW)

df = raw.select(
    F.col("ResponseId").alias("response_id"),
    F.col("ConvertedCompYearly").alias("salary_yearly"),
    F.col("Employment").alias("employment"),
    F.col("WorkExp").alias("workexp"),
    F.col("DevType").alias("devtype"),
    # tech have/want
    F.col("LanguageHaveWorkedWith").alias("lang_have"),
    F.col("LanguageWantToWorkWith").alias("lang_want"),
    F.col("DatabaseHaveWorkedWith").alias("db_have"),
    F.col("DatabaseWantToWorkWith").alias("db_want"),
    F.col("WebframeHaveWorkedWith").alias("web_have"),
    F.col("WebframeWantToWorkWith").alias("web_want"),
    F.col("PlatformHaveWorkedWith").alias("platform_have"),
    F.col("PlatformWantToWorkWith").alias("platform_want"),
)

def norm(c):
    return F.when(F.col(c).isNull(), F.lit(None)).otherwise(F.trim(F.col(c)))

df = (
    df.withColumn("employment", norm("employment"))
      .withColumn("devtype", norm("devtype"))
)

# Employment_std
df = df.withColumn(
    "employment_std",
    F.when(F.lower(F.col("employment")) == "employed", F.lit("employed"))
     .when(F.lower(F.col("employment")).contains("independent contractor"), F.lit("self_employed"))
     .when(F.lower(F.col("employment")) == "student", F.lit("student"))
     .when(F.lower(F.col("employment")) == "not employed", F.lit("not_employed"))
     .when(F.lower(F.col("employment")) == "retired", F.lit("retired"))
     .otherwise(F.lit("unknown"))
)

# WorkExpYears + Bin
df = df.withColumn("workexp_years", F.regexp_extract(F.col("workexp").cast("string"), r"(\d+)", 1).cast("int"))
df = df.withColumn(
    "workexp_bin",
    F.when(F.col("workexp_years").isNull(), F.lit("unknown"))
     .when(F.col("workexp_years") <= 1, F.lit("0-1"))
     .when(F.col("workexp_years").between(2, 3), F.lit("2-3"))
     .when(F.col("workexp_years").between(4, 6), F.lit("4-6"))
     .when(F.col("workexp_years").between(7, 10), F.lit("7-10"))
     .when(F.col("workexp_years").between(11, 15), F.lit("11-15"))
     .otherwise(F.lit("16+"))
)

# DevType_primary（若多选用第一个 token）
df = df.withColumn(
    "devtype_primary",
    F.when(F.col("devtype").isNull(), F.lit("null"))
     .otherwise(F.trim(F.split(F.col("devtype"), ";").getItem(0)))
)

# DevType_family 映射（你给的全量 + 兜底）
dt = F.col("devtype_primary")
df = df.withColumn(
    "devtype_family",
    F.when(dt == "Developer, full-stack", F.lit("fullstack"))
     .when(dt == "Developer, back-end", F.lit("backend"))
     .when(dt == "Developer, front-end", F.lit("frontend"))
     .when(dt == "Developer, mobile", F.lit("mobile"))
     .when(dt == "Developer, desktop or enterprise applications", F.lit("desktop_enterprise"))
     .when(dt.isin("Developer, embedded applications or devices", "Hardware Engineer"), F.lit("embedded_hardware"))
     .when(dt.isin("DevOps specialist", "Cloud infrastructure engineer", "Engineer, site reliability", "System administrator"), F.lit("devops_cloud_sre"))
     .when(dt.isin("Data scientist or machine learning specialist", "Data engineer", "Developer, AI"), F.lit("data_ml"))
     .when(dt == "Security professional", F.lit("security"))
     .when(dt == "Developer, QA or test", F.lit("qa"))
     .when(dt.isin("Engineering manager", "Senior Executive (C-Suite, VP, etc.)", "Project manager", "Product manager"), F.lit("management_exec"))
     .when(dt.isin("Academic researcher", "Research & Development role", "Educator", "Scientist"), F.lit("research_edu"))
     .when(dt == "Developer, game or graphics", F.lit("graphics_game"))
     .when(dt == "Developer Experience", F.lit("devex"))
     .when(dt == "Database administrator", F.lit("dba"))
     .when(dt == "Designer", F.lit("design"))
     .when(dt.isin("Developer Advocate", "Marketing or sales professional"), F.lit("advocacy_marketing"))
     .when(dt == "Student", F.lit("student_role"))
     .otherwise(F.lit("other"))
)

# salary 清洗
df = (
    df.withColumn("salary_yearly", F.col("salary_yearly").cast("double"))
      .withColumn("salary_yearly", F.when(F.col("salary_yearly") <= 0, F.lit(None)).otherwise(F.col("salary_yearly")))
)

# 写 Silver clean
df.write.mode("overwrite").parquet(SILVER_CLEAN)

# ===== 用于 benchmark 的有效样本
salary_df = (
    df.where(F.col("salary_yearly").isNotNull())
      .where(F.col("employment_std").isin("employed", "self_employed"))
      .where(F.col("workexp_bin") != "unknown")
)

def agg_quantiles(gdf):
    return gdf.agg(
        F.count("*").alias("n"),
        F.expr("percentile_approx(salary_yearly, 0.25)").alias("p25"),
        F.expr("percentile_approx(salary_yearly, 0.50)").alias("p50"),
        F.expr("percentile_approx(salary_yearly, 0.75)").alias("p75"),
        F.expr("percentile_approx(salary_yearly, 0.90)").alias("p90"),
    )

# L1: emp + workexp_bin + devtype_family
bench_l1 = agg_quantiles(salary_df.groupBy("employment_std", "workexp_bin", "devtype_family"))
bench_l1.write.mode("overwrite").parquet(GOLD_BENCH_L1)

# L2: emp + workexp_bin
bench_l2 = agg_quantiles(salary_df.groupBy("employment_std", "workexp_bin")) \
    .withColumn("devtype_family", F.lit(None).cast("string"))
bench_l2.write.mode("overwrite").parquet(GOLD_BENCH_L2)

# L3: emp + devtype_family
bench_l3 = agg_quantiles(salary_df.groupBy("employment_std", "devtype_family")) \
    .withColumn("workexp_bin", F.lit(None).cast("string"))
bench_l3.write.mode("overwrite").parquet(GOLD_BENCH_L3)

# L4: emp all
bench_l4 = agg_quantiles(salary_df.groupBy("employment_std")) \
    .withColumn("workexp_bin", F.lit(None).cast("string")) \
    .withColumn("devtype_family", F.lit(None).cast("string"))
bench_l4.write.mode("overwrite").parquet(GOLD_BENCH_L4)

# ===== Gold: tech trends（have/want 缺口）
def build_trends(df_in, have_col, want_col, out_path, tech_type):
    base = (
        df_in.where(F.col("employment_std").isin("employed", "self_employed"))
            .where(F.col("workexp_bin") != "unknown")
            .select(
                "response_id", "workexp_bin", "devtype_family",
                F.col(have_col).alias("have_raw"),
                F.col(want_col).alias("want_raw")
            )
    )

    cohort_n = base.groupBy("workexp_bin", "devtype_family") \
                   .agg(F.countDistinct("response_id").alias("n"))

    def explode_tokens(colname):
        return (
            base.select(
                "response_id", "workexp_bin", "devtype_family",
                F.explode(F.split(F.coalesce(F.col(colname), F.lit("")), ";")).alias("tech")
            )
            .withColumn("tech", F.trim(F.col("tech")))
            .where(F.col("tech") != "")
            .dropDuplicates(["response_id", "workexp_bin", "devtype_family", "tech"])
        )

    have = explode_tokens("have_raw")
    want = explode_tokens("want_raw")

    have_cnt = have.groupBy("workexp_bin", "devtype_family", "tech") \
                   .agg(F.countDistinct("response_id").alias("have_cnt"))
    want_cnt = want.groupBy("workexp_bin", "devtype_family", "tech") \
                   .agg(F.countDistinct("response_id").alias("want_cnt"))

    hv = (
        have_cnt.join(want_cnt, ["workexp_bin", "devtype_family", "tech"], "full")
                .withColumn("have_cnt", F.coalesce(F.col("have_cnt"), F.lit(0)))
                .withColumn("want_cnt", F.coalesce(F.col("want_cnt"), F.lit(0)))
    )

    trend = (
        hv.join(cohort_n, ["workexp_bin", "devtype_family"], "left")
          .withColumn("have_rate", F.col("have_cnt") / F.col("n"))
          .withColumn("want_rate", F.col("want_cnt") / F.col("n"))
          .withColumn("gap", F.col("want_rate") - F.col("have_rate"))
          .withColumn("tech_type", F.lit(tech_type))
          .select("tech_type", "workexp_bin", "devtype_family", "tech", "n", "have_rate", "want_rate", "gap")
    )

    trend.write.mode("overwrite").parquet(out_path)

build_trends(df, "lang_have", "lang_want", GOLD_TREND_LANG, "language")
build_trends(df, "db_have", "db_want", GOLD_TREND_DB, "database")
build_trends(df, "web_have", "web_want", GOLD_TREND_WEB, "webframe")
build_trends(df, "platform_have", "platform_want", GOLD_TREND_PLATFORM, "platform")


# ===== Gold: tech trends by salary tier（按薪资分层的技术趋势）
def build_trends_by_salary_tier(df_in, have_col, want_col, out_path, tech_type):
    """
    按薪资分位数分层：
    - low: <P25
    - mid: P25-P75
    - high: >P75
    按 devtype_family 分组（保留方向维度）
    """
    # 只保留有薪资数据的在职人员
    base = (
        df_in.where(F.col("salary_yearly").isNotNull())
            .where(F.col("employment_std").isin("employed", "self_employed"))
            .where(F.col("workexp_bin") != "unknown")
            .select(
                "response_id", "salary_yearly", "devtype_family",
                F.col(have_col).alias("have_raw"),
                F.col(want_col).alias("want_raw")
            )
    )

    # 计算全局薪资分位数（P25, P75）
    percentiles = base.select(
        F.expr("percentile_approx(salary_yearly, 0.25)").alias("p25"),
        F.expr("percentile_approx(salary_yearly, 0.75)").alias("p75"),
    ).collect()[0]
    p25_val = float(percentiles["p25"])
    p75_val = float(percentiles["p75"])

    # 添加 salary_tier 字段
    base = base.withColumn(
        "salary_tier",
        F.when(F.col("salary_yearly") < p25_val, F.lit("low"))
         .when(F.col("salary_yearly") > p75_val, F.lit("high"))
         .otherwise(F.lit("mid"))
    )

    # 按 devtype_family + salary_tier 分组统计人数
    cohort_n = base.groupBy("devtype_family", "salary_tier") \
                   .agg(F.countDistinct("response_id").alias("n"))

    def explode_tokens(colname):
        return (
            base.select(
                "response_id", "devtype_family", "salary_tier",
                F.explode(F.split(F.coalesce(F.col(colname), F.lit("")), ";")).alias("tech")
            )
            .withColumn("tech", F.trim(F.col("tech")))
            .where(F.col("tech") != "")
            .dropDuplicates(["response_id", "devtype_family", "salary_tier", "tech"])
        )

    have = explode_tokens("have_raw")
    want = explode_tokens("want_raw")

    have_cnt = have.groupBy("devtype_family", "salary_tier", "tech") \
                   .agg(F.countDistinct("response_id").alias("have_cnt"))
    want_cnt = want.groupBy("devtype_family", "salary_tier", "tech") \
                   .agg(F.countDistinct("response_id").alias("want_cnt"))

    hv = (
        have_cnt.join(want_cnt, ["devtype_family", "salary_tier", "tech"], "full")
                .withColumn("have_cnt", F.coalesce(F.col("have_cnt"), F.lit(0)))
                .withColumn("want_cnt", F.coalesce(F.col("want_cnt"), F.lit(0)))
    )

    trend = (
        hv.join(cohort_n, ["devtype_family", "salary_tier"], "left")
          .withColumn("have_rate", F.col("have_cnt") / F.col("n"))
          .withColumn("want_rate", F.col("want_cnt") / F.col("n"))
          .withColumn("gap", F.col("want_rate") - F.col("have_rate"))
          .withColumn("tech_type", F.lit(tech_type))
          .withColumn("p25_threshold", F.lit(p25_val))
          .withColumn("p75_threshold", F.lit(p75_val))
          .select("tech_type", "devtype_family", "salary_tier", "tech", "n",
                  "have_rate", "want_rate", "gap", "p25_threshold", "p75_threshold")
    )

    trend.write.mode("overwrite").parquet(out_path)


build_trends_by_salary_tier(df, "lang_have", "lang_want", GOLD_TREND_LANG_BY_SALARY, "language")
build_trends_by_salary_tier(df, "db_have", "db_want", GOLD_TREND_DB_BY_SALARY, "database")
build_trends_by_salary_tier(df, "web_have", "web_want", GOLD_TREND_WEB_BY_SALARY, "webframe")
build_trends_by_salary_tier(df, "platform_have", "platform_want", GOLD_TREND_PLATFORM_BY_SALARY, "platform")

# ===== 收集元数据指标 =====
metadata = {
    "build_timestamp": datetime.now().isoformat(),
    "data_year": 2025,
    "source": {
        "silver_raw": SILVER_RAW,
        "silver_clean": SILVER_CLEAN,
    },
    "data_quality": {},
    "salary_benchmark": {},
    "tech_trends": {},
    "salary_tier": {},
}

# 1. 数据源质量指标
total_raw = raw.count()
total_clean = df.count()

# 字段缺失率
missing_stats = df.agg(
    F.count("*").alias("total"),
    F.sum(F.when(F.col("salary_yearly").isNull(), 1).otherwise(0)).alias("salary_null"),
    F.sum(F.when(F.col("employment").isNull(), 1).otherwise(0)).alias("employment_null"),
    F.sum(F.when(F.col("workexp").isNull(), 1).otherwise(0)).alias("workexp_null"),
    F.sum(F.when(F.col("devtype").isNull(), 1).otherwise(0)).alias("devtype_null"),
    F.sum(F.when(F.col("lang_have").isNull(), 1).otherwise(0)).alias("lang_have_null"),
    F.sum(F.when(F.col("db_have").isNull(), 1).otherwise(0)).alias("db_have_null"),
    F.sum(F.when(F.col("web_have").isNull(), 1).otherwise(0)).alias("web_have_null"),
    F.sum(F.when(F.col("platform_have").isNull(), 1).otherwise(0)).alias("platform_have_null"),
).collect()[0]

metadata["data_quality"] = {
    "total_raw_samples": total_raw,
    "total_clean_samples": total_clean,
    "valid_salary_samples": salary_df.count(),
    "missing_rates": {
        "salary": round(missing_stats["salary_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "employment": round(missing_stats["employment_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "workexp": round(missing_stats["workexp_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "devtype": round(missing_stats["devtype_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "lang_have": round(missing_stats["lang_have_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "db_have": round(missing_stats["db_have_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "web_have": round(missing_stats["web_have_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
        "platform_have": round(missing_stats["platform_have_null"] / missing_stats["total"], 4) if missing_stats["total"] > 0 else 0,
    },
}

# 2. 薪资基准指标
# 全局薪资分位数
global_salary_stats = salary_df.agg(
    F.count("*").alias("n"),
    F.expr("percentile_approx(salary_yearly, 0.25)").alias("p25"),
    F.expr("percentile_approx(salary_yearly, 0.50)").alias("p50"),
    F.expr("percentile_approx(salary_yearly, 0.75)").alias("p75"),
    F.expr("percentile_approx(salary_yearly, 0.90)").alias("p90"),
    F.min("salary_yearly").alias("min"),
    F.max("salary_yearly").alias("max"),
    F.avg("salary_yearly").alias("avg"),
    F.stddev("salary_yearly").alias("stddev"),
).collect()[0]

# L1 覆盖度统计
l1_coverage = bench_l1.agg(
    F.count("*").alias("total_combinations"),
    F.sum("n").alias("total_samples"),
    F.avg("n").alias("avg_samples_per_combo"),
    F.min("n").alias("min_samples"),
    F.max("n").alias("max_samples"),
).collect()[0]

# 各层级统计
l2_stats = bench_l2.agg(F.count("*").alias("combos"), F.sum("n").alias("samples")).collect()[0]
l3_stats = bench_l3.agg(F.count("*").alias("combos"), F.sum("n").alias("samples")).collect()[0]
l4_stats = bench_l4.agg(F.count("*").alias("combos"), F.sum("n").alias("samples")).collect()[0]

metadata["salary_benchmark"] = {
    "global_percentiles": {
        "n": int(global_salary_stats["n"]),
        "p25": float(global_salary_stats["p25"]),
        "p50": float(global_salary_stats["p50"]),
        "p75": float(global_salary_stats["p75"]),
        "p90": float(global_salary_stats["p90"]),
        "min": float(global_salary_stats["min"]),
        "max": float(global_salary_stats["max"]),
        "avg": round(float(global_salary_stats["avg"]), 2),
        "stddev": round(float(global_salary_stats["stddev"]), 2) if global_salary_stats["stddev"] else 0,
    },
    "level_coverage": {
        "L1": {
            "combinations": int(l1_coverage["total_combinations"]),
            "total_samples": int(l1_coverage["total_samples"]),
            "avg_per_combo": round(float(l1_coverage["avg_samples_per_combo"]), 1),
            "min_samples": int(l1_coverage["min_samples"]),
            "max_samples": int(l1_coverage["max_samples"]),
        },
        "L2": {
            "combinations": int(l2_stats["combos"]),
            "total_samples": int(l2_stats["samples"]),
        },
        "L3": {
            "combinations": int(l3_stats["combos"]),
            "total_samples": int(l3_stats["samples"]),
        },
        "L4": {
            "combinations": int(l4_stats["combos"]),
            "total_samples": int(l4_stats["samples"]),
        },
    },
}

# 3. 技术趋势指标
def get_trend_stats(trend_df, tech_type):
    """获取技术趋势表的统计指标"""
    stats = trend_df.agg(
        F.countDistinct("tech").alias("unique_techs"),
        F.count("*").alias("total_rows"),
        F.avg("have_rate").alias("avg_have"),
        F.avg("want_rate").alias("avg_want"),
        F.avg("gap").alias("avg_gap"),
        F.max("gap").alias("max_gap"),
        F.min("gap").alias("min_gap"),
    ).collect()[0]

    # 获取 gap 最大的前5个技术
    top_gap = trend_df.orderBy(F.col("gap").desc()).limit(5).collect()

    return {
        "unique_techs": int(stats["unique_techs"]),
        "total_rows": int(stats["total_rows"]),
        "avg_have_rate": round(float(stats["avg_have"]), 4),
        "avg_want_rate": round(float(stats["avg_want"]), 4),
        "avg_gap": round(float(stats["avg_gap"]), 4),
        "max_gap": round(float(stats["max_gap"]), 4),
        "min_gap": round(float(stats["min_gap"]), 4),
        "top_gap_techs": [
            {"tech": r["tech"], "gap": round(float(r["gap"]), 4), "have": round(float(r["have_rate"]), 4), "want": round(float(r["want_rate"]), 4)}
            for r in top_gap
        ],
    }

# 读取刚写入的趋势表
lang_trend = spark.read.parquet(GOLD_TREND_LANG)
db_trend = spark.read.parquet(GOLD_TREND_DB)
web_trend = spark.read.parquet(GOLD_TREND_WEB)
platform_trend = spark.read.parquet(GOLD_TREND_PLATFORM)

metadata["tech_trends"] = {
    "language": get_trend_stats(lang_trend, "language"),
    "database": get_trend_stats(db_trend, "database"),
    "webframe": get_trend_stats(web_trend, "webframe"),
    "platform": get_trend_stats(platform_trend, "platform"),
}

# 4. 薪资分层指标（只保留阈值，样本量已在 data_quality 中）
lang_salary_tier = spark.read.parquet(GOLD_TREND_LANG_BY_SALARY)
tier_thresholds = lang_salary_tier.select("p25_threshold", "p75_threshold").first()

metadata["salary_tier"] = {
    "thresholds": {
        "p25": float(tier_thresholds["p25_threshold"]) if tier_thresholds else 0,
        "p75": float(tier_thresholds["p75_threshold"]) if tier_thresholds else 0,
    },
}

# 保存元数据到 HDFS
metadata_path = "hdfs:///advice/gold/2025/metadata.json"
metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)
spark.sparkContext.parallelize([metadata_json]).coalesce(1).saveAsTextFile(
    "hdfs:///advice/gold/2025/_metadata_temp"
)
# 也保存一份到本地（方便查看）
import os
local_metadata_dir = os.path.join(os.path.dirname(__file__), "..", "gold_metadata")
os.makedirs(local_metadata_dir, exist_ok=True)
local_metadata_path = os.path.join(local_metadata_dir, "gold_2025_metadata.json")
with open(local_metadata_path, "w", encoding="utf-8") as f:
    f.write(metadata_json)

print("DONE:")
print("  SILVER_CLEAN =", SILVER_CLEAN)
print("  GOLD_BENCH_L1 =", GOLD_BENCH_L1)
print("  GOLD_BENCH_L2 =", GOLD_BENCH_L2)
print("  GOLD_BENCH_L3 =", GOLD_BENCH_L3)
print("  GOLD_BENCH_L4 =", GOLD_BENCH_L4)
print("  GOLD_TREND_LANG =", GOLD_TREND_LANG)
print("  GOLD_TREND_DB   =", GOLD_TREND_DB)
print("  GOLD_TREND_WEB  =", GOLD_TREND_WEB)
print("  GOLD_TREND_PLATFORM =", GOLD_TREND_PLATFORM)
print("  GOLD_TREND_LANG_BY_SALARY =", GOLD_TREND_LANG_BY_SALARY)
print("  GOLD_TREND_DB_BY_SALARY   =", GOLD_TREND_DB_BY_SALARY)
print("  GOLD_TREND_WEB_BY_SALARY  =", GOLD_TREND_WEB_BY_SALARY)
print("  GOLD_TREND_PLATFORM_BY_SALARY =", GOLD_TREND_PLATFORM_BY_SALARY)
print("  METADATA (local) =", local_metadata_path)
print("\n=== 数据质量摘要 ===")
print(f"  原始样本: {metadata['data_quality']['total_raw_samples']}")
print(f"  清洗后样本: {metadata['data_quality']['total_clean_samples']}")
print(f"  有效薪资样本: {metadata['data_quality']['valid_salary_samples']}")
print(f"  薪资缺失率: {metadata['data_quality']['missing_rates']['salary']:.1%}")
print(f"  全局薪资 P50: ${metadata['salary_benchmark']['global_percentiles']['p50']:,.0f}")
print(f"  L1 覆盖组合数: {metadata['salary_benchmark']['level_coverage']['L1']['combinations']}")

spark.stop()
