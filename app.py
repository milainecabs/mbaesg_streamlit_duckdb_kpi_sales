import streamlit as st
import pandas as pd
import plotly.express as px

from utils.cleaning_data import clean_data
from utils.detection import detect_dataset_type
from utils.charts_amazon import get_db_connection, get_metrics_amazon, plot_bar_popularity
from utils.charts_mcdo import mcdo_generate_selected_graphs
from utils.charts_bk import bk_item_popularity

# --- CONFIGURATION PAGE ---
st.set_page_config(layout="wide", page_title="Dashboard Multi-Datasets")

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
        font-size: 3.5rem; /* Ajusté pour éviter les débordements */
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
        "SELECT * FROM sales WHERE main_category IN ?", [selected]
    ).df() if selected else df_clean

    avg_discount = df_final["discount_percentage"].mean() if "discount_percentage" in df_final.columns else 0
    avg_reviews_per_item = df_final["rating_count"].mean() if "rating_count" in df_final.columns else 0

    # KPI Amazon
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    with c1: st.markdown(f'<div class="metric-card"><p class="metric-label">Catalogue</p><p class="metric-value">{int(m["total_items"])}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><p class="metric-label">Satisfaction</p><p class="metric-value">{m["avg_rating"]:.2f}</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><p class="metric-label">Prix Moyen</p><p class="metric-value">{m["avg_price"]:.0f}₹</p></div>', unsafe_allow_html=True)
    
    with c4:
        total_avis = f"{int(m['total_volume']):,}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Total Avis</p><p class="metric-value">{total_avis}</p></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><p class="metric-label">Remise Moy.</p><p class="metric-value">{avg_discount:.1f}%</p></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="metric-card"><p class="metric-label">Avis / Prod</p><p class="metric-value">{avg_reviews_per_item:.0f}</p></div>', unsafe_allow_html=True)

    st.subheader("🏆 Popularité des Produits")
    fig, explanation = plot_bar_popularity(df_final)
    st.plotly_chart(fig, use_container_width=True)
    st.info(explanation)

# -----------------------------
# 🍟 MCDONALD'S
# -----------------------------
elif dataset_type == "mcdo":
    st.header("🍟 McDonald's – Analyse stratégique")

    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")
    df_clean["Value"] = pd.to_numeric(df_clean["Value"], errors="coerce")

    # Filtres
    st.sidebar.subheader("Filtres McDo")
    all_headings = sorted(df_clean["heading"].unique()) if "heading" in df_clean.columns else []
    all_years = sorted(df_clean["Date"].dt.year.dropna().unique())

    selected_headings = st.sidebar.multiselect("Heading", all_headings, default=all_headings)
    selected_years = st.sidebar.multiselect("Année", all_years, default=all_years)

    df_filtered = df_clean[
        df_clean["heading"].isin(selected_headings) &
        (df_clean["Date"].dt.year.isin(selected_years))
    ]

    # Calcul des 6 Métriques
    total_revenue = df_filtered[df_filtered["item"] == "total_revenue"]["Value"].sum()
    operating_income = df_filtered[df_filtered["item"] == "operating_income"]["Value"].sum()
    net_income = df_filtered[df_filtered["item"] == "net_income"]["Value"].sum()
    
    store_count = df_filtered[df_filtered["heading"] == "store_count"]["Value"].max()
    
    total_assets = df_filtered[(df_filtered["heading"] == "assets") & (df_filtered["item"] == "total")]["Value"].sum()
    total_liabilities = df_filtered[(df_filtered["heading"] == "liabilities") & (df_filtered["item"] == "total")]["Value"].sum()

    # Affichage des KPI
    c1, c2, c3 = st.columns(3)
    with c1:
        txt = f"{total_revenue:,.0f}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Chiffre d’affaires</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)
    with c2:
        txt = f"{operating_income:,.0f}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Résultat Op.</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)
    with c3:
        txt = f"{net_income:,.0f}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Résultat Net</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        txt = f"{store_count:,.0f}".replace(",", " ") if pd.notnull(store_count) else "0"
        st.markdown(f'<div class="metric-card"><p class="metric-label">Restaurants</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)
    with c5:
        txt = f"{total_assets:,.0f}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Actifs Totaux</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)
    with c6:
        txt = f"{total_liabilities:,.0f}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Passifs Totaux</p><p class="metric-value">{txt}</p></div>', unsafe_allow_html=True)

    # Graphes
    st.divider()
    graphs = mcdo_generate_selected_graphs(df_filtered)
    for heading, fig, explanation in graphs:
        st.subheader(f"📊 {heading}")
        st.plotly_chart(fig, use_container_width=True)
        st.info(explanation)

# -----------------------------
# 🍔 BURGER KING
# -----------------------------
elif dataset_type == "burger_king":
    st.header("🍔 Burger King – Analyse détaillée")

    st.sidebar.subheader("Filtres Burger King")
    items = sorted(df_clean["item"].unique())
    selected_items = st.sidebar.multiselect("Items", items, default=items[:10])
    
    df_filtered_bk = df_clean[df_clean["item"].isin(selected_items)]

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><p class="metric-label">Items</p><p class="metric-value">{df_filtered_bk["item"].nunique()}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><p class="metric-label">Attributs</p><p class="metric-value">{df_filtered_bk["Attribute"].nunique()}</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><p class="metric-label">Entrées</p><p class="metric-value">{len(df_filtered_bk)}</p></div>', unsafe_allow_html=True)

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