import plotly.express as px

def bk_item_popularity(df):
    # --- LA CORRECTION EST ICI ---
    # On transforme l'année en nombre entier (int) pour supprimer les .5 et les virgules
    df["Attribute"] = df["Attribute"].astype(int)
    
    top = df.nlargest(15, "Value")
    
    fig = px.bar(
        top, 
        x="Value", 
        y="item", 
        orientation="h", 
        color="Attribute",
        labels={"Value": "Valeur (€)", "item": "Produit", "Attribute": "Année"},
        # On force une échelle de couleurs discrète pour éviter les dégradés avec des virgules
        color_continuous_scale=px.colors.sequential.Blues
    )
    
    fig.update_layout(
        template="plotly_white", 
        height=500
    )

    # On force la légende à n'afficher que des nombres entiers
    fig.update_coloraxes(
        colorbar=dict(
            dtick=1,        # Un cran tous les 1 (2021, 2022, 2023)
            tickformat="d"  # "d" signifie entier (pas de virgules, pas de points)
        )
    )

    explanation = "Graphique mis à jour : les années sont désormais des nombres entiers."
    return fig, explanation