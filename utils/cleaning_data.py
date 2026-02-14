import pandas as pd
import re

NUMERIC_KEYWORDS = [
    'rating', 'ratings', 'stars', 'note',
    'count', 'avis', 'discount', 'price', 'prix', 'value'
]

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in df.columns:
        if any(k in col.lower() for k in NUMERIC_KEYWORDS):
            df[col] = (
                df[col]
                .astype(str)
                .apply(lambda x: re.sub(r'[^\d.\-]', '', x))
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df
