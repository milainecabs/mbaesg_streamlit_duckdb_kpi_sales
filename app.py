import streamlit as st
import pandas as pd
import plotly.express as px

from utils.cleaning_data import clean_data
from utils.detection import detect_dataset_type
from utils.charts_amazon import get_db_connection, get_metrics_amazon, plot_bar_popularity
from utils.charts_mcdo import mcdo_generate_selected_graphs
from utils.charts_bk import bk_item_popularity


st.set_page_config(layout="wide", page_title="Dashboard Multi-Datasets")

# --- CSS KPI GÉANTS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        padding: 55px;
        border-radius: 22px;
        border: 2px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.15);
        transition: 0.3s;
        width: 100%;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: scale(1.10);
        box-shadow: 0 20px 30px -5px rgba(0,0,0,0.25);
    }
    .metric-label {
        color: #1e293b;
        font-size: 2rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 15px;
        white-space: nowrap;
    }
    .metric-value {
        color: #1d4ed8;
        font-size: 15vw;
        font-weight: 900;
        line-height: 1;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Dashboard de ventes")
st.divider()

file = st.sidebar.file_uploader("📂 Charger un fichier CSV", type="csv")

if not file:
    st.info("Veuillez charger un fichier CSV.")
    st.stop()

df_raw = pd.read_csv(file)
df_clean = clean_data(df_raw)
dataset_type = detect_dataset_type(df_clean)

st.sidebar.markdown(f"**Type détecté :** `{dataset_type}`")

# -----------------------------
# AMAZON
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

    avg_discount = df_final["discount_percentage"].mean()
    avg_reviews_per_item = df_final["rating_count"].mean()

    # --- KPI Amazon (3 par ligne) ---
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    with c1:
        st.markdown(f'<div class="metric-card"><p class="metric-label">Catalogue</p><p class="metric-value">{int(m["total_items"])}</p></div>', unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="metric-card"><p class="metric-label">Satisfaction</p><p class="metric-value">{m["avg_rating"]:.2f}</p></div>', unsafe_allow_html=True)

    with c3:
        st.markdown(f'<div class="metric-card"><p class="metric-label">Prix Moyen</p><p class="metric-value">{m["avg_price"]:.0f}₹</p></div>', unsafe_allow_html=True)

    with c4:
        total_avis = f"{int(m['total_volume']):,}".replace(",", " ")
        st.markdown(f'<div class="metric-card"><p class="metric-label">Total Avis</p><p class="metric-value">{total_avis}</p></div>', unsafe_allow_html=True)

    with c5:
        st.markdown(f'<div class="metric-card"><p class="metric-label">Remise Moyenne</p><p class="metric-value">{avg_discount:.1f}%</p></div>', unsafe_allow_html=True)

    with c6:
        st.markdown(f'<div class="metric-card"><p class="metric-label">Avis / Produit</p><p class="metric-value">{avg_reviews_per_item:.0f}</p></div>', unsafe_allow_html=True)

    # --- Graphe 1 : Popularité ---
    st.subheader("🏆 Popularité des Produits")
    fig, explanation = plot_bar_popularity(df_final)
    st.plotly_chart(fig, use_container_width=True)
    st.info(explanation)

    # --- Graphe 2 : Prix vs Satisfaction (corrigé NaN) ---
    st.subheader("📉 Relation Prix vs Satisfaction")

    df_scatter = df_final.dropna(subset=["rating", "discounted_price", "rating_count"])
    df_scatter = df_scatter[df_scatter["rating_count"] > 0]

    fig_scatter = px.scatter(
        df_scatter,
        x="discounted_price",
        y="rating",
        size="rating_count",
        color="main_category",
        hover_name="product_name",
        title="Prix vs Satisfaction"
    )

    fig_scatter.update_layout(template="plotly_white", height=600)
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.info("Ce graphique montre comment le prix influence la satisfaction.")

    with st.expander("🔎 Voir les données brutes"):
        st.dataframe(df_final)


# -----------------------------
# MCDONALD'S
# -----------------------------
# -----------------------------
# MCDONALD'S
# -----------------------------
elif dataset_type == "mcdo":
    st.header("🍟 McDonald's – Analyse stratégique")

    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")
    df_clean["Value"] = pd.to_numeric(df_clean["Value"], errors="coerce")

    # --- Filtres dans la sidebar ---
    st.sidebar.subheader("Filtres McDo")

    all_headings = sorted(df_clean["heading"].unique())
    all_items = sorted(df_clean["item"].unique())
    all_years = sorted(df_clean["Date"].dt.year.unique())

    selected_headings = st.sidebar.multiselect("Heading", all_headings, default=all_headings)
    selected_items = st.sidebar.multiselect("Item", all_items, default=all_items)
    selected_years = st.sidebar.multiselect("Année", all_years, default=all_years)

    df_filtered = df_clean[
        df_clean["heading"].isin(selected_headings) &
        df_clean["item"].isin(selected_items) &
        (df_clean["Date"].dt.year.isin(selected_years))
    ]

    # --- KPI McDo (6 KPI utiles) ---
    total_revenue = df_filtered[df_filtered["item"] == "total_revenue"]["Value"].sum()
    operating_income = df_filtered[df_filtered["item"] == "operating_income"]["Value"].sum()
    net_income = df_filtered[df_filtered["item"] == "net_income"]["Value"].sum()

    store_count = df_filtered[df_filtered["heading"] == "store_count"]["Value"].max()

    total_assets = df_filtered[(df_filtered["heading"] == "assets") & (df_filtered["item"] == "total")]["Value"].sum()
    total_liabilities = df_filtered[(df_filtered["heading"] == "liabilities") & (df_filtered["item"] == "total")]["Value"].sum()

    # Ligne 1
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><p class="metric-label">Chiffre d’affaires</p><p class="metric-value">{total_revenue:,.0f}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><p class="metric-label">Résultat Op.</p><p class="metric-value">{operating_income:,.0f}</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><p class="metric-label">Résultat Net</p><p class="metric-value">{net_income:,.0f}</p></div>', unsafe_allow_html=True)

    # Ligne 2
    c4, c5, c6 = st.columns(3)
    with c4: st.markdown(f'<div class="metric-card"><p class="metric-label">Restaurants</p><p class="metric-value">{store_count:,.0f}</p></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><p class="metric-label">Actifs Totaux</p><p class="metric-value">{total_assets:,.0f}</p></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="metric-card"><p class="metric-label">Passifs Totaux</p><p class="metric-value">{total_liabilities:,.0f}</p></div>', unsafe_allow_html=True)

    # --- Graphes McDo ---
    graphs = mcdo_generate_selected_graphs(df_filtered)

    for heading, fig, explanation in graphs:
        st.subheader(f"📊 {heading}")
        st.plotly_chart(fig, use_container_width=True)
        st.info(explanation)

    with st.expander("🔎 Voir les données brutes"):
        st.dataframe(df_filtered)

# -----------------------------
# BURGER KING
# -----------------------------
elif dataset_type == "burger_king":
    st.header("🍔 Burger King – Analyse détaillée")

    # --- Filtres dans la sidebar ---
    st.sidebar.subheader("Filtres Burger King")

    items = sorted(df_clean["item"].unique())
    attributes = sorted(df_clean["Attribute"].unique())

    selected_items = st.sidebar.multiselect("Item", items, default=items)
    selected_attributes = st.sidebar.multiselect("Attribut", attributes, default=attributes)

    df_filtered_bk = df_clean[
        df_clean["item"].isin(selected_items) &
        df_clean["Attribute"].isin(selected_attributes)
    ]

    # KPI
    total_items = df_filtered_bk["item"].nunique()
    total_attributes = df_filtered_bk["Attribute"].nunique()
    total_values = len(df_filtered_bk)

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><p class="metric-label">Items</p><p class="metric-value">{total_items}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><p class="metric-label">Attributs</p><p class="metric-value">{total_attributes}</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><p class="metric-label">Entrées</p><p class="metric-value">{total_values}</p></div>', unsafe_allow_html=True)

    # Graphe
    st.subheader("🔥 Popularité des Items")
    fig, explanation = bk_item_popularity(df_filtered_bk)
    st.plotly_chart(fig, use_container_width=True)
    st.info(explanation)

    with st.expander("🔎 Voir les données brutes"):
        st.dataframe(df_filtered_bk)


else:
    st.error("Dataset non reconnu.")
    st.dataframe(df_clean)
