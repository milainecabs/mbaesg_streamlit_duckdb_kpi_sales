import duckdb


def init_db(df):
    con = duckdb.connect(database=':memory:')
    con.register('df_view', df)
    # On crée une table propre en s'assurant que les colonnes numériques sont bien typées
    con.execute("CREATE TABLE sales AS SELECT * FROM df_view")
    return con


def get_filtered_data(con, selected_cats):
    if not selected_cats:
        return con.execute("SELECT * FROM sales").df()

    # Sécurisation des noms de catégories pour SQL
    placeholder = ', '.join(['?'] * len(selected_cats))
    query = f"SELECT * FROM sales WHERE main_category IN ({placeholder})"
    return con.execute(query, selected_cats).df()