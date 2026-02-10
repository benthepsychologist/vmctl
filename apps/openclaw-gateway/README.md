# openclaw-gateway Agent Zone App

Agent-zone compose app for openclaw-gateway with strict filesystem isolation.

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
- `/srv/vmctl/agent/openclaw-gateway/outbox:/outbox:rw` - Artifacts
- `/srv/vmctl/agent/openclaw-gateway/state:/state:rw` - State

### Forbidden (not mounted)
- `/workspace` - No access to shared workspace
- `/var/run/docker.sock` - No container escape
- Host home directories - No user data access

### Hardening Applied
- `read_only: true` - Root filesystem is read-only
- `cap_drop: ["ALL"]` - All capabilities dropped
- `security_opt: ["no-new-privileges:true"]` - No privilege escalation
- `tmpfs: ["/tmp"]` - Writable tmp in memory only
- No ports exposed - No inbound network access

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
