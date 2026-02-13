import streamlit as st
import pandas as pd

st.set_page_config(page_title="KPI Sales Dashboard", layout="wide")

st.title("📊 KPI Sales Dashboard")
st.write("Téléversez un fichier CSV pour commencer l'analyse.")

uploaded_file = st.file_uploader("Choisissez un fichier CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Aperçu des données")
    st.dataframe(df.head())
