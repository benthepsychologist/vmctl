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

### Secrets Management (Google Secrets Manager)

⚠️ **CRITICAL**: Secrets are fetched from Google Secrets Manager at deploy time.
- **Never** commit secrets to git
- **Never** hardcode in Dockerfile
- Always use `deploy-with-secrets.sh` for rebuilds

See [SECRETS_SETUP.md](SECRETS_SETUP.md) for one-time GCP setup.

### Prerequisites (One-Time Setup)

**On local machine:**
1. Set up Google Secrets Manager (see [SECRETS_SETUP.md](SECRETS_SETUP.md))
2. Ensure secrets are created in GCP project `molt-chatbot`

**On VM:**
1. Copy SSH keys so the VM can clone git repos:
   ```bash
   sudo mkdir -p /root/.ssh
   sudo cp ~/.ssh/id_* /root/.ssh/
   sudo chmod 600 /root/.ssh/id_*
   sudo chmod 700 /root/.ssh
   ```

2. Grant VM service account access to GCP Secrets Manager:
   ```bash
   # Get your VM's service account ID
   SA_ID=$(gcloud compute instances describe vmctl-prod --zone=us-west1-a --format='value(serviceAccounts[0].email)')

   # Grant secretAccessor role
   gcloud projects add-iam-policy-binding molt-chatbot \
     --member="serviceAccount:$SA_ID" \
     --role="roles/secretmanager.secretAccessor"
   ```

### Day 1: Initial Deployment

**On VM:**

```bash
# 1. Pull latest vmctl repo
cd /workspace/vmctl && git pull

# 2. Create agent directories
sudo mkdir -p /srv/vmctl/agent/openclaw-gateway/{repo,outbox,state,secrets}

# 3. Clone openclaw-gateway repo (using local copy if SSH unavailable)
sudo cp -r /workspace/openclaw-gateway /srv/vmctl/agent/openclaw-gateway/repo
# OR if SSH works:
# sudo git clone git@github.com:benthepsychologist/openclaw-gateway.git /srv/vmctl/agent/openclaw-gateway/repo

# 4. Fix ownership
sudo chown -R $USER:$USER /srv/vmctl/agent/openclaw-gateway

# 5. Deploy with secrets from GCP
cd /srv/vmctl/apps/openclaw-gateway
sudo bash deploy-with-secrets.sh --fresh

# 6. Verify
docker compose logs -f openclaw
```

Expected output: `gateway entered RUNNING state` and `feed entered RUNNING state`

### Day N: Operations

**Rebuild with latest code:**
```bash
# Auto-pulls from git, fetches fresh secrets, rebuilds
cd /srv/vmctl/apps/openclaw-gateway
sudo bash deploy-with-secrets.sh
```

**Plugin installation & testing:**
```bash
# SSH into container
sudo docker compose exec openclaw bash

# Inside container
openclaw plugin install <plugin-name>
openclaw doctor --fix  # Apply config migrations
openclaw status        # Check health
```

**Logs & debugging:**
```bash
# Follow logs
sudo docker compose logs -f openclaw

# Check if secrets loaded
cat /srv/vmctl/agent/openclaw-gateway/secrets/agent.env

# Inspect container
docker ps | grep openclaw
docker inspect openclaw-gateway
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
