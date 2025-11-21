# Codestation Docker Migration - Current State & Next Steps

**Last Updated:** 2025-11-19
**Status:** Phase 1 Complete (Local Docker setup working)
**Next:** Phase 2 (Cloud deployment with GCE + IAP)

---

## What We're Building

**Goal:** Replace complex VM management Python code (1,100+ lines) with simple Docker-based deployment that works locally and in cloud.

**Philosophy:**
- Git discipline for code
- BigQuery + GCS for data/state
- Docker for portable environments
- Frequent deploy/teardown cycles (cattle, not pets)
- No sync complexity - git is source of truth

**Cost:** ~$18-26/month for cloud (vs $150/month for Cloud Workstations)

---

## Current State: What Works

### ✅ Phase 1: Local Docker Setup (Steps 1-6 COMPLETE)

**Files Created:**
```
codestation/
├── Dockerfile                                    # code-server + gcloud + git
├── docker-compose.yml                            # Local development setup
├── scripts/
│   └── entrypoint.sh                             # Git sync + code-server startup
├── .env.example                                  # Environment variables template
└── src/codestation/cli/commands/
    └── docker_commands.py                        # New up/down commands
```

**What Works:**
```bash
cstation up --local      # Starts code-server at http://localhost:8080
cstation down --local    # Stops container
```

**Docker Image:**
- Base: `codercom/code-server:latest`
- Size: 2.16GB
- Includes: git, gcloud SDK, python3, python3-pip
- Entrypoint: Auto-pulls git repos from `/workspace/.cstation/repos.txt`
- Runs init script if `/workspace/.cstation/init.sh` exists

**Key Technical Decisions:**
1. ✅ **Use Persistent Disk, NOT GCS** for `/workspace`
   - Reason: GCS via gcsfuse breaks VS Code (SQLite corruption, file watcher issues)
   - Local: Docker volume
   - Cloud: GCE Persistent Disk (50GB pd-standard)

2. ✅ **Fixed gcloud credentials mount**
   - Mount at `/gcloud-config` (not `~/.config/gcloud`) to avoid permission conflicts
   - Environment var: `GOOGLE_APPLICATION_CREDENTIALS=/gcloud-config/application_default_credentials.json`

3. ✅ **code-server config directory**
   - Let it be ephemeral (don't mount as volume)
   - Created at runtime by entrypoint: `mkdir -p ~/.config/code-server`

---

## Architecture Overview

### Local Mode
```
Your Mac/Linux
└─ Docker Desktop/Engine
   └─ Container: codestation
      ├─ Port 8080 → localhost:8080
      ├─ Volume: workspace (persistent)
      ├─ Mount: ~/.config/gcloud → /gcloud-config (read-only)
      └─ code-server running with --auth none
```

### Cloud Mode (NOT YET IMPLEMENTED)
```
Google Cloud
├─ GCE VM (Container-Optimized OS)
│  ├─ Persistent Disk (50GB pd-standard) → /workspace
│  └─ Docker container: codestation
│     └─ Mounts: /workspace from host
├─ Cloud Load Balancer + IAP
│  └─ Google Auth (specified email only)
└─ Auto-shutdown daemon (2hr idle)
```

---

## Workspace Structure

```
/workspace/
├─ .cstation/
│  ├─ repos.txt          # Git repos to clone/pull on startup
│  │                     # Format: one URL per line
│  │                     # https://github.com/user/repo.git
│  └─ init.sh            # Optional startup script
│                        # Runs after git sync, before code-server
├─ your-project/         # Cloned from repos.txt
└─ README.md
```

**Entrypoint behavior:**
1. Creates `/workspace/.cstation/` if missing
2. Reads `repos.txt`, clones new repos or pulls updates
3. Runs `init.sh` if present
4. Starts code-server on port 8080 with `--auth none`

---

## Completed Steps (6/11)

### Step 1: ✅ Dockerfile
- Base: `codercom/code-server:latest`
- Installs: git, curl, wget, python3, python3-pip, gcloud SDK
- Copies entrypoint script
- Working directory: `/workspace`

### Step 2: ✅ Entrypoint Script
- `scripts/entrypoint.sh`
- Auto-clones/pulls git repos
- Runs optional init script
- Starts code-server with proper permissions

### Step 3: ✅ docker-compose.yml
- Single service: `codestation`
- Volume: `workspace` (persistent data)
- Mount: gcloud config at `/gcloud-config` (read-only)
- Port: 8080:8080
- Restart: unless-stopped

### Step 4: ✅ Local Mode Testing
- Built image successfully (2.16GB)
- Fixed permission issues with code-server config
- Verified accessible at http://localhost:8080
- Container runs cleanly

### Steps 5-6: ✅ CLI Commands (Local)
- Created `src/codestation/cli/commands/docker_commands.py`
- Commands: `up` and `down`
- Options: `--local` (default) or `--cloud` (not yet implemented)
- Registered in `src/codestation/cli/main.py`
- Tested successfully

---

## Remaining Work (Steps 7-11)

### Step 7: Implement `cstation up --cloud` ⬅️ START HERE
**Goal:** Deploy to GCE with Container-Optimized OS

**What to build:**
```python
def _up_cloud(user: str) -> None:
    """Deploy code-server to Google Cloud."""
    # 1. Create GCE VM (Container-Optimized OS)
    #    - Machine type: e2-standard-2
    #    - Image: cos-stable
    #    - Zone: from config or default us-central1-a

    # 2. Create + attach Persistent Disk
    #    - Size: 50GB
    #    - Type: pd-standard
    #    - Name: {vm-name}-data

    # 3. Format and mount disk
    #    - Mount at /workspace on host VM

    # 4. Run Docker container on VM
    #    - Image: gcr.io/project/codestation:latest (push local image)
    #    - Volume: -v /workspace:/workspace
    #    - Port: 8080

    # 5. Copy auto-shutdown script
    #    - From: scripts/vm-auto-shutdown.sh (already exists in repo)
    #    - Install as systemd service
    #    - 2hr idle timeout

    # 6. Return VM external IP
    #    - Show user: "Access at: http://VM_IP:8080"
    #    - Note: Not yet secured (Step 9 adds IAP)
```

**Commands to use:**
```bash
# Create VM
gcloud compute instances create VM_NAME \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --machine-type=e2-standard-2 \
  --zone=ZONE

# Create disk
gcloud compute disks create DISK_NAME \
  --size=50GB \
  --type=pd-standard \
  --zone=ZONE

# Attach disk
gcloud compute instances attach-disk VM_NAME \
  --disk=DISK_NAME \
  --zone=ZONE

# SSH and setup
gcloud compute ssh VM_NAME --zone=ZONE --command="..."
```

**Files to reference:**
- Existing auto-shutdown: `scripts/vm-auto-shutdown.sh`
- Existing install script: `scripts/install-auto-shutdown.sh`

### Step 8: Implement `cstation down --cloud`
**Goal:** Stop or delete GCE VM

**What to build:**
```python
def _down_cloud() -> None:
    """Stop cloud VM (preserve disk) or delete (remove everything)."""
    # Option 1: Stop (preserves disk, can restart)
    gcloud compute instances stop VM_NAME --zone=ZONE

    # Option 2: Delete (removes VM but can preserve disk)
    gcloud compute instances delete VM_NAME --zone=ZONE --keep-disks=data

    # Ask user which they want
```

### Step 9: Setup Cloud Load Balancer + IAP
**Goal:** Add HTTPS + Google Auth

**What to build:**
```python
def _setup_iap(vm_name: str, user: str) -> str:
    """Setup Load Balancer and IAP for VM."""
    # 1. Create Health Check
    # 2. Create Backend Service
    # 3. Add VM instance group
    # 4. Create URL Map
    # 5. Create Target HTTPS Proxy
    # 6. Create Forwarding Rule
    # 7. Enable IAP
    # 8. Add IAM binding for user email
    # 9. Return HTTPS URL
```

This is complex - consider making it optional for first iteration.

### Step 10: End-to-End Testing
**Test:**
```bash
# Local
cstation up --local
# Verify: http://localhost:8080 works
# Verify: Can create files in workspace
cstation down --local

# Cloud (without IAP)
cstation up --cloud --user you@gmail.com
# Verify: Can access via VM IP
# Verify: Git repos cloned
# Verify: Auto-shutdown works
cstation down --cloud
```

### Step 11: Documentation
**Create/update:**
- README.md with new Docker-based approach
- Quick start guide
- Cost breakdown
- Troubleshooting section

---

## Technical Notes for Next Session

### Docker Images Location
- Local: Tagged as `codestation:latest`
- For cloud: Need to push to GCR or Artifact Registry
  ```bash
  docker tag codestation:latest gcr.io/PROJECT_ID/codestation:latest
  docker push gcr.io/PROJECT_ID/codestation:latest
  ```

### Config Management
- Current config is in `~/.codestation/config` (from old VM-based system)
- Contains: `vm_name`, `zone`, `project`, etc.
- Should reuse this for cloud deployment

### Existing Scripts to Leverage
- `scripts/vm-auto-shutdown.sh` - Auto-shutdown daemon (REUSE THIS)
- `scripts/install-auto-shutdown.sh` - Install script (REUSE THIS)
- Don't rebuild what works!

### Cost Estimates (for reference)
```
GCE e2-standard-2 (8hrs/day):
- Compute: $16/month
- Persistent Disk 50GB: $2/month
- Total: $18/month

With IAP (Step 9):
- Load Balancer: ~$18/month
- Total: $36/month

Without IAP:
- Just VM + disk: $18/month
- Access via VM IP (less secure)
```

### AIP Execution Log
Located at: `.aip_artifacts/claude-execution.log`

---

## How to Resume

### Quick Test (verify everything works)
```bash
# 1. Check Docker image exists
docker images | grep codestation

# 2. Test local commands
cstation up --local
# Visit http://localhost:8080
cstation down --local

# 3. Check CLI help
cstation up --help
cstation down --help
```

### Start Step 7 (Cloud Deployment)
```bash
# 1. Read the spec
cat .specwright/specs/docker-codeserver-spec.md

# 2. Check current AIP
cat .specwright/aips/docker-codeserver-spec.yaml

# 3. Review docker_commands.py
cat src/codestation/cli/commands/docker_commands.py

# 4. Implement _up_cloud() function
#    - See "Step 7" section above
#    - Reference existing VM management code if needed
#    - Test frequently with deploy/teardown cycles
```

### Key Command Reference
```bash
# Run spec-based workflow
spec run                    # Continue AIP execution

# Test Docker locally
cstation up --local
cstation down --local

# Check cloud resources
gcloud compute instances list
gcloud compute disks list

# View logs
docker logs codestation
tail -f .aip_artifacts/claude-execution.log
```

---

## Questions to Consider

1. **IAP (Step 9):** Required or optional?
   - Complex setup (~$18/month extra)
   - Could skip initially, just use VM IP
   - Add later when needed for family members

2. **Multi-user:** In scope?
   - Current plan: one VM per user
   - Each gets own `cstation deploy --user email@example.com`
   - Deferred to future iteration?

3. **Managed Instance Groups:** Worth it?
   - Auto-scale to 0 (save money)
   - But adds complexity
   - Decision: Stick with manual start/stop for now

---

## Git Workflow Assumption

**For syncing between local and cloud:**
```bash
# Work locally
cstation up --local
# make changes
git add . && git commit -m "changes"
git push

# Switch to cloud
cstation down --local
cstation up --cloud
# Entrypoint auto-pulls latest from git
# continue working
git push

# Back to local
cstation down --cloud
cstation up --local
# Entrypoint auto-pulls latest
```

**No complex sync mechanism** - just git discipline.

---

## Contact & Context

**Project:** Codestation
**Repo:** `/home/user/codestation`
**Branch:** Should be on `feat/docker-codeserver` (check with `git branch`)
**Spec:** `.specwright/specs/docker-codeserver-spec.md`
**AIP:** `.specwright/aips/docker-codeserver-spec.yaml`

**Current Status:** 6/11 steps complete (54%)
**Blockers:** None
**Next Action:** Implement Step 7 (`cstation up --cloud`)

---

## Success Criteria

When done, you should be able to:
```bash
# Work locally
cstation up --local
# Access at http://localhost:8080

# Deploy to cloud
cstation up --cloud --user you@gmail.com
# Access at http://VM_IP:8080 (or HTTPS if IAP configured)

# Teardown
cstation down --cloud

# All with:
# - Git repos auto-synced
# - Data in BQ/GCS (not local)
# - Auto-shutdown after 2hr idle
# - Cost: ~$18-36/month depending on IAP
```

Good luck! 🚀
