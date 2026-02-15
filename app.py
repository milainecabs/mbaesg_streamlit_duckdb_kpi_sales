import streamlit as st
import pandas as pd
from utils.cleaning_data import clean_data
from utils.charts_mcdo import mcdo_generate_selected_graphs

# --- CONFIGURATION PAGE ---
st.set_page_config(layout="wide", page_title="Dashboard McDonald's")

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
        font-size: 3rem;
        font-weight: 900;
        line-height: 1.1;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🍟 Dashboard de Performance McDonald's")
st.divider()

# --- CHARGEMENT FICHIER ---
file = st.sidebar.file_uploader("📂 Charger le CSV McDonald's", type="csv")

if not file:
    st.info("Veuillez charger le fichier CSV de McDonald's pour commencer.")
    st.stop()

# Traitement des données
df_raw = pd.read_csv(file)
df_clean = clean_data(df_raw)

# Préparation spécifique McDo
df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")
df_clean["Value"] = pd.to_numeric(df_clean["Value"], errors="coerce")

# --- FILTRES SIDEBAR ---
st.sidebar.subheader("Filtres d'analyse")
all_headings = sorted(df_clean["heading"].unique()) if "heading" in df_clean.columns else []
all_years = sorted(df_clean["Date"].dt.year.dropna().unique())

selected_headings = st.sidebar.multiselect("Catégories (Heading)", all_headings, default=all_headings)
selected_years = st.sidebar.multiselect("Années", all_years, default=all_years)

df_filtered = df_clean[
    df_clean["heading"].isin(selected_headings) &
    (df_clean["Date"].dt.year.isin(selected_years))
]

# --- CALCUL DES 6 MÉTRIQUES ---
total_revenue = df_filtered[df_filtered["item"] == "total_revenue"]["Value"].sum()
operating_income = df_filtered[df_filtered["item"] == "operating_income"]["Value"].sum()
net_income = df_filtered[df_filtered["item"] == "net_income"]["Value"].sum()

store_count = df_filtered[df_filtered["heading"] == "store_count"]["Value"].max()

total_assets = df_filtered[(df_filtered["heading"] == "assets") & (df_filtered["item"] == "total")]["Value"].sum()
total_liabilities = df_filtered[(df_filtered["heading"] == "liabilities") & (df_filtered["item"] == "total")]["Value"].sum()

# --- AFFICHAGE DES KPI ---
# Ligne 1 : Performance financière
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

# Ligne 2 : Structure et Bilan
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

# --- GRAPHIQUES ---
st.divider()
st.subheader("📊 Analyses Graphiques")
graphs = mcdo_generate_selected_graphs(df_filtered)

for heading, fig, explanation in graphs:
    with st.container():
        st.plotly_chart(fig, use_container_width=True)
        st.info(explanation)
        st.write("")

# --- DONNÉES BRUTES ---
with st.expander("🔎 Voir les données brutes McDonald's"):
    st.dataframe(df_filtered, use_container_width=True)