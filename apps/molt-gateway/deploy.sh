#!/bin/bash
# Deploy hook for molt-gateway agent zone app
#
# This script runs before `docker compose up` to ensure
# all required directories exist with correct permissions.
#
# Called by: vmctl deploy --app-dir /srv/vmctl/agent/molt-gateway/app

set -e

echo "molt-gateway deploy hook: Setting up agent zone directories..."

# Canonical host layout for molt-gateway
BASE_DIR="/srv/vmctl/agent/molt-gateway"

# Create all required directories
for subdir in repo outbox state app secrets; do
    dir="$BASE_DIR/$subdir"
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Set permissions
# - outbox/state: world-writable (container runs as non-root)
# - secrets: restricted (600, root-owned)
OWNER="${SUDO_USER:-$(whoami)}"
echo "Setting ownership to: $OWNER"
chown -R "$OWNER:$OWNER" "$BASE_DIR" 2>/dev/null || true

# Make outbox and state writable by container (which runs as non-root)
chmod 777 "$BASE_DIR/outbox" 2>/dev/null || true
chmod 777 "$BASE_DIR/state" 2>/dev/null || true

# Secure the secrets directory
chmod 700 "$BASE_DIR/secrets" 2>/dev/null || true

# Ensure agent.env exists (even if empty) to prevent compose errors
if [ ! -f "$BASE_DIR/secrets/agent.env" ]; then
    echo "Creating empty agent.env (add granted tokens before deploying)"
    touch "$BASE_DIR/secrets/agent.env"
    chmod 600 "$BASE_DIR/secrets/agent.env"
    chown root:root "$BASE_DIR/secrets/agent.env" 2>/dev/null || true
fi

# Clone or update the molt-gateway repo if not present
if [ ! -d "$BASE_DIR/repo/.git" ]; then
    echo "Note: molt-gateway repo not found at $BASE_DIR/repo"
    echo "Clone the repo before deploying:"
    echo "  git clone <molt-gateway-url> $BASE_DIR/repo"
else
    echo "Updating molt-gateway repo..."
    (cd "$BASE_DIR/repo" && git pull --ff-only 2>/dev/null) || echo "Git pull skipped"
fi

echo "Deploy hook complete."
echo ""
echo "Next steps:"
echo "  1. Ensure molt-gateway repo is cloned to $BASE_DIR/repo"
echo "  2. Add granted tokens to $BASE_DIR/secrets/agent.env"
echo "  3. Build the molt-gateway image (if not using registry)"
