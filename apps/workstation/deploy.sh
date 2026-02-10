#!/bin/bash
# Deploy hook for workstation containers
#
# This script runs before `docker compose up` to ensure
# all required directories exist on the host.
#
# Called by: vmctl deploy --app-dir /opt/apps/workstation

set -e

echo "Workstation deploy hook: Setting up directories..."

# Base paths (on the VM host)
WORKSPACE_DIR="${WORKSPACE_HOST_DIR:-/workspace}"
AGENT_DATA_DIR="${AGENT_HOST_DIR:-/srv/vmctl/agent}"

# Create shared workspace directory (needs sudo for /workspace at root)
if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "Creating workspace directory: $WORKSPACE_DIR"
    sudo mkdir -p "$WORKSPACE_DIR"
    sudo chown "$(whoami):$(whoami)" "$WORKSPACE_DIR"
fi

# Create agent app area directories
# These are separate from agent's /workspace to maintain trust gradient
for subdir in state outbox repo; do
    dir="$AGENT_DATA_DIR/$subdir"
    if [ ! -d "$dir" ]; then
        echo "Creating agent data directory: $dir"
        mkdir -p "$dir"
    fi
done

# Set ownership (adjust user/group as needed for your VM)
# Default to current user
OWNER="${SUDO_USER:-$(whoami)}"
echo "Setting ownership to: $OWNER"
chown "$OWNER:$OWNER" "$WORKSPACE_DIR" 2>/dev/null || true
chown -R "$OWNER:$OWNER" "$AGENT_DATA_DIR" 2>/dev/null || true

# Optionally pull latest changes if this is a git repo
if [ -d .git ]; then
    echo "Updating from git..."
    git pull --ff-only 2>/dev/null || echo "Git pull skipped (no remote or conflicts)"
fi

echo "Deploy hook complete."
