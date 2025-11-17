# Contributing to VM Workstation Manager

Thank you for your interest in contributing! This guide will help you understand the codebase and make improvements.

## Python Version (Current)

The project is now implemented in Python for better maintainability, testing, and distribution.

### Quick Start

```bash
# Prerequisites: Python 3.12+, gcloud CLI
python3 --version  # Should be 3.12+

# Clone and setup
git clone https://github.com/benthepsychologist/codestation.git
cd codestation

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
vmws --version
```

### Code Structure

```
vm-workstation-manager/
├── src/vmws/                   # Python package
│   ├── __init__.py            # Package metadata
│   ├── cli/                   # CLI implementation
│   │   ├── main.py           # Entry point
│   │   └── commands/         # Command implementations
│   │       ├── vm_commands.py
│   │       ├── backup_commands.py
│   │       └── config_commands.py
│   ├── core/                  # Core business logic
│   │   ├── vm.py             # VM operations
│   │   ├── disk.py           # Disk/snapshot operations
│   │   └── tunnel.py         # IAP tunnel management
│   ├── config/                # Configuration
│   │   ├── manager.py        # Config file handling
│   │   └── models.py         # Pydantic models
│   └── utils/                 # Utilities
├── tests/                     # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_*.py             # Unit tests
│   └── integration/          # Integration tests
├── bin/vmws                   # Legacy bash CLI
├── scripts/                   # VM setup scripts
├── pyproject.toml             # Project config
└── docs/                      # Documentation
```

### Development Workflow

1. **Make changes** to Python code in `src/vmws/`

2. **Run tests**:
   ```bash
   pytest                          # All tests
   pytest tests/test_config.py -v  # Specific test
   pytest --cov=src/vmws          # With coverage
   ```

3. **Type checking**:
   ```bash
   mypy src/vmws
   ```

4. **Linting**:
   ```bash
   ruff check src/vmws tests
   ruff format src/vmws tests  # Auto-fix
   ```

5. **Test locally**:
   ```bash
   vmws --help
   vmws status
   ```

### Code Style

- **Type hints**: All functions must have type hints
- **Docstrings**: Use Google-style docstrings
- **Error handling**: Use custom exceptions from `core.exceptions`
- **Testing**: Aim for 80%+ coverage
- **Formatting**: Use ruff (line length: 100)

Example:
```python
def create_snapshot(vm_name: str, description: str | None = None) -> str:
    """Create a snapshot of the VM disk.

    Args:
        vm_name: Name of the VM instance
        description: Optional snapshot description

    Returns:
        Snapshot name

    Raises:
        DiskError: If snapshot creation fails
    """
    # Implementation
```

### Adding New Commands

1. **Create command function** in appropriate module:
   ```python
   # src/vmws/cli/commands/vm_commands.py
   @click.command()
   @click.option("--name", help="VM name")
   def mycommand(name: str) -> None:
       """Description of your command."""
       console.print(f"Running command for {name}")
   ```

2. **Register in main.py**:
   ```python
   # src/vmws/cli/main.py
   from vmws.cli.commands import vm_commands
   cli.add_command(vm_commands.mycommand)
   ```

3. **Add tests**:
   ```python
   # tests/test_cli_vm.py
   def test_mycommand(runner):
       result = runner.invoke(cli, ["mycommand", "--name", "test"])
       assert result.exit_code == 0
   ```

4. **Update documentation**: README.md, docstrings

### Testing Guidelines

**Unit Tests**: Mock external dependencies
```python
@patch("vmws.core.vm.run_command")
def test_vm_start(mock_run: MagicMock) -> None:
    mock_run.return_value = CommandResult(0, "OK", "")
    vm = VMManager(config)
    vm.start()
    mock_run.assert_called_once()
```

**Integration Tests**: Test full workflows (use markers)
```python
@pytest.mark.integration
def test_full_workflow():
    # Tests that create real resources
    pass
```

**Run only unit tests**:
```bash
pytest -m "not integration"
```

### Pre-commit Checklist

Before committing:
- [ ] All tests pass: `pytest`
- [ ] Type checking passes: `mypy src/vmws`
- [ ] Linting passes: `ruff check src/vmws tests`
- [ ] Coverage ≥ 80%: `pytest --cov=src/vmws --cov-fail-under=80`
- [ ] Docstrings added
- [ ] Manual testing done

### Building and Distribution

```bash
# Build package
python -m build

# Check distribution
twine check dist/*

# Test installation
pip install dist/*.whl
```

## Bash Version (Legacy)

The original bash implementation is still available in `bin/vmws` and `scripts/`.

### Overview (Bash)

```
vm-workstation-manager/
├── bin/vmws                    # Main CLI entry point
├── scripts/                    # Core automation scripts
│   ├── run-vm-test-workflow.sh   # Orchestrates full VM creation
│   ├── create-test-vm.sh          # Creates VM from snapshot
│   ├── setup-vm-environment.sh    # Installs dev tools on VM
│   ├── vm-auto-shutdown.sh        # Monitors idle time
│   └── cleanup-test-vm.sh         # Deletes all resources
├── docs/                       # Documentation
└── install.sh                  # Installation script
```

## Understanding the Workflow

### 1. VM Creation Flow

```
User runs: vmws create
    ↓
run-vm-test-workflow.sh
    ↓
    ├─ create-test-vm.sh
    │   ├─ Snapshot workstation disk
    │   ├─ Create new VM with boot disk
    │   └─ Attach snapshot disk as data disk
    ↓
    ├─ Wait for SSH ready
    ↓
    ├─ Fix file permissions
    ↓
    ├─ setup-vm-environment.sh
    │   ├─ Install Docker CE
    │   ├─ Install code-server
    │   ├─ Install neovim
    │   └─ Configure services
    ↓
    ├─ install-auto-shutdown.sh
    │   └─ Set up 2hr idle timeout
    ↓
    ├─ Run validation tests
    └─ Generate report
```

### 2. Key Components

**bin/vmws** - Main CLI
- Command dispatcher
- Configuration management
- VM lifecycle operations
- User interface

**scripts/create-test-vm.sh** - VM Creator
- Takes snapshot of workstation home disk
- Creates new VM with Debian 12 boot disk
- Attaches snapshot as `/mnt/home`
- Configures startup script for auto-mount

**scripts/setup-vm-environment.sh** - Environment Setup
- Installs Docker CE from official repos
- Installs code-server via install script
- Configures code-server as systemd service
- Sets up neovim

**scripts/vm-auto-shutdown.sh** - Auto-Shutdown Monitor
- Runs as systemd service on VM
- Checks every 5 minutes for activity
- Tracks SSH and code-server connections
- Shuts down after 2hr idle (configurable)

**scripts/run-vm-test-workflow.sh** - Orchestrator
- Main workflow that ties everything together
- Runs all steps in sequence
- Performs validation tests
- Generates markdown report

## Configuration

### CLI Configuration

Config file: `~/.vmws/config`

```bash
VM_NAME="dev-workstation"
ZONE="us-central1-a"
PROJECT="your-project-id"
```

### VM Configuration

Edit `scripts/create-test-vm.sh`:

```bash
WORKSTATION_DISK="..."     # Source disk name
REGION="..."               # Region for snapshot
ZONE="..."                 # Zone for VM
VM_NAME="..."              # VM name
DISK_SIZE="200GB"          # Data disk size
MACHINE_TYPE="e2-standard-2"  # VM machine type
```

### Auto-Shutdown Configuration

Edit on VM: `/usr/local/bin/vm-auto-shutdown.sh`

```bash
IDLE_TIMEOUT_MINUTES=120    # Default: 2 hours
CHECK_INTERVAL_SECONDS=300  # Default: 5 minutes
```

## Making Changes

### Local Development

```bash
# Clone the repo
git clone https://github.com/benthepsychologist/codestation.git
cd codestation

# Make changes
vim bin/vmws

# Test locally
./bin/vmws --help

# Install to test
./install.sh
```

### Testing Changes

1. **Test CLI commands**
   ```bash
   vmws config
   vmws status
   vmws --help
   ```

2. **Test VM creation** (requires Cloud Workstation)
   ```bash
   vmws create
   ```

3. **Test from local machine**
   ```bash
   vmws start
   vmws tunnel
   vmws stop
   ```

### Code Style

- Use bash best practices
- Set `set -e` for error handling
- Use descriptive variable names (UPPERCASE for globals)
- Add comments for complex logic
- Use colored output for user feedback:
  - GREEN for success
  - RED for errors
  - YELLOW for warnings
  - BLUE for info

### Adding New Commands

1. **Add command function** in `bin/vmws`:
   ```bash
   cmd_yourcommand() {
       echo -e "${YELLOW}Your command...${NC}"
       # Implementation
   }
   ```

2. **Add to dispatcher** in `main()`:
   ```bash
   case "$1" in
       yourcommand)
           cmd_yourcommand
           ;;
   ```

3. **Update help** in `show_help()`:
   ```
   yourcommand         Description of your command
   ```

4. **Document** in README.md

## Common Modifications

### Change Machine Type

Edit `scripts/create-test-vm.sh`:
```bash
MACHINE_TYPE="e2-standard-4"  # Upgrade to 4 vCPU, 16GB RAM
```

### Change Disk Size

Edit `scripts/create-test-vm.sh`:
```bash
DISK_SIZE="500GB"  # Increase data disk
```

### Change Auto-Shutdown Timeout

On VM:
```bash
sudo vim /usr/local/bin/vm-auto-shutdown.sh
# Change IDLE_TIMEOUT_MINUTES
sudo systemctl restart vm-auto-shutdown
```

### Add New Software to VM

Edit `scripts/setup-vm-environment.sh`:
```bash
# Add to the end
echo "📦 Installing your-tool..."
sudo apt-get install -y your-tool
```

### Customize code-server

Edit `scripts/setup-vm-environment.sh`:
```bash
# Modify config
cat > ~/.config/code-server/config.yaml <<EOF
bind-addr: 127.0.0.1:8080
auth: password
password: your-custom-password
cert: false
EOF
```

## Debugging

### Enable Debug Mode

Add to any script:
```bash
set -x  # Enable debug output
```

### Check VM Logs

```bash
vmws ssh
sudo journalctl -u code-server -f
sudo journalctl -u vm-auto-shutdown -f
```

### Check Script Execution

Add echo statements:
```bash
echo "DEBUG: Variable value is: $VARIABLE"
```

## Testing Checklist

Before submitting changes:

- [ ] CLI help text updated
- [ ] README.md updated
- [ ] Code has comments
- [ ] Tested on fresh VM
- [ ] Tested from local machine
- [ ] No hardcoded values
- [ ] Error handling added
- [ ] User feedback clear

## Architecture Decisions

### Why Snapshot Instead of Image?

- Faster creation (snapshots are incremental)
- Preserves exact file permissions
- Works with any workstation configuration
- Cheaper storage

### Why Separate Boot and Data Disks?

- Clean OS installation on boot disk
- All user data on data disk
- Easy to resize or upgrade OS
- Better separation of concerns

### Why Systemd Services?

- Reliable auto-start on boot
- Easy logging with journald
- Standard service management
- Automatic restart on failure

### Why Bash Instead of Python/Go?

- No dependencies to install
- Works everywhere (Cloud Shell, VMs, local)
- Easy to read and modify
- Shell commands are natural fit

## Resources

- [gcloud CLI Reference](https://cloud.google.com/sdk/gcloud/reference)
- [code-server Docs](https://coder.com/docs/code-server)
- [Systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Bash Best Practices](https://google.github.io/styleguide/shellguide.html)

## Getting Help

- Open an issue on GitHub
- Check existing issues and PRs
- Read the full documentation in `docs/`
- Review the code comments

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Include in PR:
- Description of changes
- Why the change is needed
- Test results
- Screenshots if UI changes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
