# molt-gateway Agent Zone App

Agent-zone compose app for molt-gateway with strict filesystem isolation.

## Trust Boundary

This app enforces a one-way filesystem boundary:

- **Life/dev CAN** access the agent app area (repo/outbox/state) for review, ops, and recovery
- **Agent CANNOT** access `/workspace` or the broader host filesystem

## Host Layout

```
/srv/vmctl/agent/molt-gateway/
├── repo/           # Git checkout of molt-gateway (agent sees as /app:ro)
├── outbox/         # Cross-zone artifact channel (agent sees as /outbox:rw)
├── state/          # Runtime state - sqlite, caches (agent sees as /state:rw)
├── app/            # This compose app directory (vmctl deploy target)
└── secrets/
    └── agent.env   # Granted tokens only (chmod 600, root-owned)
```

## Deployment

### Day 1: Initial Setup

```bash
# 1. Create directories on VM
sudo mkdir -p /srv/vmctl/agent/molt-gateway/{repo,outbox,state,app,secrets}

# 2. Clone molt-gateway repo
git clone <molt-gateway-url> /srv/vmctl/agent/molt-gateway/repo

# 3. Copy this app to the VM
# (or clone/copy the compose files to /srv/vmctl/agent/molt-gateway/app)

# 4. Add granted tokens
sudo cp agent.env.example /srv/vmctl/agent/molt-gateway/secrets/agent.env
sudo chmod 600 /srv/vmctl/agent/molt-gateway/secrets/agent.env
sudo chown root:root /srv/vmctl/agent/molt-gateway/secrets/agent.env
# Edit to add actual tokens

# 5. Build the molt-gateway image (if not using registry)
cd /srv/vmctl/agent/molt-gateway/repo
docker build -t molt-gateway:latest .

# 6. Deploy
vmctl deploy --app-dir /srv/vmctl/agent/molt-gateway/app
```

### Day N: Operations

```bash
# Check status
vmctl ps --app-dir /srv/vmctl/agent/molt-gateway/app

# View logs
vmctl logs --app-dir /srv/vmctl/agent/molt-gateway/app
vmctl logs -f --app-dir /srv/vmctl/agent/molt-gateway/app  # follow

# Restart
vmctl restart --app-dir /srv/vmctl/agent/molt-gateway/app

# Redeploy (after repo update)
vmctl deploy --app-dir /srv/vmctl/agent/molt-gateway/app
```

## Security Constraints

The compose file enforces these isolation rules:

### Allowed Mounts (allowlist)
- `/srv/vmctl/agent/molt-gateway/repo:/app:ro` - Code (read-only)
- `/srv/vmctl/agent/molt-gateway/outbox:/outbox:rw` - Artifacts
- `/srv/vmctl/agent/molt-gateway/state:/state:rw` - State

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
docker inspect molt-gateway --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'

# Verify /workspace is not accessible
docker exec molt-gateway ls /workspace 2>&1  # Should fail

# Verify no docker socket
docker exec molt-gateway ls /var/run/docker.sock 2>&1  # Should fail

# Verify environment (only granted tokens)
docker exec molt-gateway env | grep -v '^PATH=' | grep -v '^HOME='
```

## Secrets Policy

Agent secrets are provided via `agent.env` and must contain **only** explicitly granted channel tokens.

**Do NOT include:**
- Cloud credentials (GCP service accounts, AWS keys)
- SSH keys or Git tokens
- Workstation environment variables
- Any secrets not explicitly granted for agent use
