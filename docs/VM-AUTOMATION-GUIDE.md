# Self-Managed VM Automation Guide

This guide explains how to use your self-managed development VM as a Cloud Workstation replacement.

## Quick Start

### From Your Workstation (to create the VM)
```bash
# Create and configure VM with full environment
bash /home/user/run-vm-test-workflow.sh
```

### From Your Local Machine (Mac/Linux)

**Start and connect to VM:**
```bash
# Download these scripts from your workstation first:
# - start-dev-vm.sh
# - stop-dev-vm.sh

bash start-dev-vm.sh
```

This will:
- Start the VM if stopped
- Wait for it to be ready
- Optionally open IAP tunnel to code-server

## Scripts Overview

### Workstation Scripts (run from Cloud Workstation)

| Script | Purpose |
|--------|---------|
| `run-vm-test-workflow.sh` | **Main script** - Creates VM, installs everything, generates report |
| `create-test-vm.sh` | Creates VM from workstation snapshot only |
| `cleanup-test-vm.sh` | Deletes VM, disk, and snapshot |
| `ssh-to-test-vm.sh` | Quick SSH into the VM |
| `setup-vm-environment.sh` | Installs Docker, code-server, neovim on VM |
| `vm-auto-shutdown.sh` | Auto-shutdown monitor (runs on VM) |
| `install-auto-shutdown.sh` | Installs auto-shutdown service on VM |

### Local Machine Scripts (run from your Mac/PC)

| Script | Purpose |
|--------|---------|
| `start-dev-vm.sh` | **Start VM and connect** |
| `stop-dev-vm.sh` | **Stop VM** (saves money) |

## Detailed Usage

### 1. Creating Your Dev VM

**From your Cloud Workstation:**
```bash
bash /home/user/run-vm-test-workflow.sh
```

**What it does:**
- ✅ Creates snapshot of workstation data
- ✅ Creates new VM with Debian 12
- ✅ Mounts your data at `/mnt/home/user/`
- ✅ Installs Docker, code-server, neovim
- ✅ Sets up auto-shutdown (2hr idle timeout)
- ✅ Runs validation tests
- ✅ Generates detailed report

**Time:** ~6 minutes
**Output:** Markdown report at `/home/user/vm-test-report-[timestamp].md`

### 2. Accessing Your VM

#### Option A: code-server (Web VS Code)

**From your local machine:**
```bash
# Start the IAP tunnel
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap \
  -- -L 8080:localhost:8080 -N
```

Then open: **http://localhost:8080**

- No password required
- Your files are at `/mnt/home/user/`
- Full VS Code experience in browser

#### Option B: SSH Terminal

**From your local machine:**
```bash
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap
```

#### Option C: Use the Helper Script

**From your local machine:**
```bash
bash start-dev-vm.sh
```

Interactive menu will ask if you want to start the tunnel.

### 3. Working on the VM

**Your workstation files:**
- Location: `/mnt/home/user/`
- Includes: life-cockpit, canonizer, dogfold, all configs

**Available tools:**
- ✅ Docker (v29.0.0)
- ✅ code-server (v4.105.1)
- ✅ neovim (v0.7.2)
- ✅ git, gcloud, python3

**Example workflow:**
```bash
# SSH into VM
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap

# Navigate to your project
cd /mnt/home/user/life-cockpit

# Edit with nvim
nvim README.md

# Use Docker
docker run hello-world
```

### 4. Auto-Shutdown

The VM automatically shuts down after **2 hours of idle time** (no SSH or code-server connections).

**Check auto-shutdown status:**
```bash
# From workstation, SSH into VM first
sudo systemctl status vm-auto-shutdown
sudo journalctl -u vm-auto-shutdown -f
```

**Adjust timeout:**
Edit `/usr/local/bin/vm-auto-shutdown.sh` on the VM and change:
```bash
IDLE_TIMEOUT_MINUTES=120  # Change this value
```

Then restart: `sudo systemctl restart vm-auto-shutdown`

### 5. Stopping the VM Manually

**From your local machine:**
```bash
bash stop-dev-vm.sh
```

Or directly:
```bash
gcloud compute instances stop test-vm-from-workstation \
  --zone=northamerica-northeast1-b
```

**Why stop manually?**
- Save money when done for the day
- VM only costs money while RUNNING
- Auto-shutdown does this automatically after 2hrs idle

### 6. Starting a Stopped VM

**From your local machine:**
```bash
bash start-dev-vm.sh
```

Or directly:
```bash
gcloud compute instances start test-vm-from-workstation \
  --zone=northamerica-northeast1-b
```

**Start time:** ~30 seconds

### 7. Cleaning Up (Deleting Everything)

**From your Cloud Workstation:**
```bash
bash /home/user/cleanup-test-vm.sh
```

**Deletes:**
- VM instance
- 200GB data disk
- Snapshot

**Does NOT delete:**
- Your Cloud Workstation
- Original workstation data

## Cost Breakdown

### Current: Cloud Workstation
- **$150/month** ($6 VM + $144 control plane)

### Self-Managed VM (24/7)
- Compute: **$49.28/month** (e2-standard-2)
- Disk: **$8/month** (200GB pd-standard)
- Boot: **$2/month** (50GB pd-standard)
- **Total: $59/month**
- **Savings: $91/month (61%)**

### Self-Managed VM (8hrs/day with auto-stop)
- Compute: **$16.43/month** (8hrs × $0.067/hr)
- Disk: **$10/month** (persistent, always charged)
- **Total: $26/month**
- **Savings: $124/month (83%)**

### Self-Managed VM (stopped, only storage)
- Disk: **$10/month**
- Compute: **$0** (not running)
- **Total: $10/month**
- **Savings: $140/month (93%)**

## Differences from Cloud Workstation

### What's the Same ✅
- ✅ IAP authentication
- ✅ Secure access (no public IPs needed)
- ✅ Same dev environment (Docker, code-server)
- ✅ All your data accessible
- ✅ Auto-shutdown after idle
- ✅ Google Cloud SSO

### What's Different ⚠️

| Feature | Cloud Workstation | Self-Managed VM |
|---------|------------------|----------------|
| **Start VM** | Click "Start" in console | Run `start-dev-vm.sh` |
| **Access** | Click "Open in browser" | Run IAP tunnel command |
| **Auto-updates** | Managed by Google | You manage |
| **Cost** | $150/mo (always) | $26-59/mo (depends on usage) |
| **Setup time** | Instant | 6 minutes (one-time) |

## Troubleshooting

### VM won't start
```bash
# Check VM status
gcloud compute instances describe test-vm-from-workstation \
  --zone=northamerica-northeast1-b
```

### Can't connect to code-server
```bash
# Check if code-server is running on VM
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap \
  --command="sudo systemctl status code-server"

# Restart code-server
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap \
  --command="sudo systemctl restart code-server"
```

### Auto-shutdown not working
```bash
# Check logs
gcloud compute ssh test-vm-from-workstation \
  --zone=northamerica-northeast1-b \
  --tunnel-through-iap \
  --command="sudo journalctl -u vm-auto-shutdown -n 50"
```

## Next Steps

1. **Test the VM** - Use it for a few days alongside your workstation
2. **Validate your workflow** - Make sure all your tools work
3. **Make a decision** - Keep workstation or migrate to VM?
4. **Migrate fully** - Delete Cloud Workstation, save $91-124/month

## Files Reference

All scripts are in `/home/user/` on your Cloud Workstation:
- `run-vm-test-workflow.sh` - Main workflow
- `start-dev-vm.sh` - Start VM (for local machine)
- `stop-dev-vm.sh` - Stop VM (for local machine)
- `cleanup-test-vm.sh` - Delete everything
- `ssh-to-test-vm.sh` - Quick SSH
- `vm-test-report-*.md` - Generated reports

---

**Questions?** Review the generated report at `/home/user/vm-test-report-[timestamp].md`
