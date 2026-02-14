import plotly.express as px

def bk_item_popularity(df):
    top = df.nlargest(15, "Value")
    fig = px.bar(top, x="Value", y="item", orientation="h", color="Attribute")
    fig.update_layout(template="plotly_white", height=500)
    explanation = (
        "Ce graphique présente les items les plus performants chez Burger King. "
        "Une valeur élevée indique une forte popularité ou un volume de ventes important."
    )
    return fig, explanation
