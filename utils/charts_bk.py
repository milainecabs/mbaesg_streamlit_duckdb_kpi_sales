import plotly.express as px
import pandas as pd

def bk_item_popularity(df):
    df = df.copy()

    if "Year" not in df.columns and "Attribute" in df.columns:
        df["Year"] = df["Attribute"].astype(int).astype(str)

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

    top = df.nlargest(15, "Value")

    fig = px.bar(
        top,
        x="Value",
        y="item",
        orientation="h",
        color="Year",
        color_continuous_scale="Blues"
    )

    fig.update_layout(
        template="plotly_white",
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )

    explanation = (
        "Ce graphique présente les items les plus performants chez Burger King. "
        "La couleur représente l’année, ce qui permet de visualiser l’évolution temporelle."
    )

    return fig, explanation
