# CUDA Implementation Plan (MT5 + ML/DL/RL)

## Objective
Accelerate HFT-side `performance_metric` computation and model training/inference paths while keeping MT5 execution stable and deterministic where required.

## Phase 1 - Baseline and Profiling (Day 1-2)
- Measure current latency and throughput:
  - MT5 fetch + feature engineering latency (p50/p95/p99).
  - `performance_metric` runtime per strategy and per portfolio batch.
  - DL training epoch time and RL timesteps/sec.
- Add a reproducible benchmark script that compares CPU vs CUDA on:
  - 10k, 100k, 1M returns points.
  - single-strategy and multi-strategy batches.
- Acceptance target:
  - Metric runtime >= 5x faster on CUDA for large batches.

## Phase 2 - CUDA Runtime Foundation (Day 2-3)
- Use `src/optimization/cuda_acceleration.py`:
  - `detect_cuda_runtime()`
  - `configure_torch_for_low_latency()`
  - `compute_performance_metrics(...)`
  - `dataframe_to_device_tensor(...)`
- Add environment flags:
  - `USE_CUDA=1`
  - `CUDA_METRICS_ENABLED=1`
  - `CUDA_INFERENCE_ENABLED=1`
- Keep automatic CPU fallback for reliability.

## Phase 3 - MT5 Connector Side (Day 3-5)
- Do not move MT5 API calls to CUDA (MT5 is CPU/IO bound DLL path).
- Accelerate the post-fetch path:
  - Convert OHLCV arrays from MT5 to contiguous float32.
  - Batch feature transforms into tensor operations.
  - If feature windows are fixed, keep warm buffers on GPU.
- Pipeline:
  - MT5 `copy_rates_from_pos` -> pandas/NumPy -> `dataframe_to_device_tensor(...)` -> GPU feature transforms -> strategy scoring.
- Acceptance target:
  - End-to-end signal generation latency improvement >= 20-35%.

## Phase 4 - Performance Metric Acceleration (Day 4-6)
- Replace CPU metric path with:
  - `compute_performance_metrics(returns, periods_per_year=..., risk_free_rate_annual=...)`
- Compute in batches per symbol/strategy to minimize host-device transfers.
- Return compact scalar dict to API/dashboard.
- Acceptance target:
  - Dashboard `/metrics` and backtest audit metric jobs consistently faster with identical values within tolerance.

## Phase 5 - DL/RL Training + Inference (Day 5-8)
- DL (`pattern_detector_dl.py`):
  - Move model and batches to `cuda`.
  - Enable mixed precision (`torch.autocast`) and GradScaler.
  - DataLoader tuning: `pin_memory=True`, tuned `num_workers`.
- RL (`volume_rl_agent.py`, `pattern_rl_agent.py`):
  - Ensure PPO policy/model uses CUDA device.
  - Increase rollout/batch sizes where GPU memory allows.
  - Profile env-step bottlenecks (many remain CPU-bound).
- Acceptance target:
  - DL epoch time >= 2-4x faster on T4/A10 class GPU.
  - RL training throughput meaningfully improved without reward degradation.

## Phase 6 - Validation, Safety, and Rollout (Day 8-10)
- Numeric validation:
  - Compare CPU vs CUDA metrics (`abs(delta) <= 1e-5` for most outputs).
- Trading safety:
  - If CUDA error/OOM occurs, auto-fallback to CPU and continue.
  - Keep order execution path unchanged and isolated from GPU exceptions.
- Deployment:
  - Staged rollout: paper mode -> low-risk live slice -> full enablement.

## Integration Checklist
- [ ] Import `configure_torch_for_low_latency()` during startup.
- [ ] Add a feature flag gate in orchestrator/entrypoint.
- [ ] Replace metric calculation calls with `compute_performance_metrics(...)`.
- [ ] Convert MT5 feature tensor path to `dataframe_to_device_tensor(...)`.
- [ ] Add benchmark + regression tests for CPU/CUDA parity.
- [ ] Add runtime telemetry (device used, latency, fallback count).
