#!/bin/bash
set -e

echo "Starting life container (operator zone)..."
echo "ZONE: ${ZONE}"
echo "TRUST_LEVEL: ${TRUST_LEVEL}"

# Initialize config directories
mkdir -p ~/.config/code-server
mkdir -p ~/.claude

# Display agent app area status
echo ""
echo "Agent app area mounts:"
echo "  /agent/state  - $(ls /agent/state 2>/dev/null | wc -l) items (read-only)"
echo "  /agent/outbox - $(ls /agent/outbox 2>/dev/null | wc -l) items (read-only)"
echo "  /agent/repo   - $(ls /agent/repo 2>/dev/null | wc -l) items (read-only)"
echo ""

# Run init script if it exists in workspace
if [ -f "/workspace/.life/init.sh" ]; then
    echo "Running life initialization script..."
    bash /workspace/.life/init.sh
fi

# Start code-server
echo "Starting code-server on port 8080..."
exec code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    /workspace
