#!/bin/bash
# Mount the data disk at /mnt/home
mkdir -p /mnt/home

# The data disk is /dev/sda (200GB disk)
if [ -b /dev/sda ]; then
  mount /dev/sda /mnt/home
  # Add to fstab if not already there
  if ! grep -q "/mnt/home" /etc/fstab; then
    echo "/dev/sda /mnt/home ext4 defaults 0 2" >> /etc/fstab
  fi
fi
