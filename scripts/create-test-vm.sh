#!/bin/bash
set -e

# Configuration
WORKSTATION_DISK="workstations-4f92986b-87d6-4868-ab63-5040fec833bb"
REGION="northamerica-northeast1"
ZONE="northamerica-northeast1-b"
VM_NAME="test-vm-from-workstation"
DISK_SIZE="200GB"
MACHINE_TYPE="e2-standard-2"

echo "🔄 Creating snapshot from workstation disk..."
SNAPSHOT_NAME="workstation-snapshot-$(date +%Y%m%d-%H%M%S)"

gcloud compute disks snapshot $WORKSTATION_DISK \
  --snapshot-names=$SNAPSHOT_NAME \
  --region=$REGION \
  --storage-location=$REGION

echo "✅ Snapshot created: $SNAPSHOT_NAME"
echo ""
echo "💾 Creating new ${DISK_SIZE} disk from snapshot..."

gcloud compute disks create ${VM_NAME}-disk \
  --source-snapshot=$SNAPSHOT_NAME \
  --size=$DISK_SIZE \
  --type=pd-standard \
  --zone=$ZONE

echo "✅ Disk created: ${VM_NAME}-disk"
echo ""
echo "🖥️  Creating VM instance with data disk..."

gcloud compute instances create $VM_NAME \
  --machine-type=$MACHINE_TYPE \
  --zone=$ZONE \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-standard \
  --disk=name=${VM_NAME}-disk,mode=rw \
  --scopes=cloud-platform \
  --metadata=enable-oslogin=TRUE \
  --metadata-from-file=startup-script=/home/user/vm-startup-script.sh

echo "✅ VM created: $VM_NAME"
echo ""
echo "📡 Waiting for VM to be ready..."
sleep 10

echo ""
echo "✅ All done!"
echo ""
echo "Your workstation files are mounted at: /mnt/home/user/"
echo ""
echo "To SSH into your VM, run:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --tunnel-through-iap"
echo ""
echo "Or use the helper script:"
echo "  bash /home/user/ssh-to-test-vm.sh"
echo ""
echo "To delete the VM when done:"
echo "  bash /home/user/cleanup-test-vm.sh"
