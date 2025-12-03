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
    separator=';',
    item_mapping=None,
):
    """
    通用聚合函数：按年统计 have / want 次数，并记录当年有效样本数 base_count。

    - 支持名称映射 item_mapping（例如 React.js -> React）
    - 支持“每行去重”：同一受访者 + 同一 canonical 名称最多算 1 次
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

        # 先清掉这一年的旧数据，避免改了映射后留下脏行
        cur.execute(f"DELETE FROM {summary_table} WHERE year = ?", (year,))

        # 2. 从对应年度原始表中取出 have / want 两列
        cur.execute(f"""
            SELECT {have_col}, {want_col}
            FROM {source_table}
        """)
        rows = cur.fetchall()

        have_counter = Counter()
        want_counter = Counter()
        base_count = 0  # 这一年的有效样本数（分母）

        # 3. 遍历每一行，名称映射 + 每行内部去重
        for have_val, want_val in rows:
            has_have = bool(have_val) and str(have_val).strip() != ''
            has_want = bool(want_val) and str(want_val).strip() != ''

            # 只要 have 或 want 任意一个非空，就计入分母
            if has_have or has_want:
                base_count += 1

            row_have_items = set()
            row_want_items = set()

            if has_have:
                for raw in str(have_val).split(separator):
                    name = raw.strip()
                    if not name:
                        continue
                    if item_mapping:
                        name = item_mapping.get(name, name)
                    row_have_items.add(name)

            if has_want:
                for raw in str(want_val).split(separator):
                    name = raw.strip()
                    if not name:
                        continue
                    if item_mapping:
                        name = item_mapping.get(name, name)
                    row_want_items.add(name)

            # 每个 canonical 名称在本行最多 +1
            for name in row_have_items:
                have_counter[name] += 1
            for name in row_want_items:
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

    # ====== 各维度的名称映射（激进版） ======

    # 1) Language
    language_mapping = {
        # HTML / CSS
        "HTML": "HTML/CSS",
        "CSS": "HTML/CSS",
        "HTML/CSS": "HTML/CSS",

        # Shell / PowerShell
        "Bash/Shell (all shells)": "Bash/Shell",
        "Bash/Shell/PowerShell": "Bash/Shell",

        # Case normalization / duplicates
        "Matlab": "MATLAB",
        "Delphi": "Delphi/Object Pascal",
        "Cobol": "COBOL",
        "Visual Basic (.Net)": "VB.NET",
        "Ocaml": "OCaml",

        # Lisp family
        "LISP": "Lisp",
        "Common Lisp": "Lisp",

        # Other catch-all
        "Other(s):": "Other",

        # Additional recommended normalizations
        "Bash/Shell (All Shells)": "Bash/Shell",
        "VB.NET": "VB.NET",
        "Visual Basic 6": "VB6",
        "VBA": "VB6",
    }

    # 2) Database
    database_mapping = {
        # DynamoDB（大小写与前缀）
        "DynamoDB": "Amazon DynamoDB",
        "Dynamodb": "Amazon DynamoDB",

        # Amazon RDS/Aurora 统一
        "Amazon RDS/Aurora": "Amazon RDS/Aurora",

        # BigQuery
        "Google BigQuery": "BigQuery",

        # CouchDB
        "Couch DB": "CouchDB",

        # CosmosDB
        "Cosmos DB": "CosmosDB",

        # CockroachDB（大小写）
        "Cockroachdb": "CockroachDB",

        # DB2
        "IBM DB2": "IBM Db2",

        # Neo4j（大小写）
        "Neo4J": "Neo4j",

        # SQL Server（与 Microsoft SQL Server 聚合）
        "SQL Server": "Microsoft SQL Server",

        # Firebase 家族可以分两层（推荐映射）
        "Firebase": "Firebase Realtime Database",
        # （理由：用户通常指的就是实时数据库，不是 Firestore）

        # Microsoft Azure 泛称 → 不映射到具体数据库，但统一名称
        "Microsoft Azure (Tables, CosmosDB, SQL, etc)": "Azure (Multiple Services)",

        # Other
        "Other(s):": "Other"
    }

    # 3) Platform
    platform_mapping = {
        # AWS variants
        "Amazon Web Services (AWS)": "AWS",

        # DigitalOcean variants
        "Digital Ocean": "DigitalOcean",

        # Google Cloud variants
        "Google Cloud Platform": "Google Cloud",
        "Google Cloud Platform/App Engine": "Google Cloud",
        "Google Cloud": "Google Cloud",

        # Azure variants
        "Microsoft Azure": "Azure",

        # macOS / Mac OS variants
        "Mac OS": "macOS",
        "MacOS": "macOS",

        # Desktop / Server -> canonical OS
        "Linux Desktop": "Linux",
        "Windows Desktop": "Windows",
        "Windows Desktop or Server": "Windows",

        # IBM Cloud variants
        "IBM Cloud Or Watson": "IBM Cloud",
        "IBM Cloud or Watson": "IBM Cloud",

        # Linode phrasing
        "Linode, now Akamai": "Linode",

        # Slack integrations
        "Slack Apps and Integrations": "Slack",

        # Oracle Cloud variants
        "Oracle Cloud Infrastructure (OCI)": "Oracle Cloud Infrastructure",

        # Misc
        "Other(s):": "Other",
    }

    # 4) Webframe
    webframe_mapping = {
        # ASP.NET casing normalization
        "ASP.NET CORE": "ASP.NET Core",

        # Angular / AngularJS variants (keep Angular (2+) separate from AngularJS (1.x))
        "Angular.js": "AngularJS",
        "Angular/Angular.js": "AngularJS",

        # React variant
        "React.js": "React",

        # Spring Boot -> Spring
        "Spring Boot": "Spring",

        # Torch/PyTorch -> PyTorch
        "Torch/PyTorch": "PyTorch",

        # Generic catch-all
        "Other(s):": "Other",
    }

    # 5) MiscTech（激进版）
    misctech_mapping = {
        # .NET family normalizations
        ".NET": ".NET (5+)",
        ".NET Core": ".NET (5+)",
        ".NET Core / .NET 5": ".NET (5+)",
        ".NET (5+)": ".NET (5+)",
        ".NET Framework (1.0 - 4.8)": ".NET Framework",
        ".NET Framework": ".NET Framework",
        ".NET MAUI": ".NET (5+)",

        # casing / typos / duplicates
        "Scikit-Learn": "Scikit-learn",
        "Scikit-learn": "Scikit-learn",
        "Opencv": "OpenCV",
        "Teraform": "Terraform",
        "Torch/PyTorch": "PyTorch",
        "mlflow": "MLflow",
        "Unity 3D": "Unity",

        # Apache
        "Apache Spark": "Apache Spark/Kafka",
        "Apache Kafka": "Apache Spark/Kafka",

        # Spring
        "Spring Framework": "Spring",

        # catch-all
        "Other(s):": "Other"
    }

    # 6) ToolsTech
    toolstech_mapping = {
        # Compiler toolchains / frontends - normalize to common short names
        "GNU GCC": "GCC",
        "LLVM's Clang": "Clang",
        "MSVC": "Microsoft Visual C++ (MSVC)",

        # Build tools - remove explanatory parentheticals
        "Maven (build tool)": "Maven",
        "Visual Studio Solution": "Visual Studio",

        # Game engines / editors
        "Unity 3D": "Unity",
        "Unreal Engine": "Unreal Engine",  # keep but listed for clarity if you want "Unreal"

        # Package / system managers - normalize casing where seen as lowercase
        "bandit": "Bandit",
        "cppunit": "CppUnit",
        "doctest": "Doctest",
        "lest": "Lest",
        "liblittletest": "LibLittleTest",
        "snitch": "Snitch",
        "tunit": "TUnit",

        # Misc small normalizations / typos
        "Homebrew": "Homebrew",  # (example kept; remove if unchanged)
        "NuGet": "NuGet",  # (example kept; remove if unchanged)

        # catch-all
        "Other(s):": "Other"
    }

    # 7) CollabTools
    collabtools_mapping = {
        "Github": "GitHub",
        "Gitlab": "GitLab",
        "Goland": "GoLand",
        "IntelliJ": "IntelliJ IDEA",
        "Rad Studio (Delphi, C++ Builder)": "RAD Studio (Delphi, C++ Builder)",
        "PHPStorm": "PhpStorm",
        "Webstorm": "WebStorm",
        "IPython": "Jupyter",
        "IPython/Jupyter": "Jupyter",
        "Jupyter Notebook/JupyterLab": "Jupyter",
        "Google Suite (Docs, Meet, etc)": "Google Workspace",
        "Netbeans": "NetBeans",
        "condo": "Other",
        "Other(s):": "Other"
    }

    # ====== 原有各维度配置 ======

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

    # 依次构建 7 个维度的汇总表（直接生成“已经归一化 + 去重”的 raw 表）
    build_yearly_stats(conn, "language_usage_trend", language_config, separator=';', item_mapping=language_mapping)
    build_yearly_stats(conn, "database_usage_trend", database_config, separator=';', item_mapping=database_mapping)
    build_yearly_stats(conn, "platform_usage_trend", platform_config, separator=';', item_mapping=platform_mapping)
    build_yearly_stats(conn, "webframe_usage_trend", webframe_config, separator=';', item_mapping=webframe_mapping)
    build_yearly_stats(conn, "misctech_usage_trend", misc_tech_config, separator=';', item_mapping=misctech_mapping)
    build_yearly_stats(conn, "toolstech_usage_trend", tools_tech_config, separator=';', item_mapping=toolstech_mapping)
    build_yearly_stats(conn, "collabtools_usage_trend", collab_tools_config, separator=';', item_mapping=collabtools_mapping)

    conn.close()


if __name__ == "__main__":
    main()
