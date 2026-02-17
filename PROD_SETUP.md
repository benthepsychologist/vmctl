# Production Workstation Setup (vmctl-prod)

Complete step-by-step documentation of creating a production workstation VM with isolated OpenClaw agent and persistent development workspace.

## What We Built

**Architecture:**
- 2-zone isolation model
- **Agent Zone**: OpenClaw in isolated Docker container (cannot access /workspace)
- **Dev Zone**: /workspace directory on host for direct development via VS Code Remote-SSH
- **Airlock**: OpenClaw communicates via dropbox/queue (not implemented in this phase)

**VM Specs:**
- Machine: e2-standard-4 (4 vCPU, 16GB RAM)
- Boot Disk: 200GB
- Region: us-central1-a
- Project: molt-chatbot

**Pre-installed:**
- Docker (v29.2.1)
- git, gcloud, python3
- Tailscale (for private network access)
- SSH configured for immediate access

## Problems Encountered & Solutions

### Problem 1: Fresh Debian VMs Don't Accept SSH Keys
**Issue:** Creating VMs with `gcloud compute instances create` results in SSH auth failures because fresh Debian 12 images don't have SSH configured to accept keys.

**Failed approaches:**
- Waiting for SSH to be ready (doesn't work on fresh image)
- Using `gcloud compute ssh` (service account permissions issue in Cloud Workstation)
- Using `gcloud compute scp` to copy setup scripts (same auth issues)
- SSH from test VM to prod on internal network (fails, no route)

**Solution:** Use **startup script with metadata** to configure SSH DURING image boot, before we ever try to SSH in.

### Problem 2: Service Account SSH Auth Issues
**Issue:** This Cloud Workstation uses a service account (vmctl-admin@molt-chatbot.iam.gserviceaccount.com) that doesn't have full IAM permissions for Compute Engine SSH/SCP operations.

**Solution:** Don't rely on Cloud Workstation's gcloud for SSH operations. Instead:
1. Use startup script to configure SSH during VM creation
2. Connect from local machine (which has proper SSH keys)
3. Use local machine credentials for git operations

## Step-by-Step Setup

### Step 1: Create Startup Script

This script runs automatically when the VM boots. It configures everything we need.

```bash
cat > /tmp/prod-startup.sh << 'SCRIPT'
#!/bin/bash
set -e

# Create developer user with sudo access
useradd -m -s /bin/bash -G sudo developer 2>/dev/null || true

# Configure SSH for developer user
mkdir -p /home/developer/.ssh
chmod 700 /home/developer/.ssh

# Add SSH public key (hardcoded, but could come from metadata)
cat > /home/developer/.ssh/authorized_keys << 'KEYS'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKf6NrLFLpOm0bg/SnLkroXI8JiUYJNdeR9JIh7m0B5h benthepsychologist@github
KEYS
chmod 600 /home/developer/.ssh/authorized_keys
chown -R developer:developer /home/developer/.ssh

# Install Docker
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
usermod -aG docker developer

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Create directories for OpenClaw and workspace
mkdir -p /workspace /srv/vmctl/agent/openclaw-gateway
chown developer:developer /workspace

# Start Tailscale (will need interactive auth later)
sudo -u developer tailscale up --ssh 2>&1 || true

echo "✓ Prod VM setup complete" >> /var/log/startup.log
SCRIPT
```

**Key points:**
- `set -e`: Stop on any error
- SSH key hardcoded (replace with your public key)
- Creates developer user with docker/sudo access
- Installs Docker in one command (official script)
- Creates Tailscale service (needs auth later)

### Step 2: Create VM with Startup Script

```bash
gcloud compute instances create vmctl-prod \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=200GB \
  --scopes=cloud-platform \
  --metadata-from-file=startup-script=/tmp/prod-startup.sh \
  --tags=allow-ssh \
  2>&1
```

**What this does:**
- Creates Debian 12 VM (small, quick boot)
- e2-standard-4: 4 vCPU, 16GB RAM (good for dev work)
- 200GB boot disk (room to grow)
- Passes startup script as metadata
- Waits ~2-3 minutes for startup to complete

**Get the VM's IP:**
```bash
gcloud compute instances describe vmctl-prod --zone=us-central1-a \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)'
# Returns: 34.67.59.3 (example)
```

### Step 3: Verify SSH Access (wait 30-60 seconds)

```bash
ssh -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  developer@34.67.59.3 \
  "docker --version"
```

**Expected output:**
```
Docker version 29.2.1, build a5c7197
```

**Why the options:**
- `-i ~/.ssh/id_ed25519`: Your private SSH key (must match public key in startup script)
- `StrictHostKeyChecking=no`: Skip host key verification (VM is new, key unknown)
- `UserKnownHostsFile=/dev/null`: Don't store key (VM might change)

### Step 4: Clone Repositories

```bash
ssh -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  developer@34.67.59.3 << 'EOF'
cd /workspace

# Clone public repos (HTTPS)
git clone https://github.com/benthepsychologist/vmctl.git
git clone https://github.com/benthepsychologist/specwright.git
git clone https://github.com/benthepsychologist/life.git

echo "✓ Public repos cloned"
EOF
```

### Step 5: Copy SSH Key for Private Repos

```bash
# Copy your SSH private key to VM (for git@github.com access)
scp -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  ~/.ssh/id_ed25519 \
  developer@34.67.59.3:~/.ssh/id_ed25519

# On VM, set permissions and add GitHub to known_hosts
ssh -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  developer@34.67.59.3 << 'EOF'
chmod 600 ~/.ssh/id_ed25519
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

cd /workspace

# Clone private repos (SSH)
git clone git@github.com:benthepsychologist/openclaw-gateway.git
git clone git@github.com:benthepsychologist/life-cockpit.git

echo "✓ Private repos cloned"
EOF
```

**Why two steps?**
1. Public repos via HTTPS (works without keys)
2. Private repos via SSH (needs your private key on VM)

### Step 6: Set Up Tailscale for Private Network Access

```bash
# Get Tailscale auth URL
ssh -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  developer@34.67.59.3 \
  "timeout 5 sudo tailscale up 2>&1 || true" | grep https
```

**Output example:**
```
https://login.tailscale.com/a/136098af01097e
```

**In your browser:**
1. Visit the URL above
2. Sign in with your Tailscale account
3. Authorize the VM to join your Tailscale network
4. The VM gets a private IP (like 100.x.x.x)

**Get the Tailscale IP:**
```bash
ssh -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  developer@34.67.59.3 \
  "sudo tailscale ip -4"
```

**Output example:**
```
100.86.78.57
```

### Step 7: Update Local SSH Config

Edit your **local** `~/.ssh/config` (on your laptop):

```
Host vmctl-prod
    HostName 100.86.78.57
    User developer
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ForwardAgent yes
```

**What this does:**
- `HostName 100.86.78.57`: Uses Tailscale IP (private network)
- `ForwardAgent yes`: Forwards SSH keys to VM (git operations work seamlessly)
- `StrictHostKeyChecking no`: No key verification (VM is trusted)

### Step 8: Connect via VS Code Remote-SSH

1. Install VS Code extension: **"Remote - SSH"**
2. Cmd+Shift+P → **"Remote-SSH: Connect to Host"**
3. Select **`vmctl-prod`** (or type `developer@100.86.78.57`)
4. VS Code opens connected to VM
5. Open folder: `/workspace`

**You can now:**
- Edit code in all repos (vmctl, life-cockpit, openclaw-gateway, etc.)
- Run git commands (SSH forwarding handles auth)
- Run Docker commands
- SSH to other GCE VMs via gcloud

### Step 9: Deploy OpenClaw (Optional)

To run OpenClaw in isolated Docker:

```bash
ssh vmctl-prod << 'EOF'
# Copy OpenClaw docker-compose setup
cp -r /workspace/vmctl/apps/openclaw-gateway ~/openclaw-compose

# Create secrets
mkdir -p ~/openclaw-compose/secrets
cat > ~/openclaw-compose/secrets/agent.env << 'SECRETS'
DISCORD_TOKEN=your_token_here
TELEGRAM_TOKEN=your_token_here
SECRETS

# Deploy
cd ~/openclaw-compose
docker compose up -d

# Verify isolation (should fail)
docker exec openclaw-gateway ls /workspace 2>&1 | grep -E "cannot|No such"
EOF
```

## Troubleshooting

### SSH "Permission denied (publickey)"
- Verify your SSH public key is in `/tmp/prod-startup.sh`
- Check key ownership: `ssh-keygen -lf ~/.ssh/id_ed25519.pub`
- Verify key was deployed: `ssh developer@PROD_IP "ls -la ~/.ssh/"`

### Git clone fails with "Permission denied"
- SSH key not copied to VM: `scp ~/.ssh/id_ed25519 developer@PROD_IP:~/.ssh/`
- SSH key permissions: `ssh PROD_IP "chmod 600 ~/.ssh/id_ed25519"`
- Test: `ssh PROD_IP "ssh-keyscan github.com >> ~/.ssh/known_hosts && git ls-remote git@github.com:benthepsychologist/openclaw-gateway.git"`

### Tailscale IP not showing
- Not authenticated yet: Visit the auth URL printed by `tailscale up`
- Check status: `ssh vmctl-prod "sudo tailscale status"`
- Force re-auth: `ssh vmctl-prod "sudo tailscale logout && sudo tailscale up"`

### VS Code Remote-SSH can't connect
- Verify SSH works locally: `ssh vmctl-prod "echo hello"`
- Check VS Code settings: `"remote.SSH.enableAgentForwarding": true`
- Restart VS Code and try again
- If using Tailscale IP and it's not working, try public IP first: `ssh developer@34.67.59.3`

## Security Notes

### SSH Key Management
- SSH private key is copied to VM (necessary for git operations)
- Use Tailscale IP only (private network, encrypted)
- Don't store in git or version control
- Rotate keys periodically

### OpenClaw Isolation
Verify OpenClaw cannot access /workspace:
```bash
docker exec openclaw-gateway ls /workspace 2>&1
# Should show: ls: cannot access '/workspace': No such file or directory
```

Verify OpenClaw can only see its mounts:
```bash
docker exec openclaw-gateway ls /
# Should show: app, outbox, state (and standard system dirs)
```

### Cost Management
- e2-standard-4 running 24/7: ~$150/month
- To save money, use `vmctl stop` when not developing
- Or delete and recreate when needed (startup is fast)

## What's Next

1. **Deploy OpenClaw**: See Step 9 above
2. **Authenticate Tailscale**: Follow Step 6
3. **Connect VS Code**: Follow Step 8
4. **Start developing**: Edit code in `/workspace` repos
5. **Tear down test VM**: Delete `test-vmctl-setup` (keep vmctl-prod)

## Commands Cheat Sheet

```bash
# Get VM IP
gcloud compute instances describe vmctl-prod --zone=us-central1-a \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)'

# SSH to prod
ssh vmctl-prod

# Check Docker
ssh vmctl-prod "docker ps -a"

# Check Tailscale
ssh vmctl-prod "sudo tailscale status"

# View startup logs
ssh vmctl-prod "cat /var/log/startup.log"

# Stop VM (saves money)
gcloud compute instances stop vmctl-prod --zone=us-central1-a

# Start VM
gcloud compute instances start vmctl-prod --zone=us-central1-a

# Delete VM
gcloud compute instances delete vmctl-prod --zone=us-central1-a
```

## Environment

All commands assume:
- gcloud CLI installed and authenticated
- SSH key at `~/.ssh/id_ed25519`
- Project: `molt-chatbot`
- Zone: `us-central1-a`

## References

- [Startup Scripts on Google Cloud](https://cloud.google.com/compute/docs/instances/startup-scripts)
- [Tailscale SSH Setup](https://tailscale.com/kb/1193/tailscale-ssh)
- [Docker Installation](https://docs.docker.com/engine/install/debian/)
