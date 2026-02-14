import duckdb
import plotly.express as px

def get_db_connection(df):
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
