"""
CUDA acceleration utilities for MT5 + ML/DL/RL paths.

This module provides:
1) Safe CUDA runtime detection and PyTorch tuning.
2) GPU-backed performance metric computation (with CPU fallback).
3) Fast DataFrame -> tensor conversion for inference/training pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

try:
    import torch

    HAS_TORCH = True
except ImportError:  # pragma: no cover - handled by fallback behavior
    HAS_TORCH = False
    torch = None  # type: ignore[assignment]


@dataclass(frozen=True)
class CudaRuntimeConfig:
    enabled: bool
    device: str
    device_name: str | None
    supports_tf32: bool
    mixed_precision_dtype: str | None


def detect_cuda_runtime() -> CudaRuntimeConfig:
    """Return runtime CUDA capability flags with safe defaults."""
    if not HAS_TORCH:
        return CudaRuntimeConfig(
            enabled=False,
            device="cpu",
            device_name=None,
            supports_tf32=False,
            mixed_precision_dtype=None,
        )

    has_cuda = torch.cuda.is_available()
    if not has_cuda:
        return CudaRuntimeConfig(
            enabled=False,
            device="cpu",
            device_name=None,
            supports_tf32=False,
            mixed_precision_dtype=None,
        )

    major, _minor = torch.cuda.get_device_capability(0)
    supports_tf32 = major >= 8
    dtype = "float16"
    return CudaRuntimeConfig(
        enabled=True,
        device="cuda",
        device_name=torch.cuda.get_device_name(0),
        supports_tf32=supports_tf32,
        mixed_precision_dtype=dtype,
    )


def configure_torch_for_low_latency() -> CudaRuntimeConfig:
    """
    Configure torch CUDA kernels for throughput and stable latency.

    Safe to call multiple times; no-op when CUDA is unavailable.
    """
    cfg = detect_cuda_runtime()
    if not cfg.enabled:
        return cfg

    # Enable autotuner for fixed/mostly-fixed tensor shapes.
    torch.backends.cudnn.benchmark = True
    # Disable deterministic kernels for speed in non-regulated backtests/training.
    torch.backends.cudnn.deterministic = False
    if cfg.supports_tf32:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    return cfg


def _to_1d_float_tensor(values: Iterable[float] | np.ndarray | "torch.Tensor", device: str) -> "torch.Tensor":
    if HAS_TORCH and isinstance(values, torch.Tensor):
        return values.to(device=device, dtype=torch.float32).flatten()
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    return torch.from_numpy(arr).to(device=device)


def compute_performance_metrics(
    returns: Iterable[float] | np.ndarray | "torch.Tensor",
    *,
    periods_per_year: int = 252,
    risk_free_rate_annual: float = 0.0,
    use_cuda: bool = True,
) -> dict[str, float]:
    """
    Compute common performance metrics using GPU when available.

    Metrics:
    - sharpe
    - sortino
    - max_drawdown_pct
    - hit_rate
    - e_ratio (avg_win / abs(avg_loss))
    """
    if not HAS_TORCH:
        raise RuntimeError("PyTorch is required for compute_performance_metrics")

    cfg = detect_cuda_runtime()
    device = "cuda" if (use_cuda and cfg.enabled) else "cpu"

    r = _to_1d_float_tensor(returns, device=device)
    if r.numel() < 2:
        return {
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "hit_rate": 0.0,
            "e_ratio": 0.0,
        }

    eps = torch.tensor(1e-8, device=device, dtype=torch.float32)
    rf_per_period = risk_free_rate_annual / float(periods_per_year)
    excess = r - rf_per_period

    mean_excess = torch.mean(excess)
    std = torch.std(excess, unbiased=True)
    sharpe = (mean_excess / (std + eps)) * np.sqrt(periods_per_year)

    downside = torch.minimum(excess, torch.tensor(0.0, device=device))
    downside_std = torch.sqrt(torch.mean(downside.pow(2)))
    sortino = (mean_excess / (downside_std + eps)) * np.sqrt(periods_per_year)

    equity = torch.cumprod(1.0 + r, dim=0)
    peak = torch.cummax(equity, dim=0).values
    drawdown = (equity - peak) / (peak + eps)
    max_dd = torch.min(drawdown) * 100.0

    wins = r[r > 0]
    losses = r[r < 0]
    hit_rate = torch.mean((r > 0).float())
    avg_win = torch.mean(wins) if wins.numel() > 0 else torch.tensor(0.0, device=device)
    avg_loss = torch.mean(losses) if losses.numel() > 0 else torch.tensor(-1.0, device=device)
    e_ratio = avg_win / (torch.abs(avg_loss) + eps)

    return {
        "sharpe": float(sharpe.detach().cpu().item()),
        "sortino": float(sortino.detach().cpu().item()),
        "max_drawdown_pct": float(abs(max_dd.detach().cpu().item())),
        "hit_rate": float(hit_rate.detach().cpu().item()),
        "e_ratio": float(e_ratio.detach().cpu().item()),
    }


def dataframe_to_device_tensor(
    df: Any,
    feature_columns: list[str],
    *,
    use_cuda: bool = True,
    dtype: "torch.dtype" = None,
) -> "torch.Tensor":
    """
    Convert DataFrame feature columns to device tensor.

    Expected `df` to support `df[feature_columns].to_numpy(dtype=np.float32)`.
    """
    if not HAS_TORCH:
        raise RuntimeError("PyTorch is required for dataframe_to_device_tensor")

    if dtype is None:
        dtype = torch.float32
    cfg = detect_cuda_runtime()
    device = "cuda" if (use_cuda and cfg.enabled) else "cpu"

    arr = df[feature_columns].to_numpy(dtype=np.float32, copy=False)
    tensor = torch.from_numpy(arr).to(device=device, dtype=dtype, non_blocking=True)
    return tensor
