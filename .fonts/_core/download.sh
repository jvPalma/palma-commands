#!/usr/bin/env bash
set -euo pipefail

# Default target directory 
TARGET_DIR="${1:-$HOME/.fonts}"

# Repository details
REPO_URL="https://github.com/jvPalma/palma-commands.git"
SOURCE_PATH=".fonts"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🎨 VS Code Font Installer${NC}"
echo "Installing to $TARGET_DIR..."

# Create parent directory if it doesn't exist
mkdir -p "$(dirname "$TARGET_DIR")"

# Remove existing installation if present
if [ -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}⚠${NC} Removing existing installation..."
    rm -rf "$TARGET_DIR"
fi

# Clone only this folder using sparse-checkout
echo "Downloading font installer..."
if git clone --depth 1 --filter=blob:none --sparse \
  "$REPO_URL" temp-font-installer 2>/dev/null; then
  cd temp-font-installer && \
  git sparse-checkout set "$SOURCE_PATH" && \
  cd .. && \
  mv temp-font-installer/"$SOURCE_PATH" "$TARGET_DIR" && \
  rm -rf temp-font-installer
  echo -e "${GREEN}✓ Installation complete!${NC}"
else
  echo -e "${RED}✗ Failed to download from repository${NC}"
  echo "Please check your internet connection and try again."
  exit 1
fi
echo ""
echo -e "${CYAN}To get started:${NC}"
echo "  cd \"$TARGET_DIR\""
echo "  ./install.sh"
echo ""
echo -e "${CYAN}Features:${NC}"
echo "  • Interactive font selection menu"
echo "  • Import custom fonts: ./_core/import-font.sh <FontName>"
echo "  • Install to both web and local VS Code"
echo "  • Multi-font variant selection"
echo ""
