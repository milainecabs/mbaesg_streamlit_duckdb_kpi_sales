import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Union

import streamlit as st

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
st.set_page_config(page_title="Dashboard – Amazon", layout="wide")

# ---------------------------
# Session init
# ---------------------------
if "db_path" not in st.session_state:
    session_id = uuid.uuid4().hex[:10]
    temp_db = Path(tempfile.gettempdir())
    st.session_state["db_path"] = str(temp_db / f"streamlit_duckdb_{session_id}.duckdb")

if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

if "last_file_name" not in st.session_state:
    st.session_state["last_file_name"] = None

if "categories_map" not in st.session_state:
    st.session_state["categories_map"] = {}

conn = connect(Path(st.session_state["db_path"]))

# ---------------------------
# Upload
# ---------------------------
st.sidebar.header("⚙️ Paramètres")
uploaded_file = st.sidebar.file_uploader("Téléverser un fichier CSV", type=["csv"])

if uploaded_file is None:
    st.title("📊 Dashboard interactif – DuckDB & Streamlit")
    st.info("👈 Téléverse un fichier CSV depuis le menu de gauche.")
    st.stop()

# ⬇️ À partir d’ici mypy sait que ce n’est plus None
file_name = uploaded_file.name

# ---------------------------
# Load data only once per file
# ---------------------------
if st.session_state["last_file_name"] != file_name:
    with st.spinner("Chargement du fichier et ingestion dans DuckDB..."):
        temp_path = Path(tempfile.gettempdir()) / "uploaded_data.csv"
        temp_path.write_bytes(uploaded_file.getbuffer())
        load_csv_to_table(conn, temp_path)

    st.session_state["last_file_name"] = file_name
    st.session_state["data_loaded"] = True
    st.session_state["categories_map"] = {}

# ---------------------------
# Header
# ---------------------------
st.title(f"📊 {file_name}")
st.markdown(
    "Tableau de bord de pilotage pour analyser l’offre Amazon selon : "
    "le volume réel de produits (uniques), le positionnement prix, "
    "la qualité perçue et la politique de réduction."
)
st.divider()

# ---------------------------
# Aperçu
# ---------------------------
row_count = get_row_count(conn)
c1, c2 = st.columns(2)
c1.metric("Nombre de lignes dans le fichier", f"{row_count}")
c2.metric("Table active", "sales")

st.subheader("👀 Aperçu des données")
preview_df = preview_table(conn)
st.dataframe(preview_df, width="stretch")

# ---------------------------
# Filtres (sidebar)
# ---------------------------
schema: List[Tuple[str, str]] = get_table_schema(conn)
colonnes = {name: dtype for name, dtype in schema}

filtres: Dict[str, Union[List[str], float, Tuple[float, float]]] = {}

is_amazon = "product_id" in colonnes and "category" in colonnes
if not is_amazon:
    st.warning("Ce dashboard est optimisé pour le dataset Amazon.")
    st.stop()

st.sidebar.subheader("Filtres – Amazon")

# --- Mapping catégories STABLE ---
if not st.session_state["categories_map"]:
    categories_full = get_distinct_values(conn, "category")

    short_to_full: Dict[str, List[str]] = {}
    for full in categories_full:
        short = full.split("|")[-1].strip()
        short_to_full.setdefault(short, []).append(full)

    st.session_state["categories_map"] = short_to_full

short_to_full = st.session_state["categories_map"]

selected_short = st.sidebar.multiselect(
    "Catégories",
    options=sorted(short_to_full.keys()),
)

if selected_short:
    filtres["category"] = [
        full for short in selected_short for full in short_to_full.get(short, [])
    ]

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
# KPI
# ---------------------------
st.divider()
st.subheader("📊 Indicateurs clés – Amazon (pilotage)")

where_clause = build_where_clause(filtres)

kpi_unique_products = int(
    query_scalar(
        conn,
        f"""
        SELECT COUNT(DISTINCT product_id)
        FROM sales
        {where_clause};
        """,
    )
)

kpi_unique_products_global = int(
    query_scalar(
        conn,
        """
        SELECT COUNT(DISTINCT product_id)
        FROM sales;
        """,
    )
)

share_pct = (
    (kpi_unique_products / kpi_unique_products_global) * 100
    if kpi_unique_products_global > 0
    else 0.0
)

price_by_cat_df = conn.execute(
    f"""
    SELECT
        category,
        ROUND(
            AVG(
                TRY_CAST(
                    regexp_replace(actual_price, '[^0-9\\.]', '', 'g')
                    AS DOUBLE
                )
            ),
            1
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

rating_by_cat_df = conn.execute(
    f"""
    SELECT
        category,
        ROUND(
            AVG(
                TRY_CAST(
                    regexp_replace(rating, '[^0-9\\.]', '', 'g')
                    AS DOUBLE
                )
            ),
            1
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

discount_df = conn.execute(
    f"""
    SELECT
        CASE
            WHEN TRY_CAST(regexp_replace(discount_percentage,
            '[^0-9\\.]', '', 'g') AS DOUBLE) < 10 THEN '<10%'
            WHEN TRY_CAST(regexp_replace(discount_percentage,
            '[^0-9\\.]', '', 'g') AS DOUBLE) BETWEEN 10 AND 30 THEN '10-30%'
            ELSE '>30%'
        END AS discount_bucket,
        COUNT(*) AS nb_products
    FROM sales
    {where_clause}
    GROUP BY discount_bucket;
    """
).fetch_df()

order = ["<10%", "10-30%", ">30%"]
discount_df["discount_bucket"] = discount_df["discount_bucket"].astype("category")
discount_df["discount_bucket"] = discount_df["discount_bucket"].cat.set_categories(
    order, ordered=True
)
discount_df = discount_df.sort_values("discount_bucket")

# ---------------------------
# Affichage KPI
# ---------------------------
c1, c2 = st.columns(2)
c1.metric("Produits uniques (périmètre)", f"{kpi_unique_products}")
c2.metric("Part du catalogue total", f"{share_pct:.1f}%")

st.markdown("### 1️⃣ Positionnement prix (Top catégories)")
st.markdown("Comparaison du prix moyen réel sur les catégories dominantes.")
st.bar_chart(price_by_cat_df.set_index("category"))

st.markdown("### 2️⃣ Qualité perçue (notes moyennes par catégorie)")
st.markdown("Perception client moyenne par grande famille de produits.")
st.bar_chart(rating_by_cat_df.set_index("category"))

st.markdown("### 3️⃣ Politique de réduction")
st.markdown("Répartition des produits selon l’intensité de remise.")
st.bar_chart(discount_df.set_index("discount_bucket"))
