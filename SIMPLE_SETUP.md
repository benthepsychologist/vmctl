# Simple Cloud Workstation + Isolated OpenClaw Setup

## Architecture

This is a dead-simple cloud workstation setup:
- **VM**: Cloud Workstation (GCE VM) for development
- **OpenClaw**: Docker container, isolated (cannot access /workspace)
- **Workspace**: /workspace directory on VM, accessed via VS Code Remote-SSH

No orchestration tools. No multi-zone complexity. Just Docker for OpenClaw isolation.

## What's Running

### OpenClaw Container
- **Purpose**: Discord/Telegram bot, isolated from repos
- **Location**: /srv/vmctl/apps/openclaw-gateway/compose.yml
- **Mounts**: ONLY /app (code), /outbox (artifacts), /state (runtime)
- **NO access to**: /workspace, /srv, host filesystem

### Workspace
- **Purpose**: Your development environment
- **Location**: /workspace on VM
- **Access**: VS Code Remote-SSH from laptop
- **Repos**: life-cockpit, vmctl, openclaw-gateway (source), etc.

## Deployment Steps

### Initial VM Setup (one-time)
```bash
# 1. SSH to VM
gcloud compute ssh VM_NAME

# 2. Create workspace
sudo mkdir -p /workspace
sudo chown $USER:$USER /workspace

# 3. Clone repos
cd /workspace
git clone git@github.com:you/life-cockpit.git
git clone git@github.com:you/vmctl.git
# ... other repos

# 4. Deploy OpenClaw (if not already running)
cd /srv/vmctl/apps/openclaw-gateway
docker compose up -d --build
```

### Daily Workflow

1. **On laptop**: Open VS Code
2. **Connect**: Remote-SSH to VM_NAME
3. **Work**: Edit files in /workspace, run commands in terminal
4. **Deploy**: Push code to cloud, SSH to other GCE VMs via gcloud

### Managing OpenClaw

```bash
# SSH to VM first
ssh VM_NAME

# Check status
cd /srv/vmctl/apps/openclaw-gateway
docker compose ps

# View logs
docker compose logs -f

# Restart
docker compose restart

# Update code and rebuild
cd /srv/vmctl/agent/openclaw-gateway/repo
git pull
cd /srv/vmctl/apps/openclaw-gateway
docker compose up -d --build
```

### Verify OpenClaw Isolation

```bash
# Should FAIL (OpenClaw cannot see /workspace)
docker exec openclaw-gateway ls /workspace

# Should SUCCEED (OpenClaw can see its allowlist)
docker exec openclaw-gateway ls /app
docker exec openclaw-gateway ls /outbox
docker exec openclaw-gateway ls /state
```

## VS Code Remote-SSH Setup

1. Install extension: "Remote - SSH"
2. Add VM to SSH config (if needed):
   ```bash
   gcloud compute config-ssh
   ```
3. Connect: Cmd+Shift+P → "Remote-SSH: Connect to Host" → VM_NAME
4. Open folder: /workspace

## Adding Code-Server (Optional)

If you want web-based VS Code for on-the-go access:

```bash
# Install code-server on VM
curl -fsSL https://code-server.dev/install.sh | sh
sudo systemctl enable --now code-server@$USER

# Access via SSH tunnel
ssh -L 8080:localhost:8080 VM_NAME
# Open http://localhost:8080 in browser
```

Password is in `~/.config/code-server/config.yaml`

## Snapshots (Manual)

```bash
# Create snapshot
gcloud compute disks snapshot DISK_NAME \
  --snapshot-names=workstation-$(date +%Y%m%d) \
  --zone=ZONE

# Restore from snapshot (if needed)
gcloud compute disks create NEW_DISK_NAME \
  --source-snapshot=SNAPSHOT_NAME \
  --zone=ZONE
```

## What Happened to vmctl?

vmctl development is paused. The tooling was getting ahead of understanding the actual systems.

This simple setup uses:
- Docker Compose for OpenClaw (from vmctl/apps/openclaw-gateway/)
- Direct work on VM (no workspace containers)
- VS Code Remote-SSH (no code-server initially)

Once Docker and gcloud patterns are well-understood, we may resume vmctl or build new tooling based on real needs.
