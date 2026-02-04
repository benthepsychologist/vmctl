# Codestation Documentation

Complete documentation for Codestation - Self-managed development environments on Google Cloud.

## Getting Started

- **[Main README](../README.md)** - Project overview, quick start, and features
- **[Quick Start Guide](guides/QUICKSTART.md)** - Get up and running in 10 minutes
- **[Migration Guide](guides/MIGRATION.md)** - Upgrade from v2.x to v3.0, migrate from Cloud Workstations

## User Guides

- **[Quick Start](guides/QUICKSTART.md)** - Fast setup guide
- **[Troubleshooting](guides/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Known Issues](guides/KNOWN-ISSUES.md)** - Current limitations and workarounds
- **[VM Automation Guide](VM-AUTOMATION-GUIDE.md)** - Advanced automation workflows

## Development

- **[Contributing](development/CONTRIBUTING.md)** - Development setup and guidelines
- **[Architecture](development/ARCHITECTURE.md)** - Technical architecture and design
- **[Release Process](development/RELEASE.md)** - How to create releases
- **[Persistent Disk Contents](development/PERSISTENT-DISK-CONTENTS.md)** - VM disk structure

## Quick Links

### Installation
```bash
pip install vmctl
vmctl --version
```

### Common Commands
```bash
vmctl config          # Configure VM settings
vmctl init-fresh      # Create new VM
vmctl start           # Start VM
vmctl tunnel          # Connect to code-server
vmctl stop            # Stop VM
```

### Getting Help

- [GitHub Issues](https://github.com/benthepsychologist/vmctl/issues)
- [Troubleshooting Guide](guides/TROUBLESHOOTING.md)
- [Known Issues](guides/KNOWN-ISSUES.md)

## Documentation Structure

```
docs/
├── README.md                          # This file
├── guides/                            # User guides
│   ├── QUICKSTART.md                 # Quick start guide
│   ├── MIGRATION.md                  # Migration & upgrade guide
│   ├── TROUBLESHOOTING.md            # Troubleshooting guide
│   └── KNOWN-ISSUES.md               # Known issues & workarounds
├── development/                       # Developer documentation
│   ├── CONTRIBUTING.md               # Contributing guide
│   ├── ARCHITECTURE.md               # Technical architecture
│   ├── RELEASE.md                    # Release process
│   └── PERSISTENT-DISK-CONTENTS.md   # Disk structure reference
└── VM-AUTOMATION-GUIDE.md            # Advanced automation guide
```
