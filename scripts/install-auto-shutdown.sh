#!/bin/bash
# Install auto-shutdown on the VM (run this script ON the VM)

set -e

echo "Installing auto-shutdown service..."

# Copy script to system location
sudo cp /tmp/vm-auto-shutdown.sh /usr/local/bin/vm-auto-shutdown.sh
sudo chmod +x /usr/local/bin/vm-auto-shutdown.sh

# Create systemd service
sudo tee /etc/systemd/system/vm-auto-shutdown.service > /dev/null <<'EOF'
[Unit]
Description=VM Auto-Shutdown Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/vm-auto-shutdown.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable vm-auto-shutdown.service
sudo systemctl start vm-auto-shutdown.service

echo "✅ Auto-shutdown service installed and started"
echo "   - Will shutdown after 2 hours of idle time"
echo "   - Tracks SSH and code-server connections"
echo ""
echo "To check status: sudo systemctl status vm-auto-shutdown"
echo "To view logs: sudo journalctl -u vm-auto-shutdown -f"
