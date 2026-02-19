# Google Secrets Manager Setup for OpenClaw Gateway

This guide sets up secure secrets management using Google Cloud Secrets Manager, so secrets survive container rebuilds and are never committed to git.

## Prerequisites

- `gcloud` CLI installed and authenticated
- Permissions to create secrets in your GCP project
- GCP project: `molt-chatbot` (or your custom `GCP_PROJECT`)

## Step 1: Create Secrets in GCP

Create each secret once (you'll reference them in deployments):

```bash
PROJECT="molt-chatbot"

# Discord bot token
echo "your-discord-token" | gcloud secrets create openclaw-discord-token \
  --data-file=- --project="$PROJECT" 2>/dev/null || \
  gcloud secrets versions add openclaw-discord-token --data-file=- --project="$PROJECT"

# Telegram bot token (optional)
echo "your-telegram-token" | gcloud secrets create openclaw-telegram-token \
  --data-file=- --project="$PROJECT" 2>/dev/null || \
  gcloud secrets versions add openclaw-telegram-token --data-file=- --project="$PROJECT"

# Azure OpenAI API key
echo "your-azure-key" | gcloud secrets create azure-openai-api-key \
  --data-file=- --project="$PROJECT" 2>/dev/null || \
  gcloud secrets versions add azure-openai-api-key --data-file=- --project="$PROJECT"

# Azure OpenAI host
echo "your-instance.openai.azure.com" | gcloud secrets create azure-openai-host \
  --data-file=- --project="$PROJECT" 2>/dev/null || \
  gcloud secrets versions add azure-openai-host --data-file=- --project="$PROJECT"

# Google API key (for BigQuery, YouTube, etc.)
echo "your-google-api-key" | gcloud secrets create google-api-key \
  --data-file=- --project="$PROJECT" 2>/dev/null || \
  gcloud secrets versions add google-api-key --data-file=- --project="$PROJECT"
```

## Step 2: Grant Permissions to Deploy User

If deploying from a Cloud Workstation or service account, grant `secretmanager.secretAccessor`:

```bash
PROJECT="molt-chatbot"
SERVICE_ACCOUNT="vmctl-admin@molt-chatbot.iam.gserviceaccount.com"

# Grant access to all openclaw secrets
for SECRET in openclaw-discord-token openclaw-telegram-token \
              azure-openai-api-key azure-openai-host google-api-key; do
    gcloud secrets add-iam-policy-binding "$SECRET" \
      --member="serviceAccount:$SERVICE_ACCOUNT" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT"
done
```

Or if deploying as a user:

```bash
PROJECT="molt-chatbot"
USER_EMAIL="your-email@example.com"

for SECRET in openclaw-discord-token openclaw-telegram-token \
              azure-openai-api-key azure-openai-host google-api-key; do
    gcloud secrets add-iam-policy-binding "$SECRET" \
      --member="user:$USER_EMAIL" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT"
done
```

## Step 3: Deploy with Secrets

Use the automated deploy script to fetch secrets and restart the container:

```bash
# Pull latest code
cd /srv/vmctl/agent/openclaw-gateway/repo
git pull origin main

# Run deploy (fetches secrets, rebuilds, restarts)
bash /srv/vmctl/apps/openclaw-gateway/deploy-with-secrets.sh

# Or rebuild only (don't restart):
bash /srv/vmctl/apps/openclaw-gateway/deploy-with-secrets.sh --rebuild-only

# Or fetch secrets only (don't rebuild):
GCP_PROJECT=molt-chatbot bash /srv/vmctl/apps/openclaw-gateway/deploy-with-secrets.sh --rebuild-only
```

## Step 4: Update Secrets

To update a secret (e.g., rotate a token):

```bash
PROJECT="molt-chatbot"

# Add a new version (old versions are retained for audit)
echo "new-token-value" | gcloud secrets versions add openclaw-discord-token \
  --data-file=- --project="$PROJECT"

# Re-deploy to pick up the new version
bash /srv/vmctl/apps/openclaw-gateway/deploy-with-secrets.sh
```

## Verification

After deployment, verify secrets are loaded:

```bash
# Check container is running
docker ps | grep openclaw-gateway

# Check logs for startup success
docker logs openclaw-gateway | grep -i "gateway\|error"

# Inside container, verify env vars (careful—prints secrets!)
docker exec openclaw-gateway env | grep -E "DISCORD|AZURE|GOOGLE"
```

## Troubleshooting

**"Secret not found" error:**
```bash
# List available secrets
gcloud secrets list --project=molt-chatbot

# Check secret exists and is readable
gcloud secrets versions access latest --secret=openclaw-discord-token --project=molt-chatbot
```

**"Permission denied" error:**
```bash
# Check IAM bindings
gcloud secrets get-iam-policy openclaw-discord-token --project=molt-chatbot

# Re-grant permissions (Step 2)
```

**Secrets file has blank lines:**
```bash
# Script gracefully skips missing secrets
# This is OK—only include tokens you actually need
# Check which are empty:
grep "=$" /srv/vmctl/agent/openclaw-gateway/secrets/agent.env
```

## Rotating All Secrets

To rotate all secrets at once (e.g., security incident):

```bash
PROJECT="molt-chatbot"

# Update each secret with new values
echo "new-discord-token" | gcloud secrets versions add openclaw-discord-token \
  --data-file=- --project="$PROJECT"
echo "new-azure-key" | gcloud secrets versions add azure-openai-api-key \
  --data-file=- --project="$PROJECT"
# ... etc

# Deploy with fresh secrets
bash /srv/vmctl/apps/openclaw-gateway/deploy-with-secrets.sh
```

## Security Notes

- Secrets are **never** committed to git (`.gitignore` protects `.env*` files)
- Secrets are **never** stored in Docker images (fetched at deploy time)
- Old secret versions are retained in GCP for audit (see `gcloud secrets versions list`)
- Container `/srv/vmctl/agent/openclaw-gateway/secrets/agent.env` is deleted on each rebuild
- Only users/SAs with `secretmanager.secretAccessor` role can deploy

## FAQ

**Q: What if I don't have GCP Secrets Manager?**
A: Store `agent.env` in `/home/developer/.openclaw-secrets/` and update the deploy script to copy instead of fetching.

**Q: Can I use different secrets for different environments?**
A: Yes—create separate secret names per environment (e.g., `openclaw-discord-token-prod`, `openclaw-discord-token-dev`) and pass `--secret-suffix` to the deploy script.

**Q: Are old secret versions accessible?**
A: Yes, via `gcloud secrets versions list` and `gcloud secrets versions access <VERSION>`. Only the latest is used.
