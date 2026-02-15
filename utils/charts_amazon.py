import duckdb
import plotly.express as px
import pandas as pd

def get_db_connection(df):
    df = df.copy()

    numeric_cols = ["discounted_price", "rating", "rating_count", "discount_percentage"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    con = duckdb.connect(database=':memory:')
    con.register('sales_table', df)
    con.execute("CREATE TABLE sales AS SELECT * FROM sales_table")
    return con


def get_metrics_amazon(con, selected_cats):
    where_clause = ""
    if selected_cats:
        cats = "', '".join(selected_cats)
        where_clause = f"WHERE main_category IN ('{cats}')"

    query = f"""
        SELECT 
            COUNT(*)::INT as total_items,
            AVG(rating)::FLOAT as avg_rating,
            SUM(rating_count)::BIGINT as total_volume,
            AVG(discounted_price)::FLOAT as avg_price
        FROM sales
        {where_clause}
    """
    return con.execute(query).df().iloc[0]


def plot_bar_popularity(df):
    df = df.copy()
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")

    top_10 = df.nlargest(10, 'rating_count')

    fig = px.bar(
        top_10,
        x='rating_count',
        y='product_name',
        orientation='h',
        color_discrete_sequence=['#1d4ed8']
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        template="plotly_white",
        height=600
    )

    explanation = (
        "Ce graphique met en évidence les produits les plus populaires selon le volume d’avis. "
        "Un nombre élevé d’avis traduit une forte visibilité et un engagement client important."
    )

    return fig, explanation


def plot_price_vs_discount(df):
    df = df.copy()
    if "discounted_price" in df.columns:
        df["discounted_price"] = pd.to_numeric(df["discounted_price"], errors="coerce")
    if "discount_percentage" in df.columns:
        df["discount_percentage"] = pd.to_numeric(df["discount_percentage"], errors="coerce")
    if "rating_count" in df.columns:
        df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")

    df = df.dropna(subset=["discounted_price", "discount_percentage"])

    fig = px.scatter(
        df,
        x="discounted_price",
        y="discount_percentage",
        color="main_category" if "main_category" in df.columns else None,
        hover_name="product_name" if "product_name" in df.columns else None,
        size="rating_count" if "rating_count" in df.columns else None,
        title="Prix vs Remise (%)"
    )

    fig.update_layout(template="plotly_white", height=600)

    explanation = (
        "Ce nuage de points montre la relation entre le prix remisé et le pourcentage de remise. "
        "Il permet d’identifier les produits fortement remisés et de visualiser la stratégie tarifaire."
    )

    return fig, explanation


def plot_price_distribution(df):
    df = df.copy()

    # Nettoyage
    if "discounted_price" in df.columns:
        df["discounted_price"] = pd.to_numeric(df["discounted_price"], errors="coerce")

    df = df.dropna(subset=["discounted_price"])

    # Palette personnalisée
    custom_colors = ["#0A2A66", "#4DA6FF", "#E63946"]

    fig = px.histogram(
        df,
        x="discounted_price",
        nbins=50,
        histnorm="density",
        opacity=0.6,
        color="main_category" if "main_category" in df.columns else None,
        color_discrete_sequence=custom_colors,
        title="Distribution des prix (densité)"
    )

    fig.update_layout(
        template="plotly_white",
        height=500,
        xaxis_title="Prix remisé",
        yaxis_title="Densité"
    )

    explanation = (
        "Cette visualisation montre la distribution des prix sous forme de densité, "
        "avec la palette imposée (bleu foncé, bleu clair, rouge)."
    )

    return fig, explanation


def plot_category_rating(df):
    df = df.copy()

    # Nettoyage
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    if "main_category" not in df.columns:
        df["main_category"] = "Inconnue"

    # Agrégation
    df_group = df.groupby("main_category", as_index=False)["rating"].mean()
    df_group = df_group.sort_values("rating", ascending=False)

    # Palette personnalisée (bleu foncé, bleu clair, rouge)
    custom_colors = ["#0A2A66", "#4DA6FF", "#E63946"]

    fig = px.bar(
        df_group,
        x="main_category",
        y="rating",
        title="Note moyenne par catégorie",
        color="main_category",
        color_discrete_sequence=custom_colors
    )

    fig.update_layout(
        template="plotly_white",
        height=500,
        xaxis_title="Catégorie",
        yaxis_title="Note moyenne",
        showlegend=True  # ✔ légende réactivée
    )

    explanation = (
        "Ce graphique compare la satisfaction moyenne par catégorie. "
        "La palette personnalisée (bleu foncé, bleu clair, rouge) met en valeur les écarts de qualité."
    )

    return fig, explanation

