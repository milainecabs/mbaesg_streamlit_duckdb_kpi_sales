from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import duckdb
import pandas as pd


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """
    Crée une connexion DuckDB vers une base donnée.
    """
    return duckdb.connect(str(db_path), read_only=False)


def load_csv_to_table(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    table_name: str = "sales",
) -> None:
    query = f"""
    CREATE OR REPLACE TABLE {table_name} AS
    SELECT * FROM read_csv_auto('{csv_path.as_posix()}');
    """
    conn.execute(query)


def get_row_count(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = "sales",
) -> int:
    result = conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()
    return int(result[0]) if result else 0


def preview_table(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = "sales",
    limit: int = 5,
) -> pd.DataFrame:
    df_any = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit};").fetch_df()
    return cast(pd.DataFrame, df_any)


def get_table_schema(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = "sales",
) -> List[Tuple[str, str]]:
    result = conn.execute(f"DESCRIBE {table_name};").fetchall()
    return [(row[0], row[1]) for row in result]


def get_distinct_values(
    conn: duckdb.DuckDBPyConnection,
    column_name: str,
    table_name: str = "sales",
    limit: int = 200,
) -> List[str]:
    result = conn.execute(
        f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        LIMIT {limit};
        """
    ).fetchall()
    return [str(row[0]) for row in result]


def build_where_clause(filters: Dict[str, Any]) -> str:
    conditions: List[str] = []

    if "product_id" in filters:
        conditions.append(f"product_id = '{filters['product_id']}'")

    if "category" in filters:
        values = ", ".join(f"'{v}'" for v in filters["category"])
        conditions.append(f"category IN ({values})")

    if "actual_price_range" in filters:
        min_p, max_p = filters["actual_price_range"]
        conditions.append(
            "TRY_CAST(regexp_replace(actual_price, '[^0-9\\.]', '', 'g') "
            f"AS DOUBLE) BETWEEN {min_p} AND {max_p}"
        )

    if "min_rating" in filters:
        conditions.append(
            "TRY_CAST(regexp_replace(rating, '[^0-9\\.]', '', 'g') "
            f"AS DOUBLE) >= {filters['min_rating']}"
        )

    if "item" in filters:
        values = ", ".join(f"'{v}'" for v in filters["item"])
        conditions.append(f"item IN ({values})")

    if not conditions:
        return ""

    return "WHERE " + " AND ".join(conditions)


def query_scalar(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
) -> float:
    result = conn.execute(sql).fetchone()
    if result is None or result[0] is None:
        return 0.0
    return float(result[0])
