#!/usr/bin/env bash
set -euo pipefail

# Default target directory 
TARGET_DIR="${1:-$HOME/.local/bin}"

# Repository details
REPO_URL="https://github.com/jvPalma/palma-commands.git"
SOURCE_PATH="python/prs"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔧 PRS - Pull Request Status CLI Installer${NC}"
echo "Installing to $TARGET_DIR..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Check if we have a writable target directory
if [ ! -w "$TARGET_DIR" ]; then
    echo -e "${RED}✗ Target directory $TARGET_DIR is not writable${NC}"
    echo "Please choose a writable directory or run with sudo"
    exit 1
fi

# Remove existing installation if present
if [ -f "$TARGET_DIR/prs" ]; then
    echo -e "${YELLOW}⚠ Removing existing PRS installation...${NC}"
    rm -f "$TARGET_DIR/prs"
fi

# Create temporary directory for download
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Clone only the PRS folder using sparse-checkout
echo "Downloading PRS CLI tool..."
if git clone --depth 1 --filter=blob:none --sparse \
  "$REPO_URL" "$TEMP_DIR/palma-commands" 2>/dev/null; then
    cd "$TEMP_DIR/palma-commands"
    git sparse-checkout set "$SOURCE_PATH"
    cd "$SOURCE_PATH"
    
    # Check if Python and pip are available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 is required but not installed${NC}"
        exit 1
    fi
    
    # Check if PyInstaller is available, install if needed
    if ! python3 -c "import PyInstaller" 2>/dev/null; then
        echo "Installing PyInstaller..."
        python3 -m pip install pyinstaller --user
    fi
    
    # Build the executable
    echo "Building PRS executable..."
    python3 -m PyInstaller --onefile --name prs prs/main.py --distpath "$TEMP_DIR"
    
    # Copy to target directory
    if [ -f "$TEMP_DIR/prs" ]; then
        cp "$TEMP_DIR/prs" "$TARGET_DIR/prs"
        chmod +x "$TARGET_DIR/prs"
        echo -e "${GREEN}✓ Installation complete!${NC}"
    else
        echo -e "${RED}✗ Failed to build executable${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Failed to download from repository${NC}"
    echo "Please check your internet connection and try again."
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}🚀 PRS is now installed!${NC}"
echo ""
echo -e "${YELLOW}  prs --help${NC}    # Show all available options"
echo -e "${YELLOW}  prs${NC}           # List your pull requests"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Quick Setup:${NC}"
echo ""
echo -e "  ${YELLOW}prs config set git.username YOUR_USERNAME${NC}"
echo -e "  ${YELLOW}prs config set git.repo_name YOUR_REPO${NC}"
echo -e "  ${YELLOW}prs config set git-org.org_name YOUR_ORG${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  • Config file: ${YELLOW}~/.prsconfig${NC}"
echo "  • Edit config: ${YELLOW}prs config open${NC}"
echo "  • View all settings: ${YELLOW}prs config all${NC}"
echo ""
echo -e "${CYAN}Features:${NC}"
echo "  • Rich panel display with color-coded PR status"
echo "  • Ignore PRs: ${YELLOW}prs ignore 1234 1235${NC}"
echo "  • Ignore users: ${YELLOW}prs ignore-users bot-user${NC}"
echo "  • Multiple verbosity levels for each component"
echo "  • Track PRs where you're author, reviewer, or both"
echo ""

# Check if target directory is in PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo -e "${YELLOW}⚠ Note: $TARGET_DIR is not in your PATH${NC}"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "${YELLOW}export PATH=\"$TARGET_DIR:\$PATH\"${NC}"
    echo ""
fi

echo -e "${GREEN}Happy PR monitoring! 🎉${NC}"
echo ""