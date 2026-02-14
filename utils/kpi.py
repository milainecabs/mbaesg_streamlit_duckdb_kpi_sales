import streamlit as st
import pandas as pd

# -----------------------------
# KPI AMAZON
# -----------------------------
def show_kpi_amazon(df):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prix moyen réduit", f"{df['discounted_price'].mean():.2f}")
    col2.metric("Prix médian réduit", f"{df['discounted_price'].median():.2f}")
    col3.metric("Réduction moyenne (%)", f"{df['discount_percentage'].mean():.2f}")
    col4.metric("Note moyenne", f"{df['rating'].mean():.2f}")

    col5, col6 = st.columns(2)
    col5.metric("Produits > 4★", f"{(df['rating'] >= 4).mean()*100:.1f}%")
    col6.metric("Produit le plus évalué", df.loc[df['rating_count'].idxmax(), "product_name"])

    st.subheader("Top 5 produits les mieux notés")
    st.dataframe(df.sort_values("rating", ascending=False)[["product_name", "rating"]].head(5))

    st.subheader("Top 5 produits les plus évalués")
    st.dataframe(df.sort_values("rating_count", ascending=False)[["product_name", "rating_count"]].head(5))



# -----------------------------
# KPI BURGER KING
# -----------------------------
def show_kpi_bk(df: pd.DataFrame):
    col1, col2, col3 = st.columns(3)

    col1.metric("Valeur moyenne", f"{df['Value'].mean():.2f}")
    col2.metric("Valeur max", f"{df['Value'].max():.2f}")
    col3.metric("Valeur min", f"{df['Value'].min():.2f}")


# -----------------------------
# KPI MCDONALD'S
# -----------------------------
def show_kpi_mcdo(df: pd.DataFrame):
    df["Date"] = pd.to_datetime(df["Date"], errors="ignore")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Valeur moyenne", f"{df['Value'].mean():.2f}")
    col2.metric("Valeur max", f"{df['Value'].max():.2f}")
    col3.metric("Valeur min", f"{df['Value'].min():.2f}")

    # Variation entre première et dernière date
    df_sorted = df.sort_values("Date")
    if df_sorted["Value"].notna().sum() > 1:
        variation = df_sorted["Value"].iloc[-1] - df_sorted["Value"].iloc[0]
        col4.metric("Variation temporelle", f"{variation:.2f}")
    else:
        col4.metric("Variation temporelle", "N/A")
