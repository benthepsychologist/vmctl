#!/bin/bash
set -e

VM_NAME="test-vm-from-workstation"
ZONE="northamerica-northeast1-b"

echo "🗑️  Cleaning up test VM resources..."
echo ""

# Get the latest snapshot for this VM
LATEST_SNAPSHOT=$(gcloud compute snapshots list --filter="name~workstation-snapshot" --sort-by=~creationTimestamp --limit=1 --format="value(name)")

echo "Deleting VM: $VM_NAME"
gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet 2>/dev/null || echo "VM already deleted or doesn't exist"

echo "Deleting disk: ${VM_NAME}-disk"
gcloud compute disks delete ${VM_NAME}-disk --zone=$ZONE --quiet 2>/dev/null || echo "Disk already deleted or doesn't exist"

if [ -n "$LATEST_SNAPSHOT" ]; then
    echo "Deleting snapshot: $LATEST_SNAPSHOT"
    gcloud compute snapshots delete $LATEST_SNAPSHOT --quiet 2>/dev/null || echo "Snapshot already deleted or doesn't exist"
fi

echo ""
echo "✅ Cleanup complete!"
