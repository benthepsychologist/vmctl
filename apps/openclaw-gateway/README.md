# openclaw-gateway Agent Zone App

Agent-zone compose app for openclaw-gateway with containerized isolation and writable state.

OpenClaw runs with ability to:
- Mutate its state files (`/state`, sqlite, caches)
- Install plugins and update npm packages
- Self-configure and maintain runtime configuration

## Trust Boundary

This app enforces a one-way filesystem boundary:

- **Life/dev CAN** access the agent app area (repo/outbox/state) for review, ops, and recovery
- **Agent CANNOT** access `/workspace` or the broader host filesystem

## Host Layout

```
/srv/vmctl/
├── apps/
│   └── openclaw-gateway/        # Compose app directory (vmctl --app-dir target)
│       ├── compose.yml
│       ├── deploy.sh
│       └── agent.env.example
└── agent/
    └── openclaw-gateway/
        ├── repo/            # Git checkout of openclaw-gateway (agent sees as /app:ro)
        ├── outbox/          # Cross-zone artifact channel (agent sees as /outbox:rw)
        ├── state/           # Runtime state - sqlite, caches (agent sees as /state:rw)
        └── secrets/
            └── agent.env    # Granted tokens only (chmod 600, root-owned)
```

## Deployment

### Day 1: Initial Setup

```bash
# 1. Create agent directories on VM
sudo mkdir -p /srv/vmctl/agent/openclaw-gateway/{repo,outbox,state,secrets}

# 2. Clone openclaw-gateway repo (or otherwise place a checkout at this path)
sudo git clone <openclaw-gateway-url> /srv/vmctl/agent/openclaw-gateway/repo

# 3. Add granted tokens
sudo cp /srv/vmctl/apps/openclaw-gateway/agent.env.example /srv/vmctl/agent/openclaw-gateway/secrets/agent.env
sudo chmod 600 /srv/vmctl/agent/openclaw-gateway/secrets/agent.env
sudo chown root:root /srv/vmctl/agent/openclaw-gateway/secrets/agent.env
# Edit to add actual tokens

# 4. Deploy (compose app dir)
vmctl deploy --app-dir /srv/vmctl/apps/openclaw-gateway
```

### Day N: Operations

```bash
# Check status
vmctl ps --app-dir /srv/vmctl/apps/openclaw-gateway

# View logs
vmctl logs --app-dir /srv/vmctl/apps/openclaw-gateway
vmctl logs -f --app-dir /srv/vmctl/apps/openclaw-gateway  # follow

# Restart
vmctl restart --app-dir /srv/vmctl/apps/openclaw-gateway

# Redeploy (after repo update)
vmctl deploy --app-dir /srv/vmctl/apps/openclaw-gateway
```

## Security Constraints

The compose file enforces these isolation rules:

### Allowed Mounts (allowlist)
- `/srv/vmctl/agent/openclaw-gateway/repo:/app:ro` - Code (read-only)
- `/srv/vmctl/agent/openclaw-gateway/outbox:/outbox:rw` - Artifacts / cross-zone communication
- `/srv/vmctl/agent/openclaw-gateway/state:/state:rw` - State, cache, plugins, sqlite

### Forbidden (not mounted)
- `/workspace` - No access to shared workspace
- `/var/run/docker.sock` - No container escape
- Host home directories - No user data access

### Hardening Applied
- Container runs as `openclaw` user (non-root)
- `cap_drop: ["ALL"]` - All capabilities dropped
- `security_opt: ["no-new-privileges:true"]` - No privilege escalation
- `tmpfs: ["/tmp"]` - Writable tmp in memory only
- No ports exposed - No inbound network access
- Python packages in virtual environment (isolated from system)
- NOTE: `read_only: true` removed to allow state/plugin mutation (required for OpenClaw self-configuration)

## Recommended Workflow: Hybrid Dev/Prod

**For code changes (git discipline):**
```bash
# Edit repo on host
vim /srv/vmctl/agent/openclaw-gateway/repo/src/...
git -C /srv/vmctl/agent/openclaw-gateway/repo add .
git -C /srv/vmctl/agent/openclaw-gateway/repo commit -m "..."
git -C /srv/vmctl/agent/openclaw-gateway/repo push origin main

# Rebuild container to pick up changes
docker build -t openclaw-gateway:agent /srv/vmctl/agent/openclaw-gateway/repo
docker restart openclaw-gateway
```

**For plugin/config testing (quick iteration):**
```bash
# SSH into container
docker exec -it openclaw-gateway bash

# Install plugins (persists in /state)
openclaw plugin install <plugin-name>

# Configure
openclaw config set key value

# Test/debug
openclaw ...
```

**Key points:**
- **Code**: Edit on host → git → rebuild (dev/prod separation)
- **Plugins/config**: `docker exec` directly (fast feedback, persists in `/state`)
- **State changes**: Automatically persisted in `/srv/vmctl/agent/openclaw-gateway/state` (survives restarts)

## Verification

After deployment, verify isolation:

```bash
# Check mounts (should show only repo/outbox/state)
docker inspect openclaw-gateway --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'

# Verify /workspace is not accessible
docker exec openclaw-gateway ls /workspace 2>&1  # Should fail

# Verify no docker socket
docker exec openclaw-gateway ls /var/run/docker.sock 2>&1  # Should fail

# Verify environment (only granted tokens)
docker exec openclaw-gateway env | grep -v '^PATH=' | grep -v '^HOME='
```

## Secrets Policy

Agent secrets are provided via `agent.env` and must contain **only** explicitly granted channel tokens.

**Do NOT include:**
- Cloud credentials (GCP service accounts, AWS keys)
- SSH keys or Git tokens
- Workstation environment variables
- Any secrets not explicitly granted for agent use
