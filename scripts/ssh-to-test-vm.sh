#!/bin/bash
# Quick SSH into the test VM via IAP

VM_NAME="test-vm-from-workstation"
ZONE="northamerica-northeast1-b"

gcloud compute ssh $VM_NAME --zone=$ZONE --tunnel-through-iap
