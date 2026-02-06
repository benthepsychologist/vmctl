#!/bin/bash
# Deploy hook for molt-gateway agent zone app
#
# This script runs before `docker compose up` as a preflight.
#
# IMPORTANT: vmctl runs this hook without sudo. Do not attempt
# privileged operations here. Instead, validate prerequisites and
# fail fast with clear instructions.
#
# Called by: vmctl deploy --app-dir /srv/vmctl/apps/molt-gateway

set -euo pipefail

echo "molt-gateway deploy hook: Preflight checks..."

# Canonical host layout for molt-gateway agent data
BASE_DIR="/srv/vmctl/agent/molt-gateway"

missing=0

require_dir() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        echo "ERROR: Missing required directory: $dir" >&2
        missing=1
    fi
}

require_file_exists() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "ERROR: Missing required file: $file" >&2
        missing=1
    fi
}

require_dir "$BASE_DIR/repo"
require_dir "$BASE_DIR/outbox"
require_dir "$BASE_DIR/state"
require_dir "$BASE_DIR/secrets"

require_file_exists "$BASE_DIR/secrets/agent.env"

if [ -f "$BASE_DIR/secrets/agent.env" ] && [ ! -r "$BASE_DIR/secrets/agent.env" ]; then
    echo "WARN: agent.env is not readable by current user; this is OK if docker compose runs via sudo." >&2
fi

if [ -d "$BASE_DIR/repo" ] && [ ! -f "$BASE_DIR/repo/Dockerfile" ]; then
    echo "WARN: No Dockerfile found at $BASE_DIR/repo/Dockerfile; compose build may fail." >&2
fi

if [ "$missing" -ne 0 ]; then
    cat >&2 <<EOF

Preflight failed.

Expected canonical layout:
  /srv/vmctl/apps/molt-gateway/              (compose app dir; this directory)
  /srv/vmctl/agent/molt-gateway/repo/        (molt-gateway git checkout)
  /srv/vmctl/agent/molt-gateway/outbox/      (RW outbox)
  /srv/vmctl/agent/molt-gateway/state/       (RW state)
  /srv/vmctl/agent/molt-gateway/secrets/agent.env

Fix on the VM (example):
  sudo mkdir -p /srv/vmctl/agent/molt-gateway/{repo,outbox,state,secrets}
  sudo touch /srv/vmctl/agent/molt-gateway/secrets/agent.env
  sudo chmod 600 /srv/vmctl/agent/molt-gateway/secrets/agent.env
  sudo chown root:root /srv/vmctl/agent/molt-gateway/secrets/agent.env
  sudo chmod 777 /srv/vmctl/agent/molt-gateway/{outbox,state}

Then ensure the repo exists:
  sudo git clone <molt-gateway-url> /srv/vmctl/agent/molt-gateway/repo

EOF
    exit 1
fi

echo "Preflight OK. Proceeding with docker compose."
