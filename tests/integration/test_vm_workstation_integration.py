"""Integration test for VM Workstation creation and validation.

This test replicates the bash workflow from scripts/run-vm-test-workflow.sh
but uses vmws CLI commands instead of raw gcloud commands.

Usage:
    # Run as pytest (requires VMWS_INTEGRATION_TESTS=1)
    VMWS_INTEGRATION_TESTS=1 pytest tests/integration/test_vm_workstation_integration.py -v -s

    # Run as standalone script
    python tests/integration/test_vm_workstation_integration.py --workstation-disk disk-name

Environment Variables:
    VMWS_INTEGRATION_TESTS - Must be set to "1" to run integration tests
    VMWS_WORKSTATION_DISK - Workstation disk to snapshot (optional)
    VMWS_REGION - GCP region (default: northamerica-northeast1)
    VMWS_ZONE - GCP zone (default: northamerica-northeast1-b)
    VMWS_PROJECT - GCP project ID (uses gcloud default if not set)
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest


class VMWorkstationIntegrationTest:
    """Integration test for VM Workstation workflow."""

    def __init__(
        self,
        workstation_disk: str,
        zone: str = "northamerica-northeast1-b",
        region: str = "northamerica-northeast1",
        project: str | None = None,
    ) -> None:
        """Initialize integration test.

        Args:
            workstation_disk: Name of workstation disk to snapshot
            zone: GCP zone
            region: GCP region
            project: GCP project ID (uses gcloud default if None)
        """
        self.workstation_disk = workstation_disk
        self.zone = zone
        self.region = region
        self.project = project or self._get_gcloud_project()

        # Generate unique test VM name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.vm_name = f"test-vm-{timestamp}"
        self.snapshot_name = f"{self.vm_name}-snapshot"
        self.disk_name = f"{self.vm_name}-disk"

        # Report data
        self.report_data: dict[str, Any] = {
            "start_time": datetime.now(),
            "steps": [],
            "validation_results": [],
            "resources": [],
        }

        # Track created resources for cleanup
        self.created_resources = {
            "vm": False,
            "disk": False,
            "snapshot": False,
        }

    def _get_gcloud_project(self) -> str:
        """Get default gcloud project."""
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=False,
        )
        project = result.stdout.strip()
        if not project or project == "(unset)":
            raise ValueError("No GCP project configured. Set VMWS_PROJECT or run 'gcloud config set project PROJECT_ID'")
        return project

    def _run_command(self, cmd: list[str], description: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run command and log result."""
        print(f"\n🔵 {description}")
        print(f"   Command: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"   ✅ Success ({duration:.1f}s)")
        else:
            print(f"   ❌ Failed ({duration:.1f}s)")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")

        self.report_data["steps"].append({
            "description": description,
            "success": result.returncode == 0,
            "duration": duration,
            "command": " ".join(cmd),
        })

        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed: {description}\n{result.stderr}")

        return result

    def step1_create_snapshot(self) -> None:
        """Step 1: Create snapshot from workstation disk."""
        print("\n" + "="*80)
        print("STEP 1: Create Snapshot from Workstation Disk")
        print("="*80)

        self._run_command(
            [
                "gcloud", "compute", "disks", "snapshot",
                self.workstation_disk,
                f"--snapshot-names={self.snapshot_name}",
                f"--region={self.region}",
                f"--project={self.project}",
                f"--storage-location={self.region}",
            ],
            f"Creating snapshot {self.snapshot_name}",
        )

        self.created_resources["snapshot"] = True
        self.report_data["resources"].append({
            "type": "Snapshot",
            "name": self.snapshot_name,
            "location": self.region,
        })

    def step2_create_disk(self) -> None:
        """Step 2: Create disk from snapshot."""
        print("\n" + "="*80)
        print("STEP 2: Create Disk from Snapshot")
        print("="*80)

        self._run_command(
            [
                "gcloud", "compute", "disks", "create",
                self.disk_name,
                f"--source-snapshot={self.snapshot_name}",
                f"--size=200GB",
                f"--type=pd-standard",
                f"--zone={self.zone}",
                f"--project={self.project}",
            ],
            f"Creating disk {self.disk_name}",
        )

        self.created_resources["disk"] = True
        self.report_data["resources"].append({
            "type": "Disk",
            "name": self.disk_name,
            "size": "200GB",
            "zone": self.zone,
        })

    def step3_create_vm(self) -> None:
        """Step 3: Create VM instance."""
        print("\n" + "="*80)
        print("STEP 3: Create VM Instance")
        print("="*80)

        # Get startup script path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        startup_script = scripts_dir / "vm-startup-script.sh"

        if not startup_script.exists():
            print(f"   ⚠️  Warning: Startup script not found at {startup_script}")
            startup_script_args = []
        else:
            startup_script_args = [f"--metadata-from-file=startup-script={startup_script}"]

        self._run_command(
            [
                "gcloud", "compute", "instances", "create",
                self.vm_name,
                f"--machine-type=e2-standard-2",
                f"--zone={self.zone}",
                f"--project={self.project}",
                "--image-family=debian-12",
                "--image-project=debian-cloud",
                "--boot-disk-size=50GB",
                "--boot-disk-type=pd-standard",
                f"--disk=name={self.disk_name},mode=rw",
                "--scopes=cloud-platform",
                "--metadata=enable-oslogin=TRUE",
            ] + startup_script_args,
            f"Creating VM {self.vm_name}",
        )

        self.created_resources["vm"] = True

        # Configure vmws to use this VM
        self._run_command(
            ["vmws", "config", f"--vm-name={self.vm_name}", f"--zone={self.zone}", f"--project={self.project}"],
            "Configuring vmws",
        )

        self.report_data["resources"].append({
            "type": "VM Instance",
            "name": self.vm_name,
            "machine_type": "e2-standard-2",
            "zone": self.zone,
        })

    def step4_wait_for_ssh(self, max_retries: int = 12, retry_delay: int = 10) -> None:
        """Step 4: Wait for SSH to be ready."""
        print("\n" + "="*80)
        print("STEP 4: Wait for SSH Connectivity")
        print("="*80)

        for attempt in range(1, max_retries + 1):
            print(f"\n   Attempt {attempt}/{max_retries}...")
            result = self._run_command(
                ["vmws", "ssh", "echo 'SSH ready'"],
                f"Testing SSH connectivity (attempt {attempt})",
                check=False,
            )

            if result.returncode == 0:
                print(f"   ✅ SSH is ready!")
                return

            if attempt < max_retries:
                print(f"   Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)

        raise RuntimeError("SSH failed to become ready after all retries")

    def step5_fix_permissions(self, username: str = "ben_getmensio_com") -> None:
        """Step 5: Fix file permissions on mounted disk."""
        print("\n" + "="*80)
        print("STEP 5: Fix File Permissions")
        print("="*80)

        self._run_command(
            ["vmws", "ssh", f"sudo chown -R {username}:{username} /mnt/home/user"],
            "Fixing ownership of /mnt/home/user",
        )

    def step6_install_dev_environment(self) -> None:
        """Step 6: Install development environment."""
        print("\n" + "="*80)
        print("STEP 6: Install Development Environment")
        print("="*80)

        # Copy and run setup script
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        setup_script = scripts_dir / "setup-vm-environment.sh"

        if not setup_script.exists():
            print(f"   ⚠️  Warning: Setup script not found at {setup_script}")
            return

        # Copy script to VM
        self._run_command(
            [
                "gcloud", "compute", "scp",
                str(setup_script),
                f"{self.vm_name}:/tmp/setup-vm-environment.sh",
                f"--zone={self.zone}",
                f"--project={self.project}",
                "--tunnel-through-iap",
            ],
            "Copying setup script to VM",
        )

        # Run setup script
        self._run_command(
            ["vmws", "ssh", "bash /tmp/setup-vm-environment.sh"],
            "Installing Docker, code-server, and neovim",
        )

    def step7_install_auto_shutdown(self) -> None:
        """Step 7: Install auto-shutdown service."""
        print("\n" + "="*80)
        print("STEP 7: Install Auto-Shutdown Service")
        print("="*80)

        scripts_dir = Path(__file__).parent.parent.parent / "scripts"

        # Copy auto-shutdown scripts
        for script_file in ["vm-auto-shutdown.sh", "install-auto-shutdown.sh"]:
            script_path = scripts_dir / script_file
            if script_path.exists():
                self._run_command(
                    [
                        "gcloud", "compute", "scp",
                        str(script_path),
                        f"{self.vm_name}:/tmp/{script_file}",
                        f"--zone={self.zone}",
                        f"--project={self.project}",
                        "--tunnel-through-iap",
                    ],
                    f"Copying {script_file} to VM",
                )

        # Run install script
        self._run_command(
            ["vmws", "ssh", "bash /tmp/install-auto-shutdown.sh"],
            "Installing auto-shutdown service",
        )

    def step8_run_validation_tests(self) -> None:
        """Step 8: Run validation tests."""
        print("\n" + "="*80)
        print("STEP 8: Run Validation Tests")
        print("="*80)

        tests = [
            ("Disk mounted", "mountpoint -q /mnt/home && echo 'PASS' || echo 'FAIL'"),
            ("Files accessible", "ls -1 /mnt/home/user/ | wc -l"),
            ("life-cockpit directory", "test -d /mnt/home/user/life-cockpit && echo 'PASS' || echo 'FAIL'"),
            ("File read access", "cat /mnt/home/user/README.md > /dev/null 2>&1 && echo 'PASS' || echo 'FAIL'"),
            ("Docker running", "docker ps > /dev/null 2>&1 && echo 'PASS' || echo 'FAIL'"),
            ("code-server running", "systemctl is-active code-server && echo 'PASS' || echo 'FAIL'"),
        ]

        for test_name, test_command in tests:
            result = self._run_command(
                ["vmws", "ssh", test_command],
                f"Testing: {test_name}",
                check=False,
            )

            output = result.stdout.strip()
            passed = "PASS" in output or (test_name == "Files accessible" and output.isdigit() and int(output) > 0)

            self.report_data["validation_results"].append({
                "test": test_name,
                "passed": passed,
                "details": output,
            })

            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test_name}: {status} - {output}")

    def generate_report(self, output_path: Path) -> None:
        """Generate Markdown report."""
        print("\n" + "="*80)
        print("Generating Report")
        print("="*80)

        end_time = datetime.now()
        duration = (end_time - self.report_data["start_time"]).total_seconds()

        # Calculate costs
        vm_cost_monthly = 26.28  # e2-standard-2 24/7
        disk_cost_monthly = 8.00  # 200GB pd-standard
        total_monthly = vm_cost_monthly + disk_cost_monthly

        workstation_cost = 150.00  # Approximate Cloud Workstation cost
        savings_percent = ((workstation_cost - total_monthly) / workstation_cost) * 100

        report = f"""# VM Workstation Integration Test Report

**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration:.1f}s ({duration/60:.1f} minutes)
**VM Name:** `{self.vm_name}`
**Zone:** `{self.zone}`
**Project:** `{self.project}`

## Executive Summary

✅ **Test Status:** {'PASSED' if all(v['passed'] for v in self.report_data['validation_results']) else 'FAILED'}
📊 **Validation Tests:** {sum(1 for v in self.report_data['validation_results'] if v['passed'])}/{len(self.report_data['validation_results'])} passed
💰 **Monthly Cost:** ${total_monthly:.2f} (vs ${workstation_cost:.2f} Cloud Workstation)
💵 **Savings:** {savings_percent:.0f}%

---

## Resources Created

| Resource Type | Name | Location | Details |
|--------------|------|----------|---------|
"""
        for resource in self.report_data["resources"]:
            details = resource.get("size", "") or resource.get("machine_type", "")
            report += f"| {resource['type']} | `{resource['name']}` | {resource.get('zone') or resource.get('location', '')} | {details} |\n"

        report += """
---

## Workflow Steps

| Step | Description | Status | Duration |
|------|-------------|--------|----------|
"""
        for i, step in enumerate(self.report_data["steps"], 1):
            status = "✅" if step["success"] else "❌"
            report += f"| {i} | {step['description']} | {status} | {step['duration']:.1f}s |\n"

        report += """
---

## Validation Tests

| Test | Status | Details |
|------|--------|---------|
"""
        for test in self.report_data["validation_results"]:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            report += f"| {test['test']} | {status} | `{test['details']}` |\n"

        report += f"""
---

## Cost Analysis

### Monthly Cost Breakdown (24/7 usage)

- **VM (e2-standard-2):** ${vm_cost_monthly:.2f}/month
- **Data disk (200GB pd-standard):** ${disk_cost_monthly:.2f}/month
- **Boot disk (50GB pd-standard):** $2.00/month
- **Total:** ${total_monthly + 2:.2f}/month

### Comparison: Cloud Workstation vs Self-Managed VM

| Scenario | Cloud Workstation | Self-Managed VM | Savings |
|----------|-------------------|-----------------|---------|
| 24/7 Usage | ${workstation_cost:.2f}/month | ${total_monthly + 2:.2f}/month | ${workstation_cost - (total_monthly + 2):.2f}/month ({savings_percent:.0f}%) |
| 8hr/day (auto-shutdown) | ${workstation_cost:.2f}/month | ${(total_monthly + 2) / 3:.2f}/month | ${workstation_cost - (total_monthly + 2) / 3:.2f}/month ({((workstation_cost - (total_monthly + 2) / 3) / workstation_cost) * 100:.0f}%) |

---

## Access Instructions

### SSH Access
```bash
vmws ssh
```

### code-server Access
```bash
# Option 1: Using vmws
vmws tunnel

# Option 2: Direct gcloud
gcloud compute start-iap-tunnel {self.vm_name} 8080 --local-host-port=localhost:8080 --zone={self.zone}
```

Then open: http://localhost:8080

### File Access
- User files: `/mnt/home/user/`
- Projects: `/mnt/home/user/life-cockpit/`

---

## Cleanup Instructions

### Using vmws
```bash
vmws delete --yes
gcloud compute snapshots delete {self.snapshot_name} --quiet
```

### Manual cleanup
```bash
gcloud compute instances delete {self.vm_name} --zone={self.zone} --quiet
gcloud compute disks delete {self.disk_name} --zone={self.zone} --quiet
gcloud compute snapshots delete {self.snapshot_name} --quiet
```

---

## Summary

- **Total execution time:** {duration:.1f}s ({duration/60:.1f} minutes)
- **Report generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **All resources created in:** {self.zone}

🤖 Generated by vmws integration test
"""

        output_path.write_text(report)
        print(f"   📄 Report saved to: {output_path}")

    def cleanup(self) -> None:
        """Clean up all created resources."""
        print("\n" + "="*80)
        print("CLEANUP: Deleting Resources")
        print("="*80)

        # Delete VM
        if self.created_resources["vm"]:
            self._run_command(
                ["vmws", "delete", "--yes"],
                f"Deleting VM {self.vm_name}",
                check=False,
            )

        # Delete disk
        if self.created_resources["disk"]:
            self._run_command(
                [
                    "gcloud", "compute", "disks", "delete",
                    self.disk_name,
                    f"--zone={self.zone}",
                    f"--project={self.project}",
                    "--quiet",
                ],
                f"Deleting disk {self.disk_name}",
                check=False,
            )

        # Delete snapshot
        if self.created_resources["snapshot"]:
            self._run_command(
                [
                    "gcloud", "compute", "snapshots", "delete",
                    self.snapshot_name,
                    f"--project={self.project}",
                    "--quiet",
                ],
                f"Deleting snapshot {self.snapshot_name}",
                check=False,
            )

    def run(self, cleanup_on_completion: bool = True) -> Path:
        """Run the complete integration test workflow.

        Args:
            cleanup_on_completion: Whether to cleanup resources after test

        Returns:
            Path to generated report
        """
        report_path = Path(f"/home/user/vm-integration-test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md")

        try:
            self.step1_create_snapshot()
            self.step2_create_disk()
            self.step3_create_vm()
            self.step4_wait_for_ssh()
            self.step5_fix_permissions()
            self.step6_install_dev_environment()
            self.step7_install_auto_shutdown()
            self.step8_run_validation_tests()

            self.generate_report(report_path)

            print("\n" + "="*80)
            print("✅ Integration Test Complete!")
            print("="*80)
            print(f"📄 Report: {report_path}")

            if cleanup_on_completion:
                self.cleanup()
            else:
                print("\n⚠️  Resources NOT cleaned up (--no-cleanup flag used)")
                print(f"   Run cleanup manually: vmws delete --yes && gcloud compute snapshots delete {self.snapshot_name}")

            return report_path

        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            self.generate_report(report_path)

            # Cleanup on failure
            try:
                self.cleanup()
            except Exception as cleanup_error:
                print(f"⚠️  Cleanup failed: {cleanup_error}")

            raise


@pytest.mark.integration
def test_vm_workstation_integration() -> None:
    """Integration test for VM workstation creation and validation."""
    # Get configuration from environment
    workstation_disk = os.getenv("VMWS_WORKSTATION_DISK")
    if not workstation_disk:
        pytest.skip("VMWS_WORKSTATION_DISK not set")

    zone = os.getenv("VMWS_ZONE", "northamerica-northeast1-b")
    region = os.getenv("VMWS_REGION", "northamerica-northeast1")
    project = os.getenv("VMWS_PROJECT")

    # Run integration test
    test = VMWorkstationIntegrationTest(
        workstation_disk=workstation_disk,
        zone=zone,
        region=region,
        project=project,
    )

    report_path = test.run(cleanup_on_completion=True)

    # Verify report was created
    assert report_path.exists(), "Report was not generated"

    # Verify all validation tests passed
    all_passed = all(v["passed"] for v in test.report_data["validation_results"])
    assert all_passed, "Some validation tests failed"


def main() -> int:
    """Run as standalone script."""
    parser = argparse.ArgumentParser(description="VM Workstation Integration Test")
    parser.add_argument("--workstation-disk", required=True, help="Workstation disk to snapshot")
    parser.add_argument("--zone", default="northamerica-northeast1-b", help="GCP zone")
    parser.add_argument("--region", default="northamerica-northeast1", help="GCP region")
    parser.add_argument("--project", help="GCP project ID (uses gcloud default if not set)")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup resources after test")

    args = parser.parse_args()

    test = VMWorkstationIntegrationTest(
        workstation_disk=args.workstation_disk,
        zone=args.zone,
        region=args.region,
        project=args.project,
    )

    try:
        test.run(cleanup_on_completion=not args.no_cleanup)
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
