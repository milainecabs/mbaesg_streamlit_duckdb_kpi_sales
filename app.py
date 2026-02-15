import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

from utils.cleaning_data import clean_data
from utils.detection import detect_dataset_type
from utils.charts_amazon import (
    get_db_connection,
    get_metrics_amazon,
    plot_bar_popularity,
    plot_price_vs_discount,
    plot_price_distribution,
    plot_category_rating
)
from utils.charts_mcdo import mcdo_generate_selected_graphs
from utils.charts_bk import bk_item_popularity

# --- CONFIGURATION PAGE ---
st.set_page_config(layout="wide", page_title="🏛️ Dashboard de ventes")

# --- CSS KPI GÉANTS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 20px;
        border: 2px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        transition: 0.3s;
        margin-bottom: 20px;
    }
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2);
    }
    .metric-label {
        color: #1e293b;
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .metric-value {
        color: #1d4ed8;
        font-size: 3.5rem;
        font-weight: 900;
        line-height: 1.1;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Dashboard de ventes")
st.divider()

# --- CHARGEMENT FICHIER ---
file = st.sidebar.file_uploader("📂 Charger un fichier CSV", type="csv")

if not file:
    st.info("Veuillez charger un fichier CSV pour commencer.")
    st.stop()

# Traitement initial
df_raw = pd.read_csv(file)
df_clean = clean_data(df_raw)
dataset_type = detect_dataset_type(df_clean)

st.sidebar.markdown(f"**Type détecté :** `{dataset_type}`")

# -----------------------------
# 🛒 AMAZON
# -----------------------------
if dataset_type == "amazon":
    st.header("🛒 Amazon – Analyse détaillée")

    if 'main_category' not in df_clean.columns and 'category' in df_clean.columns:
        df_clean['main_category'] = df_clean['category'].astype(str).str.split('|').str[0]

    con = get_db_connection(df_clean)
    categories = con.execute("SELECT DISTINCT main_category FROM sales").df()['main_category'].tolist()
    default_cats = categories[:3] if len(categories) >= 3 else categories

    selected = st.sidebar.multiselect("Filtrer les catégories", categories, default=default_cats)

    m = get_metrics_amazon(con, selected)

    df_final = con.execute(
        "SELECT * FROM sales WHERE main_category IN ?" if selected else "SELECT * FROM sales",
        [selected] if selected else []
    ).df()

    avg_discount = df_final["discount_percentage"].mean() if "discount_percentage" in df_final.columns else 0
    avg_reviews_per_item = df_final["rating_count"].mean() if "rating_count" in df_final.columns else 0

    # KPI Amazon
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    with c1:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Catalogue</p>'
            f'<p class="metric-value">{int(m["total_items"])}</p></div>',
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Satisfaction</p>'
            f'<p class="metric-value">{m["avg_rating"]:.2f}</p></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Prix Moyen</p>'
            f'<p class="metric-value">{m["avg_price"]:.0f}₹</p></div>',
            unsafe_allow_html=True)

    with c4:
        total_avis = f"{int(m['total_volume']):,}".replace(",", " ")
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Total Avis</p>'
            f'<p class="metric-value">{total_avis}</p></div>',
            unsafe_allow_html=True)
    with c5:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Remise Moy.</p>'
            f'<p class="metric-value">{avg_discount:.1f}%</p></div>',
            unsafe_allow_html=True)
    with c6:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Avis / Prod</p>'
            f'<p class="metric-value">{avg_reviews_per_item:.0f}</p></div>',
            unsafe_allow_html=True)

    # Graphes Amazon
    st.subheader("🏆 Popularité des Produits")
    fig, explanation = plot_bar_popularity(df_final)
    st.plotly_chart(fig, use_container_width=True)
    st.info(explanation)

    st.subheader("📉 Relation Prix vs Remise")
    fig_scatter, expl_scatter = plot_price_vs_discount(df_final)
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.info(expl_scatter)

    st.subheader("💰 Distribution des prix")
    fig_hist, expl_hist = plot_price_distribution(df_final)
    st.plotly_chart(fig_hist, use_container_width=True)
    st.info(expl_hist)

    st.subheader("🔥 Satisfaction par catégorie")
    fig_cat, expl_cat = plot_category_rating(df_final)
    st.plotly_chart(fig_cat, use_container_width=True)
    st.info(expl_cat)

# -----------------------------
# 🍟 MCDONALD'S (avec DuckDB)
# -----------------------------
elif dataset_type == "mcdo":
    st.header("🍟 McDonald's – Analyse stratégique")

    # Nettoyage McDo
    df_mcdo = df_clean.copy()
    df_mcdo["heading"] = df_mcdo["heading"].astype(str).str.strip()
    df_mcdo["item"] = df_mcdo["item"].astype(str).str.strip()
    df_mcdo["Date"] = pd.to_datetime(df_mcdo["Date"], errors="coerce")

    df_mcdo["Value"] = (
        df_mcdo["Value"]
        .astype(str)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df_mcdo["Value"] = pd.to_numeric(df_mcdo["Value"], errors="coerce")

    # Connexion DuckDB en mémoire
    con_mcdo = duckdb.connect(database=':memory:')
    con_mcdo.register("mcdo_df", df_mcdo)
    con_mcdo.execute("CREATE TABLE mcdo AS SELECT * FROM mcdo_df")

    # Filtres
    st.sidebar.subheader("Filtres McDo")
    all_headings = sorted(df_mcdo["heading"].unique())
    all_years = sorted(df_mcdo["Date"].dt.year.dropna().unique())

    selected_headings = st.sidebar.multiselect("Heading", all_headings, default=all_headings)
    selected_years = st.sidebar.multiselect("Année", all_years, default=all_years)

    selected_headings_sql = [str(h) for h in selected_headings]
    selected_years_sql = [int(y) for y in selected_years]

    df_filtered = con_mcdo.execute(
        """
        SELECT *
        FROM mcdo
        WHERE heading IN ?
          AND date_part('year', Date) IN ?
        """,
        [selected_headings_sql, selected_years_sql]
    ).df()

    kpi = con_mcdo.execute(
        """
        SELECT
            SUM(CASE WHEN item = 'total_revenue' THEN Value ELSE 0 END) AS total_revenue,
            SUM(CASE WHEN item = 'operating_income' THEN Value ELSE 0 END) AS operating_income,
            SUM(CASE WHEN item = 'net_income' THEN Value ELSE 0 END) AS net_income
        FROM mcdo
        WHERE heading IN ?
          AND date_part('year', Date) IN ?
        """,
        [selected_headings_sql, selected_years_sql]
    ).df().iloc[0]

    total_revenue = kpi["total_revenue"]
    operating_income = kpi["operating_income"]
    net_income = kpi["net_income"]

    c1, c2, c3 = st.columns(3)
    with c1:
        txt = f"{total_revenue:,.0f}".replace(",", " ")
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Chiffre d’affaires</p>'
            f'<p class="metric-value">{txt}</p></div>',
            unsafe_allow_html=True)
    with c2:
        txt = f"{operating_income:,.0f}".replace(",", " ")
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Résultat Op.</p>'
            f'<p class="metric-value">{txt}</p></div>',
            unsafe_allow_html=True)
    with c3:
        txt = f"{net_income:,.0f}".replace(",", " ")
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Résultat Net</p>'
            f'<p class="metric-value">{txt}</p></div>',
            unsafe_allow_html=True)

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    st.divider()
    graphs = mcdo_generate_selected_graphs(df_filtered)
    for heading, fig, explanation in graphs:
        st.subheader(f"📊 {heading}")
        st.plotly_chart(fig, use_container_width=True)
        st.info(explanation)

# -----------------------------
# 🍔 BURGER KING (avec DuckDB)
# -----------------------------
elif dataset_type == "burger_king":
    st.header("🍔 Burger King – Analyse détaillée")

    df_bk = df_clean.copy()
    df_bk["item"] = df_bk["item"].astype(str).str.strip()
    df_bk["Attribute"] = df_bk["Attribute"].astype(str).str.strip()
    df_bk["Value"] = pd.to_numeric(df_bk["Value"], errors="coerce")

    con_bk = duckdb.connect(database=':memory:')
    con_bk.register("bk_df", df_bk)
    con_bk.execute("CREATE TABLE bk AS SELECT * FROM bk_df")

    st.sidebar.subheader("Filtres Burger King")
    items = sorted(df_bk["item"].unique())
    attrs = sorted(df_bk["Attribute"].unique())

    selected_items = st.sidebar.multiselect("Items", items, default=items[:10] if len(items) > 10 else items)
    selected_attrs = st.sidebar.multiselect("Attributs", attrs, default=attrs)

    selected_items_sql = selected_items if selected_items else items
    selected_attrs_sql = selected_attrs if selected_attrs else attrs

    df_filtered_bk = con_bk.execute(
        """
        SELECT *
        FROM bk
        WHERE item IN ?
          AND Attribute IN ?
        """,
        [selected_items_sql, selected_attrs_sql]
    ).df()

    kpi_bk = con_bk.execute(
        """
        SELECT
            COUNT(DISTINCT item) AS n_items,
            COUNT(DISTINCT Attribute) AS n_attr,
            COUNT(*) AS n_rows
        FROM bk
        WHERE item IN ?
          AND Attribute IN ?
        """,
        [selected_items_sql, selected_attrs_sql]
    ).df().iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Items</p>'
            f'<p class="metric-value">{int(kpi_bk["n_items"])}</p></div>',
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Attributs</p>'
            f'<p class="metric-value">{int(kpi_bk["n_attr"])}</p></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="metric-card"><p class="metric-label">Entrées</p>'
            f'<p class="metric-value">{int(kpi_bk["n_rows"])}</p></div>',
            unsafe_allow_html=True)

    st.subheader("🔥 Popularité des Items")
    fig, explanation = bk_item_popularity(df_filtered_bk)
    st.plotly_chart(fig, use_container_width=True)
    st.info(explanation)

# -----------------------------
# ❓ AUTRE / ERREUR
# -----------------------------
else:
    st.error("Dataset non reconnu.")
    st.dataframe(df_clean)

# Section finale commune
with st.expander("🔎 Voir les données brutes"):
    if dataset_type == "amazon":
        st.dataframe(df_final)
    elif dataset_type == "mcdo":
        st.dataframe(df_filtered)
    elif dataset_type == "burger_king":
        st.dataframe(df_filtered_bk)
