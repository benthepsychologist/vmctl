# Quick Start Guide

Get your self-managed dev VM running in 10 minutes.

## 1. Install (Local Machine)

```bash
# Clone repo
git clone <your-repo-url>
cd vm-workstation-manager

# Install CLI
./install.sh

# Or manually
cp bin/vmws /usr/local/bin/vmws
chmod +x /usr/local/bin/vmws
```

## 2. Configure

```bash
# Set your defaults
vmws config --vm-name dev-vm --zone us-central1-a --project your-project-id

# Or interactive
vmws config
```

## 3. Create VM (From Cloud Workstation)

```bash
# SSH into your Cloud Workstation
# Clone this repo there

cd vm-workstation-manager
./bin/vmws create

# This takes ~6 minutes and creates:
# - VM with your workstation data
# - Docker, code-server, neovim installed
# - Auto-shutdown (2hr idle)
# - Detailed report
```

## 4. Use (From Local Machine)

```bash
# Start VM
vmws start

# Connect to code-server (web VS Code)
vmws tunnel
# Then open http://localhost:8080

# Or SSH
vmws ssh

# Check status
vmws status

# Stop when done (or auto-shuts after 2hr idle)
vmws stop
```

## 5. Daily Workflow

```bash
# Morning
vmws start && vmws tunnel &
open http://localhost:8080

# Work all day
# ...

# Evening (or let it auto-shutdown)
vmws stop
```

## Commands

```bash
vmws create     # Create VM (from workstation)
vmws start      # Start VM
vmws stop       # Stop VM
vmws status     # Check status
vmws tunnel     # Code-server tunnel
vmws ssh        # SSH into VM
vmws logs       # Auto-shutdown logs
vmws delete     # Delete everything
vmws --help     # Full help
```

## Cost Savings

- **Before:** $150/month (Cloud Workstation)
- **After:** $26-59/month (self-managed VM)
- **Savings:** $91-124/month (61-83%)

## Troubleshooting

**VM won't start?**
```bash
vmws status
```

**Can't connect to code-server?**
```bash
vmws ssh
sudo systemctl restart code-server
```

**Auto-shutdown not working?**
```bash
vmws logs
```

## What's Next?

1. **Test it** - Use for a few days
2. **Validate** - Make sure your workflow works
3. **Migrate** - Delete Cloud Workstation
4. **Save** - Enjoy $91-124/month savings

## Full Documentation

- `README.md` - Complete overview
- `docs/VM-AUTOMATION-GUIDE.md` - Detailed guide
- `vmws --help` - CLI reference

---

**Questions?** Open an issue or check the full README.
