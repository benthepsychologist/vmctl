#!/bin/bash
set -e

echo "Starting dev container (builder zone)..."
echo "ZONE: ${ZONE}"
echo "TRUST_LEVEL: ${TRUST_LEVEL}"

# Initialize config directories
mkdir -p ~/.config/code-server
mkdir -p ~/.claude

# Display agent app area status
echo ""
echo "Agent app area mounts:"
echo "  /agent/state  - $(ls /agent/state 2>/dev/null | wc -l) items (read/write)"
echo "  /agent/outbox - $(ls /agent/outbox 2>/dev/null | wc -l) items (read/write)"
echo "  /agent/repo   - $(ls /agent/repo 2>/dev/null | wc -l) items (read/write)"
echo ""

# Check if Docker socket is available
if [ -S /var/run/docker.sock ]; then
    echo "Docker socket available - Docker commands enabled"
fi

# Run init script if it exists in workspace
if [ -f "/workspace/.dev/init.sh" ]; then
    echo "Running dev initialization script..."
    bash /workspace/.dev/init.sh
fi

# Start code-server
echo "Starting code-server on port 8080..."
exec code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    /workspace
