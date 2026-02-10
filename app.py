import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src.db import (
    build_where_clause,
    connect,
    get_distinct_values,
    get_row_count,
    get_table_schema,
    load_csv_to_table,
    preview_table,
    query_scalar,
)

# ---------------------------
# Config
# ---------------------------
st.set_page_config(
    page_title="Dashboard interactif – DuckDB & Streamlit",
    layout="wide",
)

st.title("📊 Dashboard interactif – DuckDB & Streamlit")
st.markdown(
    """
    Cette application vous permet de :
    - téléverser un fichier CSV,
    - stocker les données dans DuckDB,
    - explorer rapidement le contenu du dataset.
    """
)
st.divider()

# ---------------------------
# DB par session (anti-lock)
# ---------------------------
if "db_path" not in st.session_state:
    session_id = uuid.uuid4().hex[:10]
    temp_db = Path(tempfile.gettempdir())
    st.session_state["db_path"] = str(temp_db / f"streamlit_duckdb_{session_id}.duckdb")

conn = connect(Path(st.session_state["db_path"]))

# ---------------------------
# Upload
# ---------------------------
st.sidebar.header("⚙️ Paramètres")
uploaded_file: Optional[UploadedFile] = st.sidebar.file_uploader(
    "Téléverser un fichier CSV",
    type=["csv"],
)

if uploaded_file is None:
    st.info("👈 Commence par téléverser un fichier CSV depuis le menu de gauche.")
    st.stop()

assert uploaded_file is not None

with st.spinner("Chargement du fichier et ingestion dans DuckDB..."):
    temp_path = Path("uploaded_data.csv")
    temp_path.write_bytes(uploaded_file.getbuffer())
    load_csv_to_table(conn, temp_path)

st.success("✅ Fichier chargé avec succès dans DuckDB")

# ---------------------------
# Aperçu
# ---------------------------
row_count = get_row_count(conn)
c1, c2 = st.columns(2)
c1.metric("Nombre de lignes", row_count)
c2.metric("Nom de la table", "sales")

st.divider()
st.subheader("👀 Aperçu des données")
preview_df = preview_table(conn)
st.dataframe(preview_df, width="stretch")

# ---------------------------
# Filtres
# ---------------------------
st.divider()
st.subheader("🔎 Filtres (adaptés au dataset)")

schema: List[Tuple[str, str]] = get_table_schema(conn)
colonnes = {name: dtype for name, dtype in schema}

FilterValue = Union[str, List[str], float, Tuple[float, float]]
filtres: Dict[str, FilterValue] = {}

is_amazon = "product_id" in colonnes and "category" in colonnes

if is_amazon:
    st.sidebar.subheader("Filtres – Amazon")

    product_id = st.sidebar.text_input("Rechercher par product_id")
    if product_id:
        filtres["product_id"] = product_id

    categories = get_distinct_values(conn, "category")
    categories_short = {cat: cat.split("|")[-1] for cat in categories}

    selected_short = st.sidebar.multiselect(
        "Catégorie",
        options=sorted(set(categories_short.values())),
    )

    selected_full = [
        full for full, short in categories_short.items() if short in selected_short
    ]
    if selected_full:
        filtres["category"] = selected_full

    min_price, max_price = st.sidebar.slider(
        "Prix réel (actual_price)",
        min_value=0.0,
        max_value=100000.0,
        value=(0.0, 100000.0),
        step=10.0,
    )
    filtres["actual_price_range"] = (min_price, max_price)

    min_rating = st.sidebar.slider(
        "Note minimale",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.1,
    )
    filtres["min_rating"] = min_rating

# ---------------------------
# KPI + VISUALISATIONS
# ---------------------------
st.divider()
st.subheader("📊 Indicateurs clés (KPI) – Amazon")

where_clause = build_where_clause(filtres)

# KPI 1 – Nombre de produits
kpi_count = int(query_scalar(conn, f"SELECT COUNT(*) FROM sales {where_clause};"))
st.markdown("### Nombre de produits")
st.bar_chart({"Produits": [kpi_count]})

# KPI 2 – Prix moyen par catégorie
price_by_cat_df = conn.execute(
    f"""
    SELECT
        category,
        AVG(
            TRY_CAST(
                regexp_replace(actual_price, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            )
        ) AS avg_price
    FROM sales
    {where_clause}
    GROUP BY category
    ORDER BY avg_price DESC
    LIMIT 10;
    """
).fetch_df()

price_by_cat_df["category"] = price_by_cat_df["category"].apply(
    lambda x: x.split("|")[-1]
)

st.markdown("### Prix moyen réel par catégorie (Top 10)")
st.bar_chart(price_by_cat_df.set_index("category"))

# KPI 3 – Note moyenne par catégorie
rating_by_cat_df = conn.execute(
    f"""
    SELECT
        category,
        AVG(
            TRY_CAST(
                regexp_replace(rating, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            )
        ) AS avg_rating
    FROM sales
    {where_clause}
    GROUP BY category
    ORDER BY avg_rating DESC
    LIMIT 10;
    """
).fetch_df()

rating_by_cat_df["category"] = rating_by_cat_df["category"].apply(
    lambda x: x.split("|")[-1]
)

st.markdown("### Note moyenne par catégorie (Top 10)")
st.bar_chart(rating_by_cat_df.set_index("category"))

# KPI 4 – Réduction moyenne par tranche
discount_bucket_df = conn.execute(
    f"""
    SELECT
        CASE
            WHEN TRY_CAST(
                regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            ) < 10 THEN '< 10%'
            WHEN TRY_CAST(
                regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            ) < 30 THEN '10–30%'
            ELSE '> 30%'
        END AS discount_bucket,
        COUNT(*) AS nb_products
    FROM sales
    {where_clause}
    GROUP BY discount_bucket
    ORDER BY nb_products DESC;
    """
).fetch_df()

st.markdown("### Répartition des produits par niveau de réduction")
st.bar_chart(discount_bucket_df.set_index("discount_bucket"))
