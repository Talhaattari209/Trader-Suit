# Colab Environment for RL / DL / ML Heavy Models

Run compute-heavy Alpha Factory models (RL, DL, ML, Monte Carlo) on **Google Colab** using free GPU.

## Quick Start

1. **Open in Colab**  
   - Open [Google Colab](https://colab.research.google.com).  
   - **File → Upload notebook** and upload `setup_colab.ipynb`, then `run_rl_dl_ml_colab.ipynb`.  
   - Or clone the repo in Colab (see below) and open the notebooks from the `colab/` folder.

2. **Enable GPU**  
   - **Runtime → Change runtime type → Hardware accelerator → GPU** (T4 is free).  
   - Run the first notebook (`setup_colab.ipynb`) to clone the repo, install dependencies, and set `sys.path`.

3. **Run heavy models**  
   - Run `run_rl_dl_ml_colab.ipynb` to train/evaluate:
     - **RL**: Volume PPO, Pattern PPO (stable-baselines3)
     - **DL**: Pattern LSTM (PyTorch)
     - **ML**: Regime classifier (sklearn), pattern ML classifier
     - **Monte Carlo Pro**: Strategy robustness (10k+ iterations)

## File Layout

| File | Purpose |
|------|--------|
| `README.md` | This file |
| `requirements-colab.txt` | Pip dependencies for Colab (torch, sb3, gym, sklearn, etc.) |
| `setup_colab.ipynb` | One-time setup: GPU check, clone repo, `pip install`, `sys.path` |
| `run_rl_dl_ml_colab.ipynb` | Run all RL/DL/ML/Monte Carlo workloads with synthetic or uploaded data |

## Syncing Your Repo in Colab

**Option A – Clone from GitHub (if repo is on GitHub)**  
In `setup_colab.ipynb`, set `REPO_URL` to your repo and run the clone cell. No upload needed.

**Option B – Upload repo as ZIP**  
1. Zip your project (e.g. `claude` folder).  
2. In Colab: **Files → Upload** the zip.  
3. In the setup notebook, unzip into `/content/claude` and set `PROJECT_ROOT = "/content/claude"`.

**Option C – Google Drive**  
1. Mount Drive: `from google.colab import drive; drive.mount("/content/drive")`.  
2. Copy or clone the repo into e.g. `/content/drive/MyDrive/claude`.  
3. Set `PROJECT_ROOT` to that path so trained models can be saved to Drive.

## Saving Trained Models

- Colab disk is temporary. To keep models:
  - Save to **Google Drive** (mount Drive, set `PROJECT_ROOT` or a `--output-dir` under `/content/drive/MyDrive/...`).
  - Or download files after training: `files.download("model.pt")` / `files.download("model.zip")`.

## Requirements (Colab)

See `requirements-colab.txt`. Main packages:

- `torch` (use Colab’s GPU; pip will install CUDA build)
- `stable-baselines3`, `gym`
- `scikit-learn`, `pandas`, `numpy`

Optional: `gymnasium` (newer Gym API) if you switch from `gym` later.

## Zero-MQL / Agent Conventions

Execution logic stays in Python; notebooks are for **training and validation** of RL/DL/ML models and Monte Carlo. Production strategies remain in `src/models/` and are validated by the Killer agent (e.g. via Monte Carlo Pro).
