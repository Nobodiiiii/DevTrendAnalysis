from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


def read_csv_with_guess(path: Path) -> pd.DataFrame:
    """尝试多种常见编码读取 CSV，避免 UnicodeDecodeError。"""
    encodings_to_try = ["utf-8", "utf-8-sig", "gbk", "latin1"]
    last_error = None

    for enc in encodings_to_try:
        try:
            print(f"尝试使用编码 {enc} 读取 {path} ...")
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as e:
            print(f"使用编码 {enc} 失败：{e}")
            last_error = e

    # 如果都失败，就把最后一个错误抛出去
    raise last_error


def main():
    # import_csv.py 在 backend/database 下，向上三级是项目根目录 DevTrendAnalysis
    base_dir = Path(__file__).resolve().parents[2]

    # 数据目录
    data_dir = base_dir / "data"
    raw_dir = data_dir / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 数据库路径：data/devtrend.db（如果不存在会自动创建）
    db_path = data_dir / "devtrend.db"

    # SQLite 连接：sqlite:///绝对路径
    engine = create_engine(f"sqlite:///{db_path}")

    # 循环年份：2012 ~ 2025（range(12, 26) -> 12..25）
    for year_suffix in range(12, 26):
        # year_suffix 是 int，要么转成 str，要么用 f-string
        year_str = str(year_suffix)  # 例如 "12", "13", ..., "25"

        csv_name = f"survey_results_20{year_str}.csv"
        csv_path = raw_dir / csv_name

        if not csv_path.exists():
            print(f"⚠ 跳过，CSV 文件不存在: {csv_path}")
            continue

        df = read_csv_with_guess(csv_path)

        # 表名不能用文件路径，也不要带 .csv
        # 这里用 "survey_results_2012" 这种表名
        table_name = f"survey_results_20{year_str}"

        df.to_sql(table_name, engine, if_exists="replace", index=False)

        print(f"已导入 CSV: {csv_path}")
        print(f"数据库中的表名：{table_name}")

    print(f"\n全部导入完成，数据库文件: {db_path}")


if __name__ == "__main__":
    main()
