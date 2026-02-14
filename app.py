import streamlit as st
import pandas as pd
import duckdb
import altair as alt

# ---------------------------------------------------------
# Configuration Streamlit
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard KPI – Multi‑Datasets", layout="wide")
st.title("Dashboard KPI – Amazon / Burger King / McDonald's")


# ---------------------------------------------------------
# Connexion DuckDB
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
    return duckdb.connect("sales.duckdb")

con = get_connection()


# ---------------------------------------------------------
# Nettoyage Amazon (basé sur TON dataset réel)
# ---------------------------------------------------------
def clean_amazon(df):

    # Prix : enlever ₹ + virgules → convertir en float
    price_cols = ["discounted_price", "actual_price"]
    for col in price_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("₹", "", regex=False)
                .str.replace(",", "", regex=False)  # virgule = milliers → on supprime
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Pourcentage : enlever % → convertir en float
    if "discount_percentage" in df.columns:
        df["discount_percentage"] = (
            df["discount_percentage"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        df["discount_percentage"] = pd.to_numeric(df["discount_percentage"], errors="coerce")

    # Rating : déjà au bon format (4.2)
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    # Rating count : enlever virgules → convertir en int
    if "rating_count" in df.columns:
        df["rating_count"] = (
            df["rating_count"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------
# Détection du dataset
# ---------------------------------------------------------
def detect_dataset(df):
    amazon_cols = {
        "product_id", "product_name", "category",
        "discounted_price", "actual_price", "discount_percentage",
        "rating", "rating_count", "about_product",
        "user_id", "user_name", "review_id",
        "review_title", "review_content", "img_link",
        "product_link"
    }

    bk_cols = {"item", "Attribute", "Value", "global_us_usc"}

    mcdo_cols = {"table_name", "heading", "item", "Date", "Value"}

    if amazon_cols.issubset(df.columns):
        return "amazon"
    if bk_cols.issubset(df.columns):
        return "bk"
    if mcdo_cols.issubset(df.columns):
        return "mcdo"
    return "unknown"


# ---------------------------------------------------------
# Upload du fichier
# ---------------------------------------------------------
uploaded_file = st.sidebar.file_uploader("Importer un fichier CSV", type=["csv"])

if not uploaded_file:
    st.info("Importe un fichier Amazon, Burger King ou McDo pour commencer.")
    st.stop()

df = pd.read_csv(uploaded_file)
df.columns = [c.strip() for c in df.columns]

dataset_type = detect_dataset(df)
st.sidebar.write(f"Dataset détecté : **{dataset_type.upper()}**")

# Stockage DuckDB
con.execute("DROP TABLE IF EXISTS data")
con.execute("CREATE TABLE data AS SELECT * FROM df")

st.subheader("Aperçu des données")
st.dataframe(df.head())


# ---------------------------------------------------------
# KPI + Visualisations selon dataset
# ---------------------------------------------------------

# ---------------- AMAZON ----------------
if dataset_type == "amazon":
    st.header("KPI Amazon")

    df = clean_amazon(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prix moyen réduit", f"{df['discounted_price'].mean():.2f}")
    col2.metric("Prix moyen réel", f"{df['actual_price'].mean():.2f}")
    col3.metric("Réduction moyenne (%)", f"{df['discount_percentage'].mean():.2f}")
    col4.metric("Note moyenne", f"{df['rating'].mean():.2f}")

    st.subheader("Répartition des catégories")
    chart = alt.Chart(df).mark_bar().encode(
        x="category:N",
        y="count():Q",
        color="category:N"
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Produits et liens")
    st.dataframe(df[["product_name", "product_link"]].head(20))


# ---------------- BURGER KING ----------------
elif dataset_type == "bk":
    st.header("KPI Burger King")

    col1, col2 = st.columns(2)
    col1.metric("Valeur moyenne", f"{df['Value'].mean():.2f}")
    col2.metric("Valeur max", f"{df['Value'].max():.2f}")

    st.subheader("Valeurs par item")
    chart = alt.Chart(df).mark_bar().encode(
        x="item:N",
        y="Value:Q",
        color="item:N"
    )
    st.altair_chart(chart, use_container_width=True)


# ---------------- MCDONALD'S ----------------
elif dataset_type == "mcdo":
    st.header("KPI McDonald's")

    df["Date"] = pd.to_datetime(df["Date"], errors="ignore")

    col1, col2 = st.columns(2)
    col1.metric("Valeur moyenne", f"{df['Value'].mean():.2f}")
    col2.metric("Valeur max", f"{df['Value'].max():.2f}")

    st.subheader("Évolution dans le temps")
    chart = alt.Chart(df).mark_line(point=True).encode(
        x="Date:T",
        y="Value:Q",
        color="item:N"
    )
    st.altair_chart(chart, use_container_width=True)


# ---------------- UNKNOWN ----------------
else:
    st.error("Dataset non reconnu. Vérifie les colonnes.")
