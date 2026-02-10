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

with st.spinner("Chargement du fichier et ingestion dans DuckDB..."):
    temp_path = Path("uploaded_data.csv")
    assert uploaded_file is not None
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
is_bk_mcd = "item" in colonnes and "Value" in colonnes

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

elif is_bk_mcd:
    st.sidebar.subheader("Filtres – McDonald’s / Burger King")

    items = get_distinct_values(conn, "item")
    selected_items = st.sidebar.multiselect("Indicateur", options=items)
    if selected_items:
        filtres["item"] = selected_items

# ---------------------------
# Filtres affichables (métier)
# ---------------------------
st.markdown("### Filtres actifs (vue métier)")

filtres_affichables: Dict[str, FilterValue] = filtres.copy()

if "category" in filtres_affichables:
    categories_full = filtres_affichables["category"]
    if isinstance(categories_full, list):
        filtres_affichables["category"] = sorted(
            {cat.split("|")[-1] for cat in categories_full}
        )

if filtres_affichables:
    st.json(filtres_affichables)
else:
    st.info("Aucun filtre actif.")

# ---------------------------
# KPI
# ---------------------------
st.divider()
st.subheader("📊 Indicateurs clés (KPI)")

where_clause = build_where_clause(filtres)

if is_amazon:
    kpi_count = int(query_scalar(conn, f"SELECT COUNT(*) FROM sales {where_clause};"))

    avg_price = query_scalar(
        conn,
        f"""
        SELECT AVG(
            TRY_CAST(
                regexp_replace(actual_price, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            )
        )
        FROM sales
        {where_clause};
        """,
    )

    avg_rating = query_scalar(
        conn,
        f"""
        SELECT AVG(
            TRY_CAST(
                regexp_replace(rating, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            )
        )
        FROM sales
        {where_clause};
        """,
    )

    avg_discount = query_scalar(
        conn,
        f"""
        SELECT AVG(
            TRY_CAST(
                regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            )
        )
        FROM sales
        {where_clause};
        """,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nombre de produits", kpi_count)
    c2.metric("Prix moyen réel", round(avg_price, 2))
    c3.metric("Note moyenne", round(avg_rating, 2))
    c4.metric("Réduction moyenne (%)", round(avg_discount, 2))

    # ---------------------------
    # Distribution des prix
    # ---------------------------
    st.divider()
    st.subheader("💸 Distribution des prix")

    price_where_clause = where_clause
    if price_where_clause:
        price_where_clause = f"{price_where_clause} AND actual_price IS NOT NULL"
    else:
        price_where_clause = "WHERE actual_price IS NOT NULL"

    price_dist_df = conn.execute(
        f"""
        SELECT
            TRY_CAST(
                regexp_replace(actual_price, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            ) AS price
        FROM sales
        {price_where_clause};
        """
    ).fetch_df()

    price_dist_df = price_dist_df.dropna()

    st.bar_chart(price_dist_df["price"].value_counts().sort_index())

elif is_bk_mcd:
    total_value = query_scalar(
        conn,
        f"SELECT SUM(Value) FROM sales {where_clause};",
    )
    avg_value = query_scalar(
        conn,
        f"SELECT AVG(Value) FROM sales {where_clause};",
    )

    c1, c2 = st.columns(2)
    c1.metric("Valeur totale", round(total_value, 2))
    c2.metric("Valeur moyenne", round(avg_value, 2))
