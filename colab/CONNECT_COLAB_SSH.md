# Connect Cursor to Colab via SSH (Run Heavy Models in Colab)

Use **Google Colab** for GPU compute (RL, DL, ML, US30 pipeline) while editing in **Cursor**. The Colab extension + SSH flow lets you keep your workspace in Cursor and run all heavy training/backtests on the Colab runtime.

---

## Prerequisites

- **Cursor** (or VS Code) with **Remote - SSH** extension
- **Google account** and [Google Colab](https://colab.research.google.com)
- Optional: **Colab extension** for Cursor/VS Code (e.g. “Google Colab” or “Colab”) for opening notebooks in Colab from the editor

---

## Option A: Colab Extension + Run in Browser

1. Install a **Colab extension** in Cursor (e.g. “Google Colab” from the marketplace).
2. Open the notebook (e.g. `colab/us30_model_research.ipynb` or `colab/run_rl_dl_ml_colab.ipynb`).
3. Use the extension to **Open in Colab** (or upload the notebook to Colab).
4. In Colab: **Runtime → Change runtime type → GPU** (e.g. T4).
5. Run cells in the browser. Data and models can be saved to Drive (see notebook cells).

**Pros:** No SSH setup. **Cons:** You edit in Cursor but run in the browser; no single “remote terminal” in Cursor.

---

## Option B: SSH into Colab (Cursor as Full Remote Dev)

This gives you a **remote workspace in Cursor** where the filesystem and terminal are the Colab runtime. All commands (e.g. `python`, `pip`, training scripts) run on Colab.

### Step 1: Start Colab and open a notebook

1. Go to [colab.research.google.com](https://colab.research.google.com).
2. **Runtime → Change runtime type → GPU** (T4).
3. New notebook or open e.g. `colab/setup_colab.ipynb` (upload if needed).

### Step 2: Install colab-ssh and launch SSH

In a Colab cell, run:

```python
!pip install colab-ssh --upgrade -q
```

Then (set a password you’ll use to log in):

```python
from colab_ssh import launch_ssh_cloudflared
launch_ssh_cloudflared(password="YOUR_PASSWORD")
```

Colab will print something like:

```text
Connect to the server using:
  ssh root@<something>.trycloudflare.com
```

Copy the full `ssh root@...` line.

### Step 3: (Optional) Clone repo and install deps on Colab

In another Colab cell (or after SSH, in the remote terminal):

```bash
# If you prefer project on Drive (persists across sessions)
# First in Colab: run a cell with: from google.colab import drive; drive.mount("/content/drive")
git clone https://github.com/YOUR_USER/claude.git /content/claude
cd /content/claude
pip install -r colab/requirements-colab.txt
```

Or clone to Drive:

```bash
git clone https://github.com/YOUR_USER/claude.git /content/drive/MyDrive/Alpha_FTE_Project
cd /content/drive/MyDrive/Alpha_FTE_Project
pip install -r colab/requirements-colab.txt
```

### Step 4: Connect Cursor via Remote-SSH

1. In Cursor: **Ctrl+Shift+P** (or Cmd+Shift+P) → **Remote-SSH: Connect to Host…**
2. Choose **Add New SSH Host…** and paste:

   ```text
   ssh root@<hostname>.trycloudflare.com
   ```

   (Use the hostname from Step 2; replace `<hostname>` with the actual value.)

3. Select the config file to update (e.g. `~/.ssh/config`).
4. Connect; when prompted, use the password from Step 2.
5. **File → Open Folder** and open `/content/claude` or `/content/drive/MyDrive/Alpha_FTE_Project` (or wherever you cloned the repo).

Your Cursor workspace is now on the Colab machine. The **integrated terminal** runs on Colab, so:

- `python -m src.edges.volume_based.volume_workflow`
- `pip install -r colab/requirements-colab.txt`
- `nvidia-smi`

all run on Colab’s GPU runtime.

### Step 5: Run the US30 workflow (heavy models)

From the **remote** terminal in Cursor (Colab):

```bash
cd /content/claude   # or your project path
pip install -r colab/requirements-colab.txt
```

Then either:

- **Notebook:** Open `colab/us30_model_research.ipynb` in Cursor and run cells (ensure kernel points to the remote Python), or  
- **Jupyter on Colab:** Start Jupyter in Colab and open the same notebook there:

  ```bash
  pip install jupyter -q
  jupyter notebook --allow-root --port=8888
  ```

  (Use port forwarding in Cursor if you want to use the UI.)

Or run the pipeline as a script: we can add a `colab/run_us30_pipeline.py` that runs the same steps as the notebook if you prefer not to use notebooks.

---

## Where to put the project on Colab

| Location                     | Use case                          |
|-----------------------------|------------------------------------|
| `/content/claude`           | Fast; lost when runtime is recycled |
| `/content/drive/MyDrive/...`| Persistent (Drive); survives disconnect |

For trained models and important outputs, save under **Google Drive** (e.g. `/content/drive/MyDrive/colab_us30_models` or `colab_models`). The notebook already uses a `SAVE_ROOT` that points to Drive when Drive is mounted.

---

## Summary

- **Workflow_colab.md** is implemented in **`colab/us30_model_research.ipynb`**: US30 data, preprocessing, feature engineering, walk-forward CV, ML/DL/RL comparison, and saving to Drive.
- **Colab extension:** Use “Open in Colab” for quick runs in the browser.
- **SSH (colab-ssh):** Use **Option B** when you want Cursor’s terminal and editor attached directly to Colab so that **all heavy model runs happen on Colab**, not on your local machine.

Once connected via SSH, the `.cursor/rules/colab-remote.mdc` rule applies: never run training locally; assume the terminal is remote (Colab).
