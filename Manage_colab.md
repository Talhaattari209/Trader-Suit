To set up your Cursor agent (the "Composer" or "Agent" mode) to handle the Heavy AI training on Colab while you code locally, you need to provide it with a **System Instruction** or a **`.cursor/rules`** file.

This ensures the agent doesn't try to run heavy training on your local laptop and instead manages the Colab remote environment correctly.

### The "Cursor Agent" Specification

Copy and paste this into a new file in your project root called `.cursor/rules/colab-remote.mdc` (or add it to your global "Rules for AI" in Settings):

```markdown
# Role: AI Research Engineer (Remote Colab Specialist)

## Context
I am working on RL/DL models using a local Cursor IDE connected to a Google Colab T4 GPU via SSH. My local machine is for development; the Colab instance is for compute.

## Environment Specs
- **Remote OS:** Ubuntu (Colab Runtime)
- **Primary GPU:** NVIDIA T4 (standard Colab)
- **Connection:** SSH Tunnel (via colab-ssh or cloud-flared)
- **Local Path:** Always relative to the workspace root.
- **Remote Path:** `/content/drive/MyDrive/Alpha_FTE_Project/` (assuming Drive mount).

## Behavior Guidelines
1. **Never Run Training Locally:** If I ask to "train" or "run the model," always execute the command in the integrated terminal which is connected to the SSH host.
2. **Dependency Management:** When adding new libraries (like `torch`, `stable-baselines3`, `gymnasium`), use `pip install` on the remote terminal.
3. **Data Handling:** - Direct the code to save checkpoints and logs to `/content/drive/MyDrive/...` to ensure persistence if the Colab session disconnects.
   - Use `pathlib` for all path manipulations to ensure cross-platform compatibility between my local Windows/Mac and Colab's Linux.
4. **Hardware Awareness:**
   - Always include code snippets to check for GPU availability: `device = "cuda" if torch.cuda.is_available() else "cpu"`.
   - Use `pin_memory=True` and `num_workers` in DataLoaders to optimize the Colab T4 throughput.

## Command Templates
- **To Start Training:** `python src/train.py --config configs/base.yaml`
- **To Monitor GPU:** `watch -n 1 nvidia-smi`
- **To Mount Drive (if script fails):** `from google.colab import drive; drive.mount('/content/drive')`

```

---

### How to use this with Cursor Agent

Once you have defined these rules, you can give the Agent high-level tasks in the **Composer (Ctrl+I)**:

* **Task 1:** *"Agent, set up a Stable Baselines3 PPO script for my US30 trading environment. Make sure it saves logs to my mounted Google Drive so I don't lose progress."*
* **Task 2:** *"Check the remote Colab environment and install any missing dependencies from my `requirements.txt`."*
* **Task 3:** *"Refactor my `train.py` to use a Spot Instance-friendly checkpointing system (saving every 1000 steps)."*

### Critical Setup Tip for "Cursor" specifically:

When you open Cursor, make sure you have used the **"Remote-SSH: Connect to Host"** command first. Once the bottom-left corner of Cursor says **"SSH: [Your-Colab-IP]"**, the Cursor Agent will automatically "see" the Colab file system and terminal as its primary workspace.

**Would you like me to generate a robust `train.py` template that includes the auto-save features needed for Colab's 12-hour disconnect limit?**

---

## Plan: Colab extension + Remote SSH (compute in Colab, stay in Cursor)

Use this when you want to **stay in Cursor** while **compute runs on Colab** via the Colab extension and Remote-SSH.

### Prerequisites
- [ ] **Cursor** with **Remote - SSH** extension installed.
- [ ] **Colab extension** (or manual colab-ssh / cloud-flared) to expose Colab as an SSH host.
- [ ] Colab runtime with **GPU** (Runtime → Change runtime type → GPU).
- [ ] Google Drive mounted on Colab at `/content/drive` (for persistent project and checkpoints).

### One-time setup on Colab

1. **Create a Colab notebook** that you use only for SSH + Drive:  
   - In a cell: mount Drive (`from google.colab import drive; drive.mount('/content/drive')`).  
   - In another cell: run your **Colab extension / colab-ssh** setup so it prints the SSH command (e.g. `ssh -p 22 root@...` or the host name the extension gives you).  
   - Optional: clone this repo into Drive so the project lives at `/content/drive/MyDrive/Alpha_FTE_Project/` (or your chosen path):
     ```bash
     !git clone https://github.com/YOUR_USER/claude.git /content/drive/MyDrive/Alpha_FTE_Project
     ```
   - Keep this notebook open (and the runtime alive) whenever you want to use Cursor against Colab.

2. **Add the Colab host to Cursor’s SSH config** (if not already):  
   - Command Palette → **Remote-SSH: Open SSH Configuration File**.  
   - Add a host entry using the hostname/port from the Colab extension (e.g. `Host colab-gpu`, `HostName ...`, `Port ...`, `User root`).

### Cursor workflow (every session)

1. **Connect Cursor to Colab**  
   - Command Palette → **Remote-SSH: Connect to Host** → choose your Colab host.  
   - Wait until the status bar shows **SSH: &lt;your-colab-host&gt;**.

2. **Open the project folder on the remote**  
   - **File → Open Folder** → `/content/drive/MyDrive/Alpha_FTE_Project` (or the path where the repo lives on Colab).  
   - All editing and the integrated terminal are now on the Colab machine.

3. **Run heavy work in the terminal**  
   - Open the integrated terminal in Cursor; it’s already the Colab environment.  
   - Install deps: `pip install -r requirements.txt` or `pip install -r colab/requirements-colab.txt`.  
   - Run training/scripts: e.g. `python -m src.edges.volume_based.volume_workflow`, or whatever entrypoint you use.  
   - The Cursor agent (with `.cursor/rules/colab-remote.mdc`) will suggest commands for this **remote** terminal, not for local.

4. **Persistence**  
   - Code: lives in the folder you opened (ideally on Drive: `/content/drive/MyDrive/Alpha_FTE_Project/`).  
   - Checkpoints/logs: configure your scripts to write under the same Drive path (e.g. `outputs/`, `checkpoints/`) so they survive Colab disconnects.

### What the agent does (colab-remote rule)

- The rule in **`.cursor/rules/colab-remote.mdc`** tells the agent to:
  - **Never** run training locally; always assume the terminal is the Colab (SSH) host when you’re connected.
  - Use `pip install` and `python` in the integrated terminal (remote).
  - Prefer saving outputs to Drive paths and using `pathlib` for paths.
  - Use GPU-aware code (`cuda` if available, `pin_memory`, etc.).

### Optional: syncing local ↔ Colab

- **Option A – Work only on remote:** Edit only in Cursor when connected via Remote-SSH; no extra sync (project is on Drive).  
- **Option B – Repo on GitHub:** On Colab, clone/pull the repo into the Drive folder; open that folder in Cursor over SSH.  
- **Option C – Local edits:** If you sometimes edit locally, push to GitHub and on Colab run `git pull` in the project folder (or use a sync tool); then in Cursor, connect via SSH and open that folder.

### Quick checklist before training

- [ ] Colab runtime is on (not disconnected).
- [ ] Drive is mounted at `/content/drive`.
- [ ] Cursor status bar: **SSH: [Colab host]**.
- [ ] Opened folder = project root on Colab (e.g. `/content/drive/MyDrive/Alpha_FTE_Project`).
- [ ] Terminal in Cursor is the remote (Colab) shell; run `nvidia-smi` to confirm GPU if needed.