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

print("DONE:")
print("  SILVER_CLEAN =", SILVER_CLEAN)
print("  GOLD_BENCH_L1 =", GOLD_BENCH_L1)
print("  GOLD_BENCH_L2 =", GOLD_BENCH_L2)
print("  GOLD_BENCH_L3 =", GOLD_BENCH_L3)
print("  GOLD_BENCH_L4 =", GOLD_BENCH_L4)
print("  GOLD_TREND_LANG =", GOLD_TREND_LANG)
print("  GOLD_TREND_DB   =", GOLD_TREND_DB)
print("  GOLD_TREND_WEB  =", GOLD_TREND_WEB)

spark.stop()
