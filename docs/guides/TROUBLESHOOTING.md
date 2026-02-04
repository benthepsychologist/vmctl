# Troubleshooting Guide

Common issues and solutions for VM Workstation Manager.

## Table of Contents
- [Cannot Connect to code-server (Connection Refused)](#cannot-connect-to-code-server-connection-refused)
- [VM Already Exists Error](#vm-already-exists-error)
- [Cannot Pull Latest Changes (Git Conflicts)](#cannot-pull-latest-changes-git-conflicts)
- [SSH Connection Issues](#ssh-connection-issues)
- [Auto-shutdown Not Working](#auto-shutdown-not-working)
- [Docker Permission Denied](#docker-permission-denied)

---

## Cannot Connect to code-server (Connection Refused)

### Symptoms
```bash
vmws tunnel
# Shows:
channel 2: open failed: connect failed: Connection refused
```

### Diagnosis
Check if code-server is running:
```bash
vmws ssh
sudo systemctl status code-server
```

### Common Causes & Solutions

#### 1. Permission Denied (Most Common)

**Error in logs:**
```
code-server.service: Failed at step CHDIR spawning /usr/bin/code-server: Permission denied
```

**Cause:** When migrating from Cloud Workstation, `/mnt/home/user` is owned by the old user (UID 1000), but code-server runs as your current user (e.g., UID 1046285519).

**Fix:**
```bash
vmws ssh
sudo chown -R $USER:$USER /mnt/home/user
sudo systemctl restart code-server
sudo systemctl status code-server  # Verify it's running
```

**Why this happens:**
- Cloud Workstation uses standard Linux user (UID 1000)
- Self-managed VM with OS Login creates user from Google account (e.g., `ben_getmensio_com` with UID 1046285519)
- Directory permissions were `drwxr-x--- 1000 1000` (owner only)
- Your new user falls into "others" category → no access

**Permanent fix:** This is now handled automatically in `scripts/setup-vm-environment.sh` (as of 2025-11-17).

#### 2. code-server Not Installed

**Check:**
```bash
vmws ssh
which code-server
```

**Fix:**
```bash
# Re-run setup script
vmws ssh
curl -fsSL https://code-server.dev/install.sh | sh
sudo systemctl restart code-server
```

#### 3. Wrong Port

**Check what port code-server is using:**
```bash
vmws ssh
sudo ss -tlnp | grep code-server
```

Should show `127.0.0.1:8080`. If different, update `/etc/systemd/system/code-server.service`.

---

## VM Already Exists Error

### Symptoms
```bash
vmws create
# Shows:
Error: VM 'dev-workstation' already exists
To delete it first: vmws delete
```

### Solution

**Option 1: Delete and recreate (loses data unless you have backup)**
```bash
vmws delete
vmws create  # or vmws init-fresh
```

**Option 2: Create a backup first**
```bash
vmws backup  # Takes incremental snapshot
vmws snapshots  # View all backups
vmws delete
vmws create
# If something goes wrong:
vmws restore <snapshot-name>
```

**Option 3: Use a different VM name**
```bash
vmws config --vm-name my-dev-vm-2
vmws create
```

---

## Cannot Pull Latest Changes (Git Conflicts)

### Symptoms
```bash
vmws upgrade
# or
git pull
# Shows:
error: Your local changes to the following files would be overwritten by merge:
```

### Solutions

**Option 1: Discard local changes (clean slate)**
```bash
cd ~/vm-workstation-manager
git reset --hard origin/master
git pull origin master
./bin/vmws install
```

**Option 2: Keep local changes**
```bash
cd ~/vm-workstation-manager
git stash  # Save your changes
git pull origin master
git stash pop  # Reapply your changes (may have conflicts)
./bin/vmws install
```

**Option 3: See what's different first**
```bash
cd ~/vm-workstation-manager
git status  # See changed files
git diff  # See exact changes
# Then choose Option 1 or 2
```

**Note:** Your VM config (`~/.vmws/config`) is stored outside the repo and is safe.

---

## SSH Connection Issues

### Symptoms
```bash
vmws ssh
# Hangs or times out
```

### Diagnosis

**1. Check VM is running:**
```bash
vmws status
```

**2. Check IAP firewall rules:**
```bash
gcloud compute firewall-rules list --filter="name~iap"
```

Should have a rule allowing TCP:22 from `35.235.240.0/20` (IAP range).

**3. Check VM has metadata for OS Login:**
```bash
gcloud compute instances describe <vm-name> --zone=<zone> --format="value(metadata.items[enable-oslogin])"
```

Should return `TRUE`.

### Solutions

**Create IAP firewall rule (if missing):**
```bash
gcloud compute firewall-rules create allow-iap-ssh \
    --allow=tcp:22 \
    --source-ranges=35.235.240.0/20 \
    --description="Allow IAP SSH access"
```

**Try direct SSH (bypass vmws):**
```bash
gcloud compute ssh <vm-name> \
    --zone=<zone> \
    --tunnel-through-iap
```

---

## Auto-shutdown Not Working

### Symptoms
VM doesn't shut down after 2 hours of idle time.

### Diagnosis
```bash
vmws logs
# or
vmws ssh
sudo journalctl -u vm-auto-shutdown -n 50
```

### Solutions

**1. Check if service is running:**
```bash
vmws ssh
sudo systemctl status vm-auto-shutdown
```

**2. Reinstall auto-shutdown:**
```bash
# From your local machine (repo directory)
gcloud compute scp scripts/vm-auto-shutdown.sh \
    <vm-name>:/tmp/vm-auto-shutdown.sh \
    --zone=<zone> \
    --tunnel-through-iap

gcloud compute scp scripts/install-auto-shutdown.sh \
    <vm-name>:/tmp/install-auto-shutdown.sh \
    --zone=<zone> \
    --tunnel-through-iap

vmws ssh
bash /tmp/install-auto-shutdown.sh
```

**3. Adjust timeout:**
```bash
vmws ssh
sudo vim /usr/local/bin/vm-auto-shutdown.sh
# Change IDLE_TIMEOUT_MINUTES=120 to desired value
sudo systemctl restart vm-auto-shutdown
```

---

## Docker Permission Denied

### Symptoms
```bash
vmws ssh
docker ps
# Shows:
permission denied while trying to connect to the Docker daemon socket
```

### Solution

**Add user to docker group:**
```bash
sudo usermod -aG docker $USER
```

**Then log out and back in:**
```bash
exit  # Exit SSH
vmws ssh  # Reconnect
docker ps  # Should work now
```

---

## General Debugging Tips

### Check All Service Statuses
```bash
vmws ssh
systemctl status code-server
systemctl status vm-auto-shutdown
systemctl status docker
```

### View Full Logs
```bash
# code-server logs
sudo journalctl -u code-server -f

# auto-shutdown logs
sudo journalctl -u vm-auto-shutdown -f

# System logs
sudo journalctl -xe
```

### Verify Disk Mount
```bash
vmws ssh
df -h | grep /mnt/home
lsblk
```

Should show data disk mounted at `/mnt/home`.

### Check Network Connectivity
```bash
vmws ssh
# Test internet
curl -I https://google.com

# Test IAP tunnel from local machine
gcloud compute ssh <vm-name> \
    --zone=<zone> \
    --tunnel-through-iap \
    --command="echo connected"
```

---

## Getting Help

If you're still stuck:

1. **Gather diagnostic info:**
   ```bash
   vmws status
   vmws logs
   vmws ssh --command="sudo journalctl -u code-server -n 50 --no-pager"
   ```

2. **Check the logs systematically:**
   - VM status (running/stopped?)
   - Service status (code-server, auto-shutdown)
   - Permission issues (ownership, file permissions)
   - Network issues (firewall, IAP)

3. **Search GitHub issues:** https://github.com/benthepsychologist/vmctl/issues

4. **Use Claude locally with this documentation** - the error messages are usually clear enough to diagnose with AI assistance

---

## Quick Reference: Common Commands

```bash
# Check everything
vmws status
vmws logs

# Restart services
vmws ssh
sudo systemctl restart code-server
sudo systemctl restart vm-auto-shutdown

# Check service status
sudo systemctl status code-server
sudo systemctl status vm-auto-shutdown

# View logs
sudo journalctl -u code-server -n 50
sudo journalctl -u vm-auto-shutdown -n 50

# Fix permissions (for migrated workstations)
sudo chown -R $USER:$USER /mnt/home/user

# Reinstall vmws
cd ~/vm-workstation-manager
git pull
./bin/vmws install
```
