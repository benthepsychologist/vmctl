#!/bin/bash
set -e

echo "Starting code-server..."

# Initialize config directory with proper permissions
mkdir -p ~/.config/code-server
mkdir -p /workspace/.cstation

# Clone/pull git repos if configured
if [ -f "/workspace/.cstation/repos.txt" ]; then
    echo "Syncing git repositories..."
    while IFS= read -r repo; do
        # Skip empty lines and comments
        if [ -n "$repo" ] && [[ ! "$repo" =~ ^# ]]; then
            repo_name=$(basename "$repo" .git)
            if [ -d "/workspace/$repo_name" ]; then
                echo "Pulling updates for $repo_name..."
                (cd "/workspace/$repo_name" && git pull) || echo "Failed to pull $repo_name"
            else
                echo "Cloning $repo_name..."
                git clone "$repo" "/workspace/$repo_name" || echo "Failed to clone $repo_name"
            fi
        fi
    done < /workspace/.cstation/repos.txt
fi

# Run init script if it exists
if [ -f "/workspace/.cstation/init.sh" ]; then
    echo "Running initialization script..."
    bash /workspace/.cstation/init.sh
fi

# Start code-server
exec code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    /workspace
