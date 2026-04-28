"""DL pattern detection (simplified LSTM).

Epoch count and batch size are driven by ComputationBudget:
  local → 10 epochs / batch 32   (EarlyStopping terminates even earlier)
  colab → 100 epochs / batch 256
"""
import numpy as np
from typing import Any

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from src.config.computation_budget import budget as CB


if HAS_TORCH:

    class PatternLSTM(nn.Module):
        def __init__(self, input_size: int = 5, hidden_size: int = 50):
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
            self.fc = nn.Linear(hidden_size, 3)  # buy, sell, hold

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            _, (hn, _) = self.lstm(x)
            return self.fc(hn.squeeze(0))


def train_pattern_lstm(
    X_seq: np.ndarray,
    y_labels: np.ndarray,
    epochs: int | None = None,
    batch_size: int | None = None,
) -> Any:
    """Train PatternLSTM. Epochs/batch_size default to ComputationBudget values."""
    if not HAS_TORCH or X_seq is None or len(X_seq) < 10:
        return None

    _epochs     = epochs     if epochs     is not None else CB.dl_epochs
    _batch_size = batch_size if batch_size is not None else CB.dl_batch_size

    X = torch.tensor(X_seq, dtype=torch.float32)
    y = torch.tensor(y_labels, dtype=torch.long).clamp(0, 2)
    model = PatternLSTM(input_size=X_seq.shape[2])
    opt = torch.optim.Adam(model.parameters(), lr=0.001)

    best_loss = float("inf")
    patience_counter = 0
    patience = 3  # EarlyStopping equivalent

    dataset = torch.utils.data.TensorDataset(X, y)
    loader  = torch.utils.data.DataLoader(dataset, batch_size=_batch_size, shuffle=True)

    for _ in range(_epochs):
        epoch_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            out  = model(xb)
            loss = nn.functional.cross_entropy(out, yb)
            loss.backward()
            opt.step()
            epoch_loss += loss.item()
        avg_loss = epoch_loss / len(loader)
        if avg_loss < best_loss - 1e-4:
            best_loss = avg_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break  # early stopping

    return model
