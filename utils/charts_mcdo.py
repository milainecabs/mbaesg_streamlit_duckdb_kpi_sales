import plotly.express as px
import pandas as pd

def prepare_mcdo(df):
    df = df.copy()

    df["heading"] = df["heading"].astype(str).str.strip()
    df["item"] = df["item"].astype(str)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

    return df


def mcdo_generate_selected_graphs(df):
    df = prepare_mcdo(df)

    graphs = []

    selected_headings = [
        "revenue",
        "operating_non_operating_results",
        "income_statement",
        "assets",
        "store_count"
    ]

    for heading in selected_headings:
        subset = df[df["heading"] == heading]

        if subset.empty:
            continue

        if subset["Date"].nunique() > 1:
            fig = px.line(
                subset,
                x="Date",
                y="Value",
                color="item",
                markers=True,
                title=f"{heading} – évolution"
            )
        else:
            fig = px.bar(
                subset,
                x="item",
                y="Value",
                color="item",
                title=f"{heading} – répartition"
            )

        fig.update_layout(template="plotly_white", height=500)

        explanation = (
            f"Analyse de l’indicateur **{heading}**. "
            f"Ce graphique montre l’évolution ou la répartition des valeurs associées."
        )

        graphs.append((heading, fig, explanation))

    df_rev = df[df["item"] == "total_revenue"]
    df_op = df[df["item"] == "operating_income"]

    if not df_rev.empty and not df_op.empty:
        df_merge = pd.merge(df_rev, df_op, on="Date", suffixes=("_rev", "_op"))

        fig_comp = px.line(
            df_merge,
            x="Date",
            y=["Value_rev", "Value_op"],
            markers=True,
            title="Revenue vs Operating Income"
        )
        fig_comp.update_layout(template="plotly_white", height=500)

        graphs.append((
            "Revenue vs Operating Income",
            fig_comp,
            "Comparaison directe entre le chiffre d’affaires et le résultat opérationnel."
        ))

    df_franchise = df[df["item"].str.contains("franchised_", case=False, na=False)]
    df_company = df[df["item"].str.contains("company_operated_", case=False, na=False)]

    if not df_franchise.empty and not df_company.empty:
        df_franchise_sum = df_franchise.groupby("Date")["Value"].sum().reset_index()
        df_company_sum = df_company.groupby("Date")["Value"].sum().reset_index()

        df_mix = pd.merge(df_franchise_sum, df_company_sum, on="Date", suffixes=("_franchise", "_company"))

        fig_mix = px.line(
            df_mix,
            x="Date",
            y=["Value_franchise", "Value_company"],
            markers=True,
            title="Franchise vs Company-operated Revenue"
        )
        fig_mix.update_layout(template="plotly_white", height=500)

        graphs.append((
            "Franchise vs Company-operated Revenue",
            fig_mix,
            "Comparaison entre les revenus franchisés et les restaurants opérés directement."
        ))

    df_rev_segments = df[df["heading"] == "revenue"]

    if not df_rev_segments.empty:
        df_latest = df_rev_segments[df_rev_segments["Date"] == df_rev_segments["Date"].max()]

        fig_pie = px.pie(
            df_latest,
            names="item",
            values="Value",
            title="Répartition des revenus par segment (année la plus récente)"
        )
        fig_pie.update_layout(template="plotly_white", height=500)

        graphs.append((
            "Revenue Breakdown",
            fig_pie,
            "Répartition des revenus par segment pour l’année la plus récente."
        ))

    return graphs