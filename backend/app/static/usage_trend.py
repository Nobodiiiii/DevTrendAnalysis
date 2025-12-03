import sqlite3
from collections import Counter
from pathlib import Path


def get_connection():
    here = Path(__file__).resolve()
    # static/.. = app, .. = backend, .. = 项目根目录
    project_root = here.parents[3]
    db_path = project_root / "data" / "devtrend.db"

    print("Using database:", db_path)
    conn = sqlite3.connect(db_path)
    return conn


def build_yearly_stats(
    conn,
    summary_table,
    yearly_config,
    separator=';'
):
    """
    通用聚合函数：按年统计 have / want 次数，并记录当年有效样本数 base_count。

    summary_table: 目标汇总表名，如 'language_usage_trend'
    yearly_config: dict，形如：
        {
          2018: {"table": "survey_results_2018", "have": "LanguageWorkedWith", "want": "LanguageDesireNextYear"},
          2019: {"table": "survey_results_2019", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
          ...
        }
    separator: 源数据中的分隔符，默认 ';'
    """
    cur = conn.cursor()

    # 1. 确保汇总表存在（带 base_count）
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {summary_table} (
            year        INTEGER NOT NULL,
            item        TEXT    NOT NULL,
            have_count  INTEGER NOT NULL,
            want_count  INTEGER NOT NULL,
            base_count  INTEGER NOT NULL,   -- 分母：该年有效行数（have 或 want 至少一个不为空）
            PRIMARY KEY (year, item)
        )
    """)

    for year, cfg in yearly_config.items():
        source_table = cfg["table"]
        have_col = cfg["have"]
        want_col = cfg["want"]

        print(f"Processing {summary_table} for year {year} from {source_table}...")

        # 2. 从对应年度原始表中取出 have / want 两列
        cur.execute(f"""
            SELECT {have_col}, {want_col}
            FROM {source_table}
        """)
        rows = cur.fetchall()

        have_counter = Counter()
        want_counter = Counter()
        base_count = 0  # 这一年的有效样本数（分母）

        # 3. 遍历每一行，按照 separator 拆分 + strip
        for have_val, want_val in rows:
            has_have = bool(have_val) and str(have_val).strip() != ''
            has_want = bool(want_val) and str(want_val).strip() != ''

            # 只要 have 或 want 任意一个非空，就计入分母
            if has_have or has_want:
                base_count += 1

            if has_have:
                for raw in str(have_val).split(separator):
                    name = raw.strip()
                    if name:
                        have_counter[name] += 1

            if has_want:
                for raw in str(want_val).split(separator):
                    name = raw.strip()
                    if name:
                        want_counter[name] += 1

        # 4. 合并 have / want 的所有 item，写入汇总表
        all_items = set(have_counter.keys()) | set(want_counter.keys())

        for item in all_items:
            have_count = have_counter.get(item, 0)
            want_count = want_counter.get(item, 0)
            cur.execute(
                f"""
                INSERT OR REPLACE INTO {summary_table}
                    (year, item, have_count, want_count, base_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (year, item, have_count, want_count, base_count)
            )

    conn.commit()


def main():
    conn = get_connection()

    # 1. Language
    language_config = {
        2017: {"table": "survey_results_2017", "have": "HaveWorkedLanguage", "want": "WantWorkLanguage"},
        2018: {"table": "survey_results_2018", "have": "LanguageWorkedWith", "want": "LanguageDesireNextYear"},
        2019: {"table": "survey_results_2019", "have": "LanguageWorkedWith", "want": "LanguageDesireNextYear"},
        2020: {"table": "survey_results_2020", "have": "LanguageWorkedWith", "want": "LanguageDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
        2025: {"table": "survey_results_2025", "have": "LanguageHaveWorkedWith", "want": "LanguageWantToWorkWith"},
    }

    # 2. Database
    database_config = {
        2017: {"table": "survey_results_2017", "have": "HaveWorkedDatabase", "want": "WantWorkDatabase"},
        2018: {"table": "survey_results_2018", "have": "DatabaseWorkedWith", "want": "DatabaseDesireNextYear"},
        2019: {"table": "survey_results_2019", "have": "DatabaseWorkedWith", "want": "DatabaseDesireNextYear"},
        2020: {"table": "survey_results_2020", "have": "DatabaseWorkedWith", "want": "DatabaseDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "DatabaseHaveWorkedWith", "want": "DatabaseWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "DatabaseHaveWorkedWith", "want": "DatabaseWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "DatabaseHaveWorkedWith", "want": "DatabaseWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "DatabaseHaveWorkedWith", "want": "DatabaseWantToWorkWith"},
        2025: {"table": "survey_results_2025", "have": "DatabaseHaveWorkedWith", "want": "DatabaseWantToWorkWith"},
    }

    # 3. Platform
    platform_config = {
        2017: {"table": "survey_results_2017", "have": "HaveWorkedPlatform", "want": "WantWorkPlatform"},
        2018: {"table": "survey_results_2018", "have": "PlatformWorkedWith", "want": "PlatformDesireNextYear"},
        2019: {"table": "survey_results_2019", "have": "PlatformWorkedWith", "want": "PlatformDesireNextYear"},
        2020: {"table": "survey_results_2020", "have": "PlatformWorkedWith", "want": "PlatformDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "PlatformHaveWorkedWith", "want": "PlatformWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "PlatformHaveWorkedWith", "want": "PlatformWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "PlatformHaveWorkedWith", "want": "PlatformWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "PlatformHaveWorkedWith", "want": "PlatformWantToWorkWith"},
        2025: {"table": "survey_results_2025", "have": "PlatformHaveWorkedWith", "want": "PlatformWantToWorkWith"},
    }

    # 4. Webframe / Framework
    webframe_config = {
        2017: {"table": "survey_results_2017", "have": "HaveWorkedFramework", "want": "WantWorkFramework"},
        2018: {"table": "survey_results_2018", "have": "FrameworkWorkedWith", "want": "FrameworkDesireNextYear"},
        2019: {"table": "survey_results_2019", "have": "WebFrameWorkedWith", "want": "WebFrameDesireNextYear"},
        2020: {"table": "survey_results_2020", "have": "WebframeWorkedWith", "want": "WebframeDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "WebframeHaveWorkedWith", "want": "WebframeWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "WebframeHaveWorkedWith", "want": "WebframeWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "WebframeHaveWorkedWith", "want": "WebframeWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "WebframeHaveWorkedWith", "want": "WebframeWantToWorkWith"},
        2025: {"table": "survey_results_2025", "have": "WebframeHaveWorkedWith", "want": "WebframeWantToWorkWith"},
    }

    # 5. MiscTech
    misc_tech_config = {
        2019: {"table": "survey_results_2019", "have": "MiscTechWorkedWith", "want": "MiscTechDesireNextYear"},
        2020: {"table": "survey_results_2020", "have": "MiscTechWorkedWith", "want": "MiscTechDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "MiscTechHaveWorkedWith", "want": "MiscTechWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "MiscTechHaveWorkedWith", "want": "MiscTechWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "MiscTechHaveWorkedWith", "want": "MiscTechWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "MiscTechHaveWorkedWith", "want": "MiscTechWantToWorkWith"},
    }

    # 6. ToolsTech
    tools_tech_config = {
        2021: {"table": "survey_results_2021", "have": "ToolsTechHaveWorkedWith", "want": "ToolsTechWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "ToolsTechHaveWorkedWith", "want": "ToolsTechWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "ToolsTechHaveWorkedWith", "want": "ToolsTechWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "ToolsTechHaveWorkedWith", "want": "ToolsTechWantToWorkWith"},
    }

    # 7. NEWCollabTools
    collab_tools_config = {
        2020: {"table": "survey_results_2020", "have": "NEWCollabToolsWorkedWith", "want": "NEWCollabToolsDesireNextYear"},
        2021: {"table": "survey_results_2021", "have": "NEWCollabToolsHaveWorkedWith", "want": "NEWCollabToolsWantToWorkWith"},
        2022: {"table": "survey_results_2022", "have": "NEWCollabToolsHaveWorkedWith", "want": "NEWCollabToolsWantToWorkWith"},
        2023: {"table": "survey_results_2023", "have": "NEWCollabToolsHaveWorkedWith", "want": "NEWCollabToolsWantToWorkWith"},
        2024: {"table": "survey_results_2024", "have": "NEWCollabToolsHaveWorkedWith", "want": "NEWCollabToolsWantToWorkWith"},
    }

    # 依次构建 7 个维度的汇总表
    build_yearly_stats(conn, "language_usage_trend_raw", language_config, separator=';')
    build_yearly_stats(conn, "database_usage_trend_raw", database_config, separator=';')
    build_yearly_stats(conn, "platform_usage_trend_raw", platform_config, separator=';')
    build_yearly_stats(conn, "webframe_usage_trend_raw", webframe_config, separator=';')
    build_yearly_stats(conn, "misctech_usage_trend_raw", misc_tech_config, separator=';')
    build_yearly_stats(conn, "toolstech_usage_trend_raw", tools_tech_config, separator=';')
    build_yearly_stats(conn, "collabtools_usage_trend_raw", collab_tools_config, separator=';')

    conn.close()


if __name__ == "__main__":
    main()
