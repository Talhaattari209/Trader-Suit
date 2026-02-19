# Deployment & Infrastructure

## Docker (local)

```bash
docker-compose up -d
# Or run once: docker-compose run --rm app python run_killer_agent.py
```

## GCP Cloud Run

1. Build and push image to Artifact Registry:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/ai-employee
   ```
2. Deploy:
   ```bash
   gcloud run deploy ai-employee --image gcr.io/PROJECT_ID/ai-employee \
     --platform managed --region us-central1 --allowunauthenticated
   ```
3. Set env vars (VAULT_PATH, ANTHROPIC_API_KEY, US30_CSV_PATH) in Cloud Run console or via `--set-env-vars`.
4. For persistent vault, use a Cloud Storage bucket mounted via sidecar or copy at startup.

## GCP VM

1. Create a VM (e.g. e2-small), install Docker.
2. Clone repo, copy `AI_Employee_Vault` and data as needed.
3. Run with docker-compose or systemd:
   ```bash
   docker-compose up -d
   ```
4. Optionally attach a persistent disk for vault and accounting data.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`/`master`:

- Unit tests: `pytest tests/`
- Monte Carlo sanity check: `simulate_paths` and `prob_of_ruin` validation

Add branch protection to require CI pass before merge.
