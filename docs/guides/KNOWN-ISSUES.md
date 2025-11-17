# Known Issues and Limitations

This document tracks known issues, limitations, and planned improvements for the VM Workstation Manager Python package.

**Last Updated:** 2024-11-17
**Version:** 2.0.0

## Current Limitations

### Not Implemented (Use Bash Version)

The following commands are **not yet implemented** in the Python version. Use the bash version (`./bin/vmws`) for these operations:

#### `vmws create`
**Status:** Not implemented
**Workaround:** Use bash version
```bash
# Use bash script instead
./bin/vmws create
```

**Planned:** v2.1.0 (next release)

#### `vmws init-fresh`
**Status:** Not implemented
**Workaround:** Use bash version
```bash
# Use bash script instead
./bin/vmws init-fresh
```

**Planned:** v2.1.0 (next release)

### Partial Implementations

None currently - all implemented commands are feature-complete.

## Minor Issues

### Linting Warnings

**Issue:** 22 minor ruff linting warnings
**Impact:** Low - does not affect functionality
**Details:**
- Long lines (>100 chars) in some CLI output
- Exception handling style (B904) in CLI commands

**Status:** Will be addressed in future patch releases

**Example:**
```python
# Current (works but linter warns)
except DiskError as e:
    raise click.Abort()

# Preferred
except DiskError as e:
    raise click.Abort() from e
```

### Integration Tests Skipped

**Issue:** Integration tests require live GCP resources
**Impact:** Low - unit tests provide 99% coverage
**Workaround:** Run integration tests manually with GCP sandbox

**Status:** Planning CI integration with test project (v2.2.0)

## Compatibility Notes

### Bash vs Python Differences

The Python version is designed to be backward compatible, but there are minor differences:

#### Output Formatting

**Bash Version:**
```
Starting VM dev-workstation...
VM started successfully
```

**Python Version:**
```
Starting VM dev-workstation...
✓ VM started successfully
```

**Impact:** None - purely cosmetic

#### Error Messages

**Python Version** provides more detailed error messages:

**Bash:**
```
Error: VM not found
```

**Python:**
```
Error: VM not found
→ Run 'vmws create' to create a VM first
```

**Impact:** Positive - better UX

### Configuration Files

Both versions use the same `~/.vmws/config` format:
- ✅ Python reads bash format
- ✅ Python writes bash format
- ✅ Both versions can be used interchangeably

**No migration needed.**

## Platform-Specific Issues

### macOS

No known issues.

### Linux

No known issues.

### Windows

**Status:** Not tested
**Support:** Windows is not officially supported
**Workaround:** Use WSL2 (Windows Subsystem for Linux)

Expected to work in WSL2, but not tested.

## Dependencies

### Python Version

**Requirement:** Python 3.12+
**Reason:** Uses modern type hints (PEP 604: `str | None`)

**Workaround for Python 3.10/3.11:**
Not supported. Upgrade to Python 3.12+ or use bash version.

### gcloud CLI

**Requirement:** gcloud CLI must be installed and configured
**Impact:** All VM operations fail without gcloud

**Check installation:**
```bash
gcloud --version
gcloud auth list
```

**Install:** https://cloud.google.com/sdk/docs/install

## Planned Improvements

### v2.1.0 (Next Release)
- [ ] Implement `vmws create` command
- [ ] Implement `vmws init-fresh` command
- [ ] Add progress bars for long-running operations
- [ ] Improve error messages with suggestions

### v2.2.0 (Future)
- [ ] Replace gcloud subprocess calls with Cloud Compute API
- [ ] Add YAML config format support
- [ ] Interactive configuration wizard
- [ ] Parallel operations (start/stop multiple VMs)

### v2.3.0 (Future)
- [ ] Plugin system for custom workflows
- [ ] Cloud Workstations API integration
- [ ] Enhanced monitoring and metrics
- [ ] Cost tracking and optimization suggestions

## Workarounds

### Mixed Bash/Python Usage

You can use both versions side-by-side:

```bash
# Use Python for most commands
vmws start
vmws stop
vmws backup

# Use bash for create/init-fresh
./bin/vmws create
./bin/vmws init-fresh
```

Both versions share the same config file (`~/.vmws/config`), so this works seamlessly.

### Force Bash Version

If you need to use bash exclusively:

```bash
# Uninstall Python package
pip uninstall vm-workstation-manager

# Use bash script directly
./bin/vmws <command>

# Or install bash version globally
./install.sh
```

## Reporting Issues

Found a bug or have a feature request?

1. **Check existing issues:** https://github.com/benthepsychologist/codestation/issues
2. **Search this document** for known issues
3. **Report new issue** with:
   - Python version (`python --version`)
   - Package version (`vmws --version`)
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages (if any)

**Issue Template:**
```markdown
## Bug Report

**Version:** `vmws --version` output
**Python:** `python --version` output
**OS:** macOS/Linux/WSL2

**Command:**
`vmws command here`

**Expected:**
What should happen

**Actual:**
What actually happened

**Error:**
```
Error message if any
```

**Additional context:**
Any other relevant information
```

## FAQs

### Why aren't create/init-fresh implemented yet?

These commands require complex VM creation logic with multiple steps (snapshots, disk attachment, environment setup). They're planned for v2.1.0 to ensure proper testing and API integration.

### Will the bash version be deprecated?

The bash version will remain available but won't receive new features. It serves as a fallback for commands not yet in Python and for environments where Python 3.12+ isn't available.

### Can I contribute fixes?

Yes! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

### When will all commands be implemented?

Target: v2.1.0 (estimated 1-2 months after v2.0.0 release)

## Version History

### v2.0.0 (Current)
- ✅ Python package structure
- ✅ All VM lifecycle commands (except create/init-fresh)
- ✅ Backup and restore
- ✅ Configuration management
- ✅ 99% test coverage
- ⚠️ create/init-fresh not implemented

### v1.x (Bash)
- ✅ All features implemented
- ✅ Stable and tested
- ⚠️ Limited to bash environments
