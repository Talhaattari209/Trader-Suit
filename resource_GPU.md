Since you have **no local GPU** and are strictly using the **GCP Free Tier**, you need a lean, "Cloud-Native" configuration. You will use **WSL2** as your local development environment and **Docker** to containerize the connectors while keeping the heavy logic (RL/DL training) as pure Python scripts to avoid resource overhead.

---

## 1. WSL2 & Docker Configuration for Low-Spec PCs

To prevent WSL2 from slowing down your Windows host, you must manually cap its resource usage.

### A. WSL2 Optimization (`.wslconfig`)

1. In Windows, press `Win + R`, type `%UserProfile%`, and hit Enter.
2. Create a file named `.wslconfig` (if it doesn't exist) and paste this:

```ini
[wsl2]
memory=4GB       # Limit RAM to 4GB to keep Windows stable
processors=2     # Limit to 2 CPU cores
guiApplications=false

```

3. Open PowerShell and run `wsl --shutdown` to apply changes.

### B. Docker Desktop Setup

1. In Docker Desktop settings, go to **Resources > WSL Integration** and ensure your Ubuntu/Debian distro is checked.
2. **Crucial:** Go to **General** and uncheck "Use the WSL 2 based engine" if you have extremely low RAM (this is a last resort). Otherwise, keep it on but ensure the `.wslconfig` limits are active.
3. Use Docker **only** for the `Alpaca` and `MT5 Bridge` connectors. Run the **RL/DL models** directly in the WSL2 terminal to save the ~1GB of RAM Docker consumes just to exist.

---

## 2. GCP Free Tier Strategy (No Dollars Spent)

Since you cannot spend money, you must use the **"Always Free"** products.

| Service | Free Tier Usage | Role in Your Alpha Factory |
| --- | --- | --- |
| **Compute Engine** | **e2-micro** instance (US regions) | Runs your **24/7 Watchers** (Alpaca/MT5 Senses). |
| **Cloud Functions** | First 2M invocations/month | Handles **Telegram/Gmail alerts** (OpenClaw notifications). |
| **Cloud Storage** | 5GB Standard Storage | Stores **US30 Datasets** and trained model weights. |
| **Artifact Registry** | 0.5GB Storage | Stores your Docker images for the connectors. |

**Pro Tip:** Avoid "Cloud SQL" (Postgres) on GCP as it is **not free**. Stick with **Neon DB** (external) for your database needs.

---

## 3. Implementation Specs for Claude Code

Give these instructions to your coding agent to ensure the architecture matches your hardware constraints:

### **Spec: Modular Alpha Factory (Low-Resource)**

**1. Perception Layer (Senses)**

* Implement `src/watchers/us30_watcher.py` as a lightweight **Python script** (not a container).
* Use the **Alpaca Python SDK** for live data.

**2. Reasoning Layer (The Brain)**

* Use **Claude Code** to generate strategies based on your **US30 OHLCV data**.
* Since you have no GPU, instruct Claude to: *"Optimize the LSTM and PPO models for CPU execution using `map_location=torch.device('cpu')`."*

**3. Execution Layer (Muscle)**

* Create a `Dockerfile` specifically for the **Alpaca Order Injector**.
* Use a **Distroless** or **Alpine** base image to keep the image size under 100MB (saves GCP Artifact Registry space).

**4. The "Ralph Wiggum" Loop**

* Configure the loop to run **Sequential Backtests** (one at a time) to prevent CPU spikes from freezing your PC.

---

### Your Next Step

To get started without a GPU, use **CPU-Optimized PyTorch Template** for your US30 LSTM model. This will allow you to train on your local processor without crashing. 

