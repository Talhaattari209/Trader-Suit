"""ML pattern classifier (Random Forest)."""
import numpy as np
from typing import Any, List

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def ml_pattern_classifier(
    X: np.ndarray, y: np.ndarray, n_estimators: int = 100, max_depth: int = 10
) -> Any:
    if not HAS_SKLEARN or len(X) < 10:
        return None
    rf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
    rf.fit(X, y)
    return rf


def detect_pattern_ml(model: Any, new_data: np.ndarray) -> int:
    if model is None or new_data is None or len(new_data) == 0:
        return 0
    pred = model.predict(new_data.reshape(1, -1) if new_data.ndim == 1 else new_data)
    return int(pred[0]) if hasattr(pred, "__getitem__") else 0
