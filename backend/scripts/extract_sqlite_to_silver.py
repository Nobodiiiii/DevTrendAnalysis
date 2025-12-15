from pyspark.sql import SparkSession

SQLITE_PATH = "/mnt/d/MyFiles/Projects/DevTrendAnalysis/data/devtrend.db"
TABLE = "survey_results_2025"  # <- 改成你 sqlite3 .tables 看到的真实表名
SILVER_PATH = "hdfs:///advice/silver/survey_results_2025_raw"

spark = SparkSession.builder.appName("sqlite-to-silver").getOrCreate()

df = (
    spark.read.format("jdbc")
    .option("url", f"jdbc:sqlite:{SQLITE_PATH}")
    .option("driver", "org.sqlite.JDBC")
    .option("dbtable", TABLE)
    .load()
)

df.write.mode("overwrite").parquet(SILVER_PATH)

print("WROTE:", SILVER_PATH)
spark.stop()
