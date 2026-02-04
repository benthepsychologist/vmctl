# Migration Guide

## Upgrading to v3.0.0 (Project Rename: vmws/cstation → vmctl)

**Version 3.0.0 introduces a major branding change:** The package is now called **vmctl**.

### What Changed

| Old (v2.x) | New (v3.0.0) |
|------------|--------------|
| Package name: `vm-workstation-manager` / `codestation` | Package name: `vmctl` |
| CLI command: `vmws` / `cstation` | CLI command: `vmctl` |
| Config directory: `~/.vmws/` / `~/.codestation/` | Config directory: `~/.vmctl/` |
| Import: `from vmws.config import ...` | Import: `from vmctl.config import ...` |

### Backward Compatibility

**Good news:** v3.0.0 includes automatic migration:

✅ **Automatic config migration** - First run copies `~/.vmws/` or `~/.codestation/` → `~/.vmctl/`
✅ **Original config preserved** - Legacy directories are kept for rollback
✅ **VMs continue to work** - No changes needed to existing VMs

### Upgrading

```bash
# Upgrade to v3.0.0
pip install --upgrade vmctl

# Verify version
vmctl --version
# Output: vmctl, version 3.0.0

# Your old config is automatically migrated
vmctl config --show
# Migrating configuration from ~/.codestation to ~/.vmctl...
#   Copied config
# ✓ Migration complete!
```

### Update Your Scripts

Update any scripts using `vmws` or `cstation` to use `vmctl`:

```bash
# Old (v2.x)
vmws start      # or cstation start
vmws tunnel     # or cstation tunnel
vmws stop       # or cstation stop

# New (v3.0.0)
vmctl start
vmctl tunnel
vmctl stop
```

---

## Migrating from Bash to Python Version

This guide helps you migrate from the legacy bash version to the Python package.

## TL;DR

The Python version is **100% backward compatible**. Your existing config and VMs continue to work unchanged:

```bash
# Install Python version
pip install -e .

# Your old config still works
vmctl status  # Same commands, same behavior
```

## Why Migrate?

The Python version offers significant improvements:

- **Type Safety**: Full mypy type checking prevents bugs
- **Better Testing**: 99% test coverage with pytest
- **IDE Support**: Autocomplete and refactoring in IDEs
- **Easier Distribution**: Install via `pip install vmctl`
- **Modern CLI**: Rich terminal output and progress indicators
- **Maintainability**: Cleaner code organization and error handling

## Installation

### Option 1: pip install (Recommended)

```bash
# From source (development)
pip install -e .

# Or from PyPI (when released)
pip install vmctl
```

### Option 2: Keep using bash

The bash version (`bin/vmws`) continues to work. You can keep using it if preferred.

## Compatibility

### Configuration Files

Your existing `~/.vmctl/config` file works with both versions:

```bash
# Bash format (current)
VM_NAME="dev-workstation"
ZONE="us-central1-a"
PROJECT="your-project"
WORKSTATION_DISK="workstation-disk-123"
REGION="us-central1"
```

The Python version:
- ✅ Reads bash format configs
- ✅ Writes back in bash format (for compatibility)
- ✅ Validates values with Pydantic models
- ✅ Future: Will support YAML format too

### Commands

All bash commands work identically in Python:

| Command | Bash | Python | Notes |
|---------|------|--------|-------|
| `vmctl config` | ✅ | ✅ | Same options |
| `vmctl create` | ✅ | ⚠️ | Not yet implemented |
| `vmctl init-fresh` | ✅ | ⚠️ | Not yet implemented |
| `vmctl start` | ✅ | ✅ | Same behavior |
| `vmctl stop` | ✅ | ✅ | Same behavior |
| `vmctl status` | ✅ | ✅ | Enhanced output |
| `vmctl connect` | ✅ | ✅ | Alias for ssh |
| `vmctl ssh` | ✅ | ✅ | Same behavior |
| `vmctl tunnel` | ✅ | ✅ | Same ports |
| `vmctl logs` | ✅ | ✅ | Same log files |
| `vmctl delete` | ✅ | ✅ | Same confirmations |
| `vmctl backup` | ✅ | ✅ | Same snapshots |
| `vmctl restore` | ✅ | ✅ | Same flow |
| `vmctl snapshots` | ✅ | ✅ | Same output |

### Virtual Machines

Your existing VMs work with both versions:
- ✅ No changes needed to VMs
- ✅ Same startup scripts
- ✅ Same auto-shutdown behavior
- ✅ Same SSH access
- ✅ Same IAP tunnels

## Migration Steps

### 1. Install Python Version

```bash
# Ensure Python 3.12+ installed
python3 --version  # Should be 3.12 or higher

# Clone repo (if not already)
git clone https://github.com/benthepsychologist/vmctl.git
cd vmctl

# Install with pip
pip install -e .

# Verify installation
vmctl --version
```

### 2. Test with Existing Config

```bash
# Your existing config should work
vmctl status

# Try other commands
vmctl backup
vmctl snapshots
```

### 3. Gradual Transition

You can use both versions side-by-side:

```bash
# Use Python version (if in PATH)
vmctl status

# Use bash version explicitly
./bin/vmws status
```

### 4. Verify Behavior

Test key workflows:

```bash
# VM lifecycle
vmctl status
vmctl start
vmctl stop

# Tunneling
vmctl tunnel

# Backups
vmctl backup
vmctl snapshots
```

## Differences

### Enhanced Features

The Python version adds:

**Rich Terminal Output**:
```bash
# Colored progress indicators
vmctl start
Starting VM test-vm...
✓ VM started successfully
```

**Better Error Messages**:
```bash
# Clear, actionable errors
vmctl start
Error: VM not found
→ Run 'vmctl create' to create a VM first
```

**Type Validation**:
```bash
# Config validation
vmctl config --vm-name "123-invalid"
Error: VM name must start with a letter
```

### Not Yet Implemented

The following commands are stubs in the Python version:

- `vmctl create` - Use bash version for now
- `vmctl init-fresh` - Use bash version for now

These will be implemented in a future release.

## Troubleshooting

### Python version not found

```bash
# Check pip installation
which vmctl

# If not found, try
pip install -e . --force-reinstall

# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Import errors

```bash
# Install dependencies
pip install -e ".[dev]"
```

### Config not loading

```bash
# Check config file exists
ls -la ~/.vmctl/config

# Check format is correct
cat ~/.vmctl/config
```

### VM commands fail

```bash
# Ensure gcloud configured
gcloud auth list
gcloud config get-value project

# Check config has project
vmctl config --show
```

## Getting Help

- Check existing issues: https://github.com/benthepsychologist/vmctl/issues
- Read the docs: README.md, CONTRIBUTING.md
- Review test files: `tests/` directory for usage examples

## Rollback

To revert to bash version:

```bash
# Uninstall Python package
pip uninstall vmctl

# Use bash script directly
./bin/vmws status

# Or re-install bash version
./install.sh
```

Your config and VMs remain unchanged.

## Future Plans

Upcoming Python version features:

- [ ] Complete `create` and `init-fresh` implementation
- [ ] YAML config format support
- [ ] Cloud Workstation API integration (replace gcloud CLI)
- [ ] Interactive prompts with validation
- [ ] Parallel VM operations
- [ ] Enhanced monitoring and logging
- [ ] Plugin system for custom workflows

## Feedback

Please report issues or suggestions:
- GitHub Issues: https://github.com/benthepsychologist/vmctl/issues
- Include: Python version, OS, error messages, steps to reproduce
