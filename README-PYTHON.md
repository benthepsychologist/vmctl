# VM Workstation Manager - Python Installation

This is the Python version of the VM Workstation Manager CLI tool.

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/benthepsychologist/vm-workstation-manager.git
cd vm-workstation-manager

# Create virtual environment with Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
vmws --version
```

### Using uv (Recommended)

```bash
# Install with uv
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### From PyPI (Coming Soon)

```bash
pip install vm-workstation-manager
```

## Quick Start

```bash
# Configure your VM
vmws config --vm-name my-dev-vm --zone us-central1-a

# Create a fresh VM
vmws init-fresh

# Or migrate from existing Cloud Workstation
vmws create

# Daily usage
vmws start
vmws tunnel  # Access code-server at http://localhost:8080
vmws stop
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/vmws --cov-report=html

# Run specific test file
pytest tests/test_config.py -v
```

### Type Checking

```bash
mypy src/vmws
```

### Linting

```bash
ruff check src/vmws tests
```

### Building the Package

```bash
python -m build
```

## Migrating from Bash Version

The Python version is fully backward compatible with the bash version:

- Reads existing `~/.vmws/config` files
- Same command structure and behavior
- No changes to your existing VMs

See [MIGRATION.md](MIGRATION.md) for details.

## Features

- ✅ Type-safe Python implementation
- ✅ Comprehensive test coverage
- ✅ Rich terminal output
- ✅ Easy to extend and maintain
- ✅ pip-installable package
- ✅ IDE autocomplete support

## Requirements

- Python 3.12+
- gcloud CLI installed and configured
- Google Cloud project with Compute Engine API enabled

## Documentation

- [Main README](README.md) - Feature overview and usage
- [MIGRATION.md](MIGRATION.md) - Migration guide from bash version
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details
