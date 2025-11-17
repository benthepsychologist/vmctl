# Migration Guide

## Upgrading to v3.0.0 (Project Rename: vmws → cstation)

**Version 3.0.0 introduces a major branding change:** The package is now called **Codestation** with the CLI command `cstation`.

### What Changed

| Old (v2.x) | New (v3.0.0) |
|------------|--------------|
| Package name: `vm-workstation-manager` | Package name: `codestation` |
| CLI command: `vmws` | CLI command: `cstation` |
| Config directory: `~/.vmws/` | Config directory: `~/.codestation/` |
| Import: `from vmws.config import ...` | Import: `from codestation.config import ...` |

### Backward Compatibility

**Good news:** v3.0.0 maintains full backward compatibility:

✅ **`vmws` command still works** - Shows deprecation warning, forwards to `cstation`
✅ **Automatic config migration** - First run copies `~/.vmws/` → `~/.codestation/`
✅ **Original config preserved** - `~/.vmws/` is kept for rollback
✅ **VMs continue to work** - No changes needed to existing VMs

### Upgrading

```bash
# Upgrade to v3.0.0
pip install --upgrade codestation

# Verify version
cstation --version
# Output: cstation, version 3.0.0

# Your old config is automatically migrated
cstation config --show
# Migrating configuration from ~/.vmws to ~/.codestation...
#   Copied config
# ✓ Migration complete!
```

### Update Your Scripts

Update any scripts using `vmws` to use `cstation`:

```bash
# Old (v2.x)
vmws start
vmws tunnel
vmws stop

# New (v3.0.0)
cstation start
cstation tunnel
cstation stop
```

### Deprecation Timeline

- **v3.0.0 (current)**: `vmws` command works with deprecation warning
- **v4.0.0 (future)**: `vmws` command will be removed

**Recommendation:** Update to `cstation` now to avoid warnings and prepare for v4.0.0.

---

## Migrating from Bash to Python Version

This guide helps you migrate from the legacy bash version to the Python package.

## TL;DR

The Python version is **100% backward compatible**. Your existing config and VMs continue to work unchanged:

```bash
# Install Python version
pip install -e .

# Your old config still works
cstation status  # Same commands, same behavior
```

## Why Migrate?

The Python version offers significant improvements:

- **Type Safety**: Full mypy type checking prevents bugs
- **Better Testing**: 99% test coverage with pytest
- **IDE Support**: Autocomplete and refactoring in IDEs
- **Easier Distribution**: Install via `pip install vmws`
- **Modern CLI**: Rich terminal output and progress indicators
- **Maintainability**: Cleaner code organization and error handling

## Installation

### Option 1: pip install (Recommended)

```bash
# From source (development)
pip install -e .

# Or from PyPI (when released)
pip install vm-workstation-manager
```

### Option 2: Keep using bash

The bash version (`bin/vmws`) continues to work. You can keep using it if preferred.

## Compatibility

### Configuration Files

Your existing `~/.codestation/config` file works with both versions:

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
| `cstation config` | ✅ | ✅ | Same options |
| `cstation create` | ✅ | ⚠️ | Not yet implemented |
| `cstation init-fresh` | ✅ | ⚠️ | Not yet implemented |
| `cstation start` | ✅ | ✅ | Same behavior |
| `cstation stop` | ✅ | ✅ | Same behavior |
| `cstation status` | ✅ | ✅ | Enhanced output |
| `cstation connect` | ✅ | ✅ | Alias for ssh |
| `cstation ssh` | ✅ | ✅ | Same behavior |
| `cstation tunnel` | ✅ | ✅ | Same ports |
| `cstation logs` | ✅ | ✅ | Same log files |
| `cstation delete` | ✅ | ✅ | Same confirmations |
| `cstation backup` | ✅ | ✅ | Same snapshots |
| `cstation restore` | ✅ | ✅ | Same flow |
| `cstation snapshots` | ✅ | ✅ | Same output |

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
git clone https://github.com/benthepsychologist/codestation.git
cd codestation

# Install with pip
pip install -e .

# Verify installation
cstation --version
```

### 2. Test with Existing Config

```bash
# Your existing config should work
cstation status

# Try other commands
cstation backup
cstation snapshots
```

### 3. Gradual Transition

You can use both versions side-by-side:

```bash
# Use Python version (if in PATH)
cstation status

# Use bash version explicitly
./bin/vmws status
```

### 4. Verify Behavior

Test key workflows:

```bash
# VM lifecycle
cstation status
cstation start
cstation stop

# Tunneling
cstation tunnel

# Backups
cstation backup
cstation snapshots
```

## Differences

### Enhanced Features

The Python version adds:

**Rich Terminal Output**:
```bash
# Colored progress indicators
cstation start
Starting VM test-vm...
✓ VM started successfully
```

**Better Error Messages**:
```bash
# Clear, actionable errors
cstation start
Error: VM not found
→ Run 'cstation create' to create a VM first
```

**Type Validation**:
```bash
# Config validation
cstation config --vm-name "123-invalid"
Error: VM name must start with a letter
```

### Not Yet Implemented

The following commands are stubs in the Python version:

- `cstation create` - Use bash version for now
- `cstation init-fresh` - Use bash version for now

These will be implemented in a future release.

## Troubleshooting

### Python version not found

```bash
# Check pip installation
which vmws

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
ls -la ~/.codestation/config

# Check format is correct
cat ~/.codestation/config
```

### VM commands fail

```bash
# Ensure gcloud configured
gcloud auth list
gcloud config get-value project

# Check config has project
cstation config --show
```

## Getting Help

- Check existing issues: https://github.com/benthepsychologist/codestation/issues
- Read the docs: README.md, CONTRIBUTING.md
- Review test files: `tests/` directory for usage examples

## Rollback

To revert to bash version:

```bash
# Uninstall Python package
pip uninstall codestation

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
- GitHub Issues: https://github.com/benthepsychologist/codestation/issues
- Include: Python version, OS, error messages, steps to reproduce
