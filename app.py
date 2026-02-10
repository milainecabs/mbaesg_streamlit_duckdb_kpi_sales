import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
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
    page_title="Indicateurs clés – Amazon",
    layout="wide",
)

st.title("📊 Indicateurs clés – Amazon")
st.markdown(
    """
    Tableau de bord interactif permettant d’analyser l’offre Amazon selon :
    le volume de produits, le positionnement prix, la qualité perçue
    et la politique de réduction.
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
    "Téléverser un fichier CSV Amazon",
    type=["csv"],
)

if uploaded_file is None:
    st.info("👈 Téléverse le fichier Amazon depuis le menu de gauche.")
    st.stop()

assert uploaded_file is not None

st.info(f"📄 Fichier chargé : **{uploaded_file.name}**")

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
c1.metric("Nombre de lignes dans le CSV", row_count)
c2.metric("Nom de la table", "sales")

st.divider()
st.subheader("👀 Aperçu des données")
preview_df = preview_table(conn)
st.dataframe(preview_df, width="stretch")

# ---------------------------
# Filtres
# ---------------------------
st.divider()
st.subheader("🎛️ Filtres")

schema: List[Tuple[str, str]] = get_table_schema(conn)
colonnes = {name: dtype for name, dtype in schema}

FilterValue = Union[str, List[str], float, Tuple[float, float]]
filtres: Dict[str, FilterValue] = {}

is_amazon = "product_id" in colonnes and "category" in colonnes
if not is_amazon:
    st.error("Ce dashboard est prévu uniquement pour le dataset Amazon.")
    st.stop()

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
# Filtres actifs (vue métier)
# ---------------------------
st.subheader("🎯 Filtres actifs")

filtres_affichables = filtres.copy()

if "category" in filtres_affichables:
    categories_full: List[str] = list(filtres_affichables["category"])  # type: ignore
    filtres_affichables["category"] = sorted(
        {cat.split("|")[-1] for cat in categories_full}
    )

if filtres_affichables:
    st.json(filtres_affichables)
else:
    st.info("Aucun filtre actif.")

where_clause = build_where_clause(filtres)

# ---------------------------
# KPI
# ---------------------------
st.divider()
st.subheader("📊 Indicateurs clés")

# KPI 1 – Nombre de produits distincts
nb_produits = int(
    query_scalar(
        conn,
        f"SELECT COUNT(DISTINCT product_id) FROM sales {where_clause};",
    )
)

st.metric("Nombre de produits distincts", nb_produits)

# KPI 2 – Prix moyen par catégorie
st.subheader("Prix moyen réel par catégorie (Top 10)")
st.caption("Comparaison du positionnement prix entre catégories principales.")

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

st.bar_chart(price_by_cat_df.set_index("category"), width="stretch")

# KPI 3 – Note moyenne par catégorie
st.subheader("Note moyenne par catégorie (Top 10)")
st.caption("Niveau de satisfaction client par catégorie de produits.")

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

st.bar_chart(rating_by_cat_df.set_index("category"), width="stretch")

# KPI 4 – Répartition par niveau de réduction
st.subheader("Répartition des produits par niveau de réduction")
st.caption("Structure des remises appliquées aux produits Amazon.")

discount_df = conn.execute(
    f"""
    SELECT
        CASE
            WHEN TRY_CAST(
                regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            ) < 10 THEN '<10%'
            WHEN TRY_CAST(
                regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                AS DOUBLE
            ) <= 30 THEN '10-30%'
            ELSE '>30%'
        END AS discount_bucket,
        COUNT(*) AS nb_produits
    FROM sales
    {where_clause}
    GROUP BY discount_bucket;
    """
).fetch_df()

ordre = ["<10%", "10-30%", ">30%"]
discount_df["discount_bucket"] = pd.Categorical(
    discount_df["discount_bucket"],
    categories=ordre,
    ordered=True,
)
discount_df = discount_df.sort_values("discount_bucket")

st.bar_chart(discount_df.set_index("discount_bucket"), width="stretch")
