def detect_dataset_type(df):
    cols = set(df.columns)

    amazon_cols = {"product_id", "product_name", "rating", "rating_count"}
    mcdo_cols = {"table_name", "heading", "item", "Value"}
    bk_cols = {"item", "Attribute", "Value"}

    if amazon_cols.issubset(cols):
        return "amazon"
    if mcdo_cols.issubset(cols):
        return "mcdo"
    if bk_cols.issubset(cols):
        return "burger_king"
    return "unknown"
