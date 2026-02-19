# AI Employee / Intelligence Layer + Post-Intelligence
FROM python:3.11-slim

WORKDIR /app

# System deps if needed (e.g. for MT5 later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run Ralph loop (override with docker-compose or run command)
ENV VAULT_PATH=/app/AI_Employee_Vault
ENV PYTHONPATH=/app
CMD ["python", "run_ralph.py"]
