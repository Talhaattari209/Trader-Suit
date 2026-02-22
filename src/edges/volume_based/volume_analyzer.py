"""Volume ML/CNN for spike detection."""
import numpy as np
import pandas as pd
from typing import Any, Tuple

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def train_volume_classifier(
    df_reduced: pd.DataFrame,
) -> Tuple[Any, float, float, np.ndarray]:
    if not HAS_SKLEARN or "spike_label" not in df_reduced.columns:
        return None, 0.0, 0.0, np.array([])
    X = df_reduced.drop("spike_label", axis=1)
    y = df_reduced["spike_label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)
    preds = rf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    imp = rf.feature_importances_ if hasattr(rf, "feature_importances_") else np.zeros(X.shape[1])
    return rf, acc, prec, imp
