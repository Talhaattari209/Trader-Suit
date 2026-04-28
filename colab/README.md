# Colab Environment for RL / DL / ML Heavy Models

Run compute-heavy Alpha Factory models (RL, DL, ML, Monte Carlo) on **Google Colab** using free GPU. You can run in the browser or **connect Cursor to Colab via SSH** so that editing and terminal both use the Colab runtime.

## Connect Cursor to Colab (SSH)

To run heavy models from Cursor with compute on Colab:

1. Read **[CONNECT_COLAB_SSH.md](CONNECT_COLAB_SSH.md)** for step-by-step instructions.
2. Use **colab-ssh** in a Colab notebook to get an `ssh root@...trycloudflare.com` command.
3. In Cursor: **Remote-SSH: Connect to Host** → paste that host → open your project folder on the Colab filesystem.
4. All terminal commands then run on Colab (GPU). Never run training locally when connected this way.

## Quick Start (browser)

1. **Open in Colab**  
   - Open [Google Colab](https://colab.research.google.com).  
   - **File → Upload notebook** and upload `setup_colab.ipynb`, then `run_rl_dl_ml_colab.ipynb` or `us30_model_research.ipynb`.  
   - Or clone the repo in Colab (see below) and open the notebooks from the `colab/` folder.

2. **Enable GPU**  
   - **Runtime → Change runtime type → Hardware accelerator → GPU** (T4 is free).  
   - Run the first notebook (`setup_colab.ipynb`) to clone the repo, install dependencies, and set `sys.path`.

3. **Run heavy models**  
   - **`run_rl_dl_ml_colab.ipynb`** — Project RL/DL/ML agents + Monte Carlo (synthetic or uploaded OHLCV).
   - **`us30_model_research.ipynb`** — US30 (^DJI) research pipeline from [Workflow_colab.md](../Workflow_colab.md): yfinance data, feature engineering, walk-forward CV, RF/SVM/LSTM/PPO comparison, MAE/RMSE/Sharpe.

## File Layout

| File | Purpose |
|------|--------|
| `README.md` | This file |
| `CONNECT_COLAB_SSH.md` | **Connect Cursor to Colab via SSH** (colab-ssh, Remote-SSH) |
| `requirements-colab.txt` | Pip dependencies (torch, sb3, gym, yfinance, pandas_ta, tensorflow, etc.) |
| `setup_colab.ipynb` | One-time setup: GPU check, clone repo, `pip install`, `sys.path` |
| `run_rl_dl_ml_colab.ipynb` | RL/DL/ML/Monte Carlo with synthetic or uploaded data |
| `us30_model_research.ipynb` | **US30 pipeline**: load ^DJI, preprocess, features, ML/DL/RL, compare, save to Drive |

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
