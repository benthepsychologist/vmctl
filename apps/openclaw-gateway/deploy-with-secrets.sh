#!/bin/bash
# Deploy openclaw-gateway with secrets from Google Secrets Manager
#
# Prerequisites:
#   - gcloud CLI configured with sufficient permissions
#   - Secrets stored in GCP (see SECRETS_SETUP.md)
#
# Usage:
#   ./deploy-with-secrets.sh [--rebuild-only] [--no-restart]

set -euo pipefail

REPO_PATH="${REPO_PATH:-/srv/vmctl/agent/openclaw-gateway/repo}"
SECRETS_DIR="${SECRETS_DIR:-/srv/vmctl/agent/openclaw-gateway/secrets}"
PROJECT="${GCP_PROJECT:-molt-chatbot}"

# Parse flags
REBUILD_ONLY=false
NO_RESTART=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild-only) REBUILD_ONLY=true; shift ;;
        --no-restart) NO_RESTART=true; shift ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

echo "🔐 Fetching secrets from Google Secrets Manager..."

# Create secrets directory
mkdir -p "$SECRETS_DIR"

# Fetch secrets from GCP and build agent.env
cat > "$SECRETS_DIR/agent.env" << 'EOF'
# Auto-generated from Google Secrets Manager
# Do not commit to git
EOF

# Fetch each secret
echo "  • Fetching DISCORD_BOT_TOKEN..."
DISCORD_TOKEN=$(gcloud secrets versions access latest --secret=openclaw-discord-token --project="$PROJECT" 2>/dev/null || echo "")
if [ -n "$DISCORD_TOKEN" ]; then
    echo "DISCORD_BOT_TOKEN=$DISCORD_TOKEN" >> "$SECRETS_DIR/agent.env"
fi

echo "  • Fetching TELEGRAM_BOT_TOKEN..."
TELEGRAM_TOKEN=$(gcloud secrets versions access latest --secret=openclaw-telegram-token --project="$PROJECT" 2>/dev/null || echo "")
if [ -n "$TELEGRAM_TOKEN" ]; then
    echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN" >> "$SECRETS_DIR/agent.env"
fi

echo "  • Fetching AZURE_OPENAI_API_KEY..."
AZURE_KEY=$(gcloud secrets versions access latest --secret=azure-openai-api-key --project="$PROJECT" 2>/dev/null || echo "")
if [ -n "$AZURE_KEY" ]; then
    echo "AZURE_OPENAI_API_KEY=$AZURE_KEY" >> "$SECRETS_DIR/agent.env"
fi

echo "  • Fetching AZURE_OPENAI_HOST..."
AZURE_HOST=$(gcloud secrets versions access latest --secret=azure-openai-host --project="$PROJECT" 2>/dev/null || echo "")
if [ -n "$AZURE_HOST" ]; then
    echo "AZURE_OPENAI_HOST=$AZURE_HOST" >> "$SECRETS_DIR/agent.env"
fi

echo "  • Fetching GOOGLE_API_KEY..."
GOOGLE_KEY=$(gcloud secrets versions access latest --secret=google-api-key --project="$PROJECT" 2>/dev/null || echo "")
if [ -n "$GOOGLE_KEY" ]; then
    echo "GOOGLE_API_KEY=$GOOGLE_KEY" >> "$SECRETS_DIR/agent.env"
fi

# Add defaults
echo "AZURE_OPENAI_API_VERSION=2024-10-21" >> "$SECRETS_DIR/agent.env"
echo "GOOGLE_CLOUD_PROJECT=$PROJECT" >> "$SECRETS_DIR/agent.env"

# Set strict permissions
chmod 600 "$SECRETS_DIR/agent.env"

echo "✅ Secrets loaded: $(wc -l < "$SECRETS_DIR/agent.env") lines"

if [ "$REBUILD_ONLY" = true ]; then
    echo "✓ Secrets ready (--rebuild-only: skipping rebuild and restart)"
    exit 0
fi

# Rebuild image
echo ""
echo "🔨 Rebuilding Docker image..."
docker build -t openclaw-gateway:agent "$REPO_PATH"

if [ "$NO_RESTART" = true ]; then
    echo "✓ Build complete (--no-restart: skipping container restart)"
    exit 0
fi

# Restart container
echo ""
echo "🚀 Restarting container..."
docker restart openclaw-gateway

echo ""
echo "✅ Deployment complete!"
echo "   Run: docker logs -f openclaw-gateway"
