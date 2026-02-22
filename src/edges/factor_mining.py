"""Factor mining edge (XGBoost importance / autoencoder stub)."""
import pandas as pd
import numpy as np
from typing import List, Optional

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

def mine_factors(data_df: pd.DataFrame, target: str = "returns") -> List[str]:
    if not HAS_XGB or target not in data_df.columns:
        return list(data_df.columns[:5])
    X = data_df.drop(columns=[target], errors="ignore").fillna(0)
    y = data_df[target]
    model = XGBRegressor(n_estimators=100)
    model.fit(X, y)
    imp = model.feature_importances_
    return list(X.columns[np.argsort(imp)[-5:]])
