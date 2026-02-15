import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

from src.db import (
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
st.set_page_config(page_title="Dashboard – Pilotage Data", layout="wide")

# ---------------------------
# Session init
# ---------------------------
if "db_path" not in st.session_state:
    session_id = uuid.uuid4().hex[:10]
    temp_db = Path(tempfile.gettempdir())
    st.session_state["db_path"] = str(temp_db / f"streamlit_duckdb_{session_id}.duckdb")

if "last_file_name" not in st.session_state:
    st.session_state["last_file_name"] = None

if "amazon_categories_map" not in st.session_state:
    st.session_state["amazon_categories_map"] = {}

if "bk_items" not in st.session_state:
    st.session_state["bk_items"] = []
if "bk_scopes" not in st.session_state:
    st.session_state["bk_scopes"] = []
if "bk_years" not in st.session_state:
    st.session_state["bk_years"] = []

if "mcd_headings" not in st.session_state:
    st.session_state["mcd_headings"] = []
if "mcd_items" not in st.session_state:
    st.session_state["mcd_items"] = []

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

file_name = uploaded_file.name

# ---------------------------
# Load once per file
# ---------------------------
if st.session_state["last_file_name"] != file_name:
    with st.spinner("Chargement du fichier..."):
        temp_path = Path(tempfile.gettempdir()) / "uploaded_data.csv"
        temp_path.write_bytes(uploaded_file.getbuffer())
        load_csv_to_table(conn, temp_path)

    st.session_state["last_file_name"] = file_name
    st.session_state["amazon_categories_map"] = {}
    st.session_state["bk_items"] = []
    st.session_state["bk_scopes"] = []
    st.session_state["bk_years"] = []
    st.session_state["mcd_headings"] = []
    st.session_state["mcd_items"] = []

# ---------------------------
# Header
# ---------------------------
st.title(f"📊 {file_name}")
st.markdown(
    "Dashboard de pilotage pour analyser la performance business : "
    "volumes, trajectoire temporelle et répartition."
)
st.divider()

# ---------------------------
# Aperçu
# ---------------------------
row_count = get_row_count(conn)
c1, c2 = st.columns(2)
c1.metric("Nombre de lignes", f"{row_count}")
c2.metric("Table active", "sales")

st.subheader("Aperçu des données")
preview_df = preview_table(conn)
st.dataframe(preview_df, width="stretch")

# ---------------------------
# Dataset detection
# ---------------------------
schema: List[Tuple[str, str]] = get_table_schema(conn)
cols = {name: dtype for name, dtype in schema}

is_amazon = "product_id" in cols and "category" in cols
is_bk = "Attribute" in cols and "global_us_usc" in cols and "Value" in cols
is_mcd = "heading" in cols and "Date" in cols and "Value" in cols

# ---------------------------
# Helpers
# ---------------------------


def sql_in_list(values: List[str]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"({joined})"


where_clause = ""

# ---------------------------
# Filters
# ---------------------------
if is_amazon:
    st.sidebar.subheader("Filtres – Amazon")

    if not st.session_state["amazon_categories_map"]:
        categories_full = get_distinct_values(conn, "category")
        short_to_full: Dict[str, List[str]] = {}
        for full in categories_full:
            short = full.split("|")[-1].strip()
            short_to_full.setdefault(short, []).append(full)
        st.session_state["amazon_categories_map"] = short_to_full

    amz_map = st.session_state["amazon_categories_map"]

    selected_short = st.sidebar.multiselect(
        "Catégories",
        options=sorted(amz_map.keys()),
    )

    min_price, max_price = st.sidebar.slider(
        "Prix réel (actual_price)",
        min_value=0.0,
        max_value=100000.0,
        value=(0.0, 100000.0),
        step=10.0,
    )

    min_rating = st.sidebar.slider(
        "Note minimale",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.1,
    )

    amz_parts: List[str] = []

    if selected_short:
        full_vals: List[str] = []
        for short in selected_short:
            full_vals.extend(amz_map.get(short, []))
        amz_parts.append(f"category IN {sql_in_list(full_vals)}")

    amz_parts.append(
        "TRY_CAST(regexp_replace(actual_price, '[^0-9\\.]', '', 'g') AS DOUBLE) "
        f"BETWEEN {min_price} AND {max_price}"
    )
    amz_parts.append(
        "TRY_CAST(regexp_replace(rating, '[^0-9\\.]', '', 'g') AS DOUBLE) "
        f">= {min_rating}"
    )

    where_clause = "WHERE " + " AND ".join(amz_parts)

elif is_bk:
    st.sidebar.subheader("Filtres – Burger King")

    if not st.session_state["bk_items"]:
        st.session_state["bk_items"] = get_distinct_values(conn, "item")
    if not st.session_state["bk_scopes"]:
        st.session_state["bk_scopes"] = get_distinct_values(conn, "global_us_usc")
    if not st.session_state["bk_years"]:
        st.session_state["bk_years"] = get_distinct_values(conn, "Attribute")

    bk_items: List[str] = st.session_state["bk_items"]
    bk_scopes: List[str] = st.session_state["bk_scopes"]
    bk_years: List[str] = st.session_state["bk_years"]

    bk_selected_items: List[str] = st.sidebar.multiselect(
        "Indicateurs",
        options=bk_items,
        default=bk_items,
        key="bk_items_select",
    )

    bk_selected_scopes: List[str] = st.sidebar.multiselect(
        "Périmètre",
        options=bk_scopes,
        default=bk_scopes,
        key="bk_scopes_select",
    )

    bk_selected_years: List[str] = st.sidebar.multiselect(
        "Années",
        options=bk_years,
        default=bk_years,
        key="bk_years_select",
    )

    bk_parts: List[str] = []

    if bk_selected_items:
        bk_parts.append(f"item IN {sql_in_list(bk_selected_items)}")
    if bk_selected_scopes:
        bk_parts.append(f"global_us_usc IN {sql_in_list(bk_selected_scopes)}")
    if bk_selected_years:
        bk_parts.append(f"Attribute IN {sql_in_list(bk_selected_years)}")

    where_clause = "WHERE " + " AND ".join(bk_parts) if bk_parts else ""

elif is_mcd:
    st.sidebar.subheader("Filtres – McDonald’s")

    if not st.session_state["mcd_headings"]:
        st.session_state["mcd_headings"] = get_distinct_values(conn, "heading")
    if not st.session_state["mcd_items"]:
        st.session_state["mcd_items"] = get_distinct_values(conn, "item")

    mcd_headings: List[str] = st.session_state["mcd_headings"]
    mcd_items: List[str] = st.session_state["mcd_items"]

    mcd_selected_headings: List[str] = st.sidebar.multiselect(
        "Domaines",
        options=mcd_headings,
        default=mcd_headings,
        key="mcd_headings_select",
    )

    mcd_selected_items: List[str] = st.sidebar.multiselect(
        "Indicateurs",
        options=mcd_items,
        default=mcd_items,
        key="mcd_items_select",
    )

    mcd_parts: List[str] = []

    if mcd_selected_headings:
        mcd_parts.append(f"heading IN {sql_in_list(mcd_selected_headings)}")
    if mcd_selected_items:
        mcd_parts.append(f"item IN {sql_in_list(mcd_selected_items)}")

    where_clause = "WHERE " + " AND ".join(mcd_parts) if mcd_parts else ""

else:
    st.warning("Dataset non reconnu (Amazon / BK / McD attendu).")
    st.stop()

# ---------------------------
# KPI sections
# ---------------------------
st.divider()

if is_amazon:
    st.subheader("📊 Indicateurs clés – Amazon")

    unique_products = int(
        query_scalar(
            conn,
            f"SELECT COUNT(DISTINCT product_id) FROM sales {where_clause};",
        )
    )

    unique_products_global = int(
        query_scalar(
            conn,
            "SELECT COUNT(DISTINCT product_id) FROM sales;",
        )
    )

    share_pct = 0.0
    if unique_products_global > 0:
        share_pct = (unique_products / unique_products_global) * 100

    c1, c2 = st.columns(2)
    c1.metric("1️⃣ Produits uniques (périmètre)", f"{unique_products}")
    c2.metric("2️⃣ Part du catalogue total", f"{share_pct:.1f}%")

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
                WHEN TRY_CAST(
                    regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                    AS DOUBLE
                ) < 10 THEN '<10%'
                WHEN TRY_CAST(
                    regexp_replace(discount_percentage, '[^0-9\\.]', '', 'g')
                    AS DOUBLE
                ) BETWEEN 10 AND 30 THEN '10-30%'
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
        order,
        ordered=True,
    )
    discount_df = discount_df.sort_values("discount_bucket")

    st.markdown("### 3️⃣ Positionnement prix (Top catégories)")
    st.markdown("Comparaison du prix moyen réel sur les catégories dominantes.")
    st.bar_chart(price_by_cat_df.set_index("category"))

    st.markdown("### 4️⃣ Qualité perçue (notes moyennes par catégorie)")
    st.markdown("Perception client moyenne par grande famille de produits.")
    st.bar_chart(rating_by_cat_df.set_index("category"))

    st.markdown("### 5️⃣ Politique de réduction")
    st.markdown("Répartition des produits selon l’intensité de remise.")
    st.bar_chart(discount_df.set_index("discount_bucket"))

elif is_bk:
    st.subheader("📊 Indicateurs clés – Burger King")

    total_value = query_scalar(
        conn,
        f"SELECT SUM(Value) FROM sales {where_clause};",
    )

    yearly_df = conn.execute(
        f"""
        SELECT
            CAST(Attribute AS INTEGER) AS year,
            SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY year
        ORDER BY year;
        """
    ).fetch_df()

    yoy = 0.0
    if len(yearly_df) >= 2:
        last_val = float(yearly_df.iloc[-1]["value"])
        prev_val = float(yearly_df.iloc[-2]["value"])
        if prev_val > 0:
            yoy = ((last_val - prev_val) / prev_val) * 100

    by_scope_df = conn.execute(
        f"""
        SELECT global_us_usc, SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY global_us_usc
        ORDER BY value DESC;
        """
    ).fetch_df()

    top_items_df = conn.execute(
        f"""
        SELECT item, SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY item
        ORDER BY value DESC
        LIMIT 10;
        """
    ).fetch_df()

    c1, c2 = st.columns(2)
    c1.metric("Volume total", f"{total_value:.1f}")
    c2.metric("Croissance YoY", f"{yoy:.1f}%")

    st.markdown("### 1️⃣ Évolution du volume (annuel)")
    st.markdown("Trajectoire annuelle de la valeur sur le périmètre sélectionné.")
    st.line_chart(yearly_df.set_index("year"))

    st.markdown("### 2️⃣ Répartition par périmètre")
    st.markdown("Part de valeur entre Global / US (selon la donnée).")
    st.bar_chart(by_scope_df.set_index("global_us_usc"))

    st.markdown("### 3️⃣ Top contributeurs (indicateurs)")
    st.markdown("Indicateurs qui concentrent le plus de valeur sur le périmètre.")
    st.bar_chart(top_items_df.set_index("item"))

elif is_mcd:
    st.subheader("📊 Indicateurs clés – McDonald’s")

    total_value = query_scalar(
        conn,
        f"SELECT SUM(Value) FROM sales {where_clause};",
    )

    yearly_df = conn.execute(
        f"""
        SELECT
            CAST(EXTRACT(YEAR FROM Date) AS INTEGER) AS year,
            SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY year
        ORDER BY year;
        """
    ).fetch_df()

    yoy = 0.0
    if len(yearly_df) >= 2:
        last_val = float(yearly_df.iloc[-1]["value"])
        prev_val = float(yearly_df.iloc[-2]["value"])
        if prev_val > 0:
            yoy = ((last_val - prev_val) / prev_val) * 100

    by_heading_df = conn.execute(
        f"""
        SELECT heading, SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY heading
        ORDER BY value DESC
        LIMIT 10;
        """
    ).fetch_df()

    top_items_df = conn.execute(
        f"""
        SELECT item, SUM(Value) AS value
        FROM sales
        {where_clause}
        GROUP BY item
        ORDER BY value DESC
        LIMIT 10;
        """
    ).fetch_df()

    c1, c2 = st.columns(2)
    c1.metric("Valeur totale", f"{total_value:.1f}")
    c2.metric("Croissance YoY", f"{yoy:.1f}%")

    st.markdown("### 1️⃣ Évolution de la valeur (annuel)")
    st.markdown("Trajectoire annuelle agrégée sur le périmètre sélectionné.")
    st.line_chart(yearly_df.set_index("year"))

    st.markdown("### 2️⃣ Répartition par domaine (heading)")
    st.markdown("Domaines qui concentrent le plus de valeur.")
    st.bar_chart(by_heading_df.set_index("heading"))

    st.markdown("### 3️⃣ Top contributeurs (indicateurs)")
    st.markdown("Indicateurs qui concentrent le plus de valeur.")
    st.bar_chart(top_items_df.set_index("item"))
