# Integration Tests

Integration tests that create real GCP resources to validate the complete `vmws` workflow.

## ⚠️ Important Notes

- **These tests create real GCP resources** (VMs, disks, snapshots)
- **You will be charged** for the resources while they exist
- **Resources are cleaned up automatically** after tests complete
- Tests are **disabled by default** - must be explicitly enabled

## Running Integration Tests

### Prerequisites

1. **GCP Authentication:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **vmws Installed:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Workstation Disk Name:**
   You need the name of your Cloud Workstation disk to snapshot.

   Find it with:
   ```bash
   gcloud compute disks list --filter="name~workstations"
   ```

### Method 1: Run as pytest

```bash
# Enable integration tests and run
VMWS_INTEGRATION_TESTS=1 \
VMWS_WORKSTATION_DISK=workstations-YOUR-DISK-ID \
pytest tests/integration/test_vm_workstation_integration.py -v -s

# With custom zone/region
VMWS_INTEGRATION_TESTS=1 \
VMWS_WORKSTATION_DISK=workstations-YOUR-DISK-ID \
VMWS_ZONE=us-central1-a \
VMWS_REGION=us-central1 \
pytest tests/integration/test_vm_workstation_integration.py -v -s
```

### Method 2: Run as standalone script

```bash
# Basic test with defaults (e2-standard-2, 200GB)
python tests/integration/test_vm_workstation_integration.py \
  --workstation-disk workstations-YOUR-DISK-ID

# Test with larger VM and disk
python tests/integration/test_vm_workstation_integration.py \
  --workstation-disk workstations-YOUR-DISK-ID \
  --machine-type n2-standard-4 \
  --disk-size 500

# Run without cleanup (to inspect resources)
python tests/integration/test_vm_workstation_integration.py \
  --workstation-disk workstations-YOUR-DISK-ID \
  --no-cleanup

# Custom zone/region
python tests/integration/test_vm_workstation_integration.py \
  --workstation-disk workstations-YOUR-DISK-ID \
  --zone us-central1-a \
  --region us-central1
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VMWS_INTEGRATION_TESTS` | Yes (pytest only) | - | Must be "1" to enable integration tests |
| `VMWS_WORKSTATION_DISK` | Yes | - | Name of workstation disk to snapshot |
| `VMWS_ZONE` | No | northamerica-northeast1-b | GCP zone |
| `VMWS_REGION` | No | northamerica-northeast1 | GCP region |
| `VMWS_PROJECT` | No | gcloud default | GCP project ID |
| `VMWS_MACHINE_TYPE` | No | e2-standard-2 | VM machine type (e2-standard-4, n2-standard-2, etc.) |
| `VMWS_DISK_SIZE_GB` | No | 200 | Data disk size in GB |

**Note:** Cloud Workstation cost is calculated automatically based on your VM specs (same compute + $0.20/hour always-on fee = $146/month extra).

## What The Test Does

The integration test replicates the complete VM workstation creation workflow:

### Workflow Steps

1. **Create Snapshot** - Snapshots the workstation disk
2. **Create Data Disk** - Creates 200GB disk from snapshot
3. **Create VM** - Creates e2-standard-2 VM with Debian 12
4. **Wait for SSH** - Waits for SSH to become available
5. **Fix Permissions** - Sets correct ownership on user files
6. **Install Dev Environment** - Installs Docker, code-server, neovim
7. **Install Auto-Shutdown** - Sets up 2-hour idle shutdown
8. **Run Validation Tests** - Validates all functionality works

### Validation Tests

- ✅ Disk mounted at `/mnt/home`
- ✅ Files accessible in `/mnt/home/user/`
- ✅ Specific directories exist (life-cockpit)
- ✅ File read access works
- ✅ Docker is running
- ✅ code-server is running

### Generated Report

The test generates a detailed Markdown report:

```
/home/user/vm-integration-test-report-YYYYMMDD-HHMMSS.md
```

The report includes:
- Executive summary with pass/fail status
- **Actual test cost breakdown** (TRUE cost based on resource duration)
- Resource creation details
- Step-by-step workflow results
- Validation test results
- **Personalized cost analysis** (using your machine type, disk size, and workstation cost)
- Monthly cost projections (24/7 and 8hr/day scenarios)
- Savings comparison vs Cloud Workstation
- Access instructions
- Cleanup instructions

## Resource Cleanup

### Automatic Cleanup (Default)

Resources are automatically cleaned up after test completion:
- ✅ VM instance deleted
- ✅ Data disk deleted
- ✅ Snapshot deleted

### Manual Cleanup

If you used `--no-cleanup`, clean up manually:

```bash
# Using vmws
vmws delete --yes
gcloud compute snapshots delete test-vm-TIMESTAMP-snapshot --quiet

# Or manual gcloud commands
gcloud compute instances delete test-vm-TIMESTAMP --zone=ZONE --quiet
gcloud compute disks delete test-vm-TIMESTAMP-disk --zone=ZONE --quiet
gcloud compute snapshots delete test-vm-TIMESTAMP-snapshot --quiet
```

### List Resources

To see what test resources exist:

```bash
# VMs
gcloud compute instances list --filter="name~test-vm-"

# Disks
gcloud compute disks list --filter="name~test-vm-"

# Snapshots
gcloud compute snapshots list --filter="name~test-vm-"
```

## Estimated Costs

Running the integration test creates resources for approximately:
- **Duration:** ~10-15 minutes
- **Cost:** <$0.10 per test run

Resources created:
- 1 VM instance (e2-standard-2) - ~$0.02 for 15 minutes
- 1 200GB pd-standard disk - ~$0.01 for 15 minutes
- 1 200GB snapshot - ~$0.05 for 15 minutes (then deleted)

**Note:** Resources are deleted automatically, so you only pay for the test duration.

## Troubleshooting

### Test Skipped: "Integration tests disabled"

Enable integration tests:
```bash
export VMWS_INTEGRATION_TESTS=1
```

### Error: "VMWS_WORKSTATION_DISK not set"

Set the workstation disk name:
```bash
export VMWS_WORKSTATION_DISK=workstations-YOUR-DISK-ID
```

### Error: "No GCP project configured"

Configure gcloud:
```bash
gcloud config set project YOUR_PROJECT_ID
```

### SSH Timeout

The test waits up to 2 minutes for SSH. If it fails:
- Check VM is running: `gcloud compute instances describe test-vm-TIMESTAMP`
- Check firewall rules allow IAP: Port 22 from 35.235.240.0/20
- Try increasing retry count in the script

### Cleanup Failed

If automatic cleanup fails, clean up manually (see "Manual Cleanup" section above).

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on:
  workflow_dispatch:  # Manual trigger only
    inputs:
      workstation_disk:
        description: 'Workstation disk to snapshot'
        required: true

jobs:
  integration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run integration test
        env:
          VMWS_INTEGRATION_TESTS: "1"
          VMWS_WORKSTATION_DISK: ${{ github.event.inputs.workstation_disk }}
        run: |
          pytest tests/integration/test_vm_workstation_integration.py -v -s

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: integration-test-report
          path: /home/user/vm-integration-test-report-*.md
```

## Differences from Bash Version

The Python integration test improves on `scripts/run-vm-test-workflow.sh`:

| Feature | Bash Version | Python Version |
|---------|--------------|----------------|
| **Commands** | Raw gcloud commands | vmws CLI commands |
| **Error Handling** | Basic exit codes | Python exceptions + detailed logging |
| **Reporting** | Manual string building | Structured data + templating |
| **Testing** | Standalone script | pytest + standalone |
| **Type Safety** | None | Full type hints |
| **Resource Tracking** | Manual | Automatic tracking |
| **Cleanup** | Separate script | Integrated with error handling |
| **CI/CD** | Manual integration | pytest-ready |

## Development

To modify the integration test:

1. **Edit the script:** `tests/integration/test_vm_workstation_integration.py`
2. **Add new validation tests** in `step8_run_validation_tests()`
3. **Update report format** in `generate_report()`
4. **Test locally** before committing

## Support

If you encounter issues:
1. Check the generated report for error details
2. Review GCP Console for resource status
3. Check vmws logs: `vmws status`, `vmws logs`
4. File an issue: https://github.com/benthepsychologist/vmctl/issues
