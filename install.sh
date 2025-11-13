#!/bin/bash
# Install VM Workstation Manager

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "VM Workstation Manager Installer"
echo "=========================================="
echo ""

# Determine install location
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
else
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

# Install CLI
echo "Installing vmws to $INSTALL_DIR..."
cp bin/vmws "$INSTALL_DIR/vmws"
chmod +x "$INSTALL_DIR/vmws"

echo -e "${GREEN}✓ Installed vmws CLI${NC}"
echo ""

# Check PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}Note: Add $INSTALL_DIR to your PATH${NC}"
    echo ""
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
    echo ""
fi

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}Warning: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    echo ""
fi

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Get started:"
echo "  1. vmws config              # Configure VM name/zone"
echo "  2. vmws create              # Create VM (from workstation)"
echo "  3. vmws start               # Start VM"
echo "  4. vmws tunnel              # Connect to code-server"
echo ""
echo "For help: vmws --help"
echo ""
