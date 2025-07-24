#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get the directory of this script
DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$DIR/dist/prs"

echo -e "${BLUE}🔧 PRS Local Installation Script${NC}"
echo ""

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo -e "${RED}✗ Binary not found at $BINARY${NC}"
    echo "Please build the project first:"
    echo -e "${YELLOW}  pyinstaller --onefile --name prs prs/main.py${NC}"
    exit 1
fi

# Define candidate directories (in order of preference)
candidates=(
    "$HOME/.local/bin"
    "$HOME/bin"
    "/usr/local/bin"
    "/usr/bin"
    "/opt/bin"
)

destination=""
needs_sudo=false

echo "Searching for installation directory..."

# Iterate over candidate directories
for d in "${candidates[@]}"; do
    if [ -d "$d" ]; then
        if [ -w "$d" ]; then
            destination="$d/prs"
            echo -e "${GREEN}✓ Found writable directory: $d${NC}"
            break
        else
            # Directory exists but not writable, might need sudo
            destination="$d/prs"
            needs_sudo=true
            echo -e "${YELLOW}⚠ Found directory (requires sudo): $d${NC}"
            break
        fi
    else
        # Try to create the directory
        if mkdir -p "$d" 2>/dev/null; then
            destination="$d/prs"
            echo -e "${GREEN}✓ Created directory: $d${NC}"
            break
        elif [ "$d" = "$HOME/.local/bin" ] || [ "$d" = "$HOME/bin" ]; then
            # For user directories, try again with explicit creation
            mkdir -p "$d" 2>/dev/null || true
            if [ -d "$d" ] && [ -w "$d" ]; then
                destination="$d/prs"
                echo -e "${GREEN}✓ Created directory: $d${NC}"
                break
            fi
        else
            # For system directories, try with sudo
            if sudo mkdir -p "$d" 2>/dev/null; then
                destination="$d/prs"
                needs_sudo=true
                echo -e "${YELLOW}⚠ Created directory (with sudo): $d${NC}"
                break
            fi
        fi
    fi
done

if [ -z "$destination" ]; then
    echo -e "${RED}✗ No suitable destination directory found${NC}"
    echo "Please create one of these directories and add it to your PATH:"
    for d in "${candidates[@]}"; do
        echo "  - $d"
    done
    exit 1
fi

echo ""
echo "Installing PRS to: $destination"

# Copy the binary
if [ "$needs_sudo" = true ]; then
    echo -e "${YELLOW}⚠ Sudo required for installation...${NC}"
    sudo cp -f "$BINARY" "$destination"
    sudo chmod +x "$destination"
else
    cp -f "$BINARY" "$destination"
    chmod +x "$destination"
fi

echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""

# Check if destination directory is in PATH
install_dir=$(dirname "$destination")
if [[ ":$PATH:" != *":$install_dir:"* ]]; then
    echo -e "${YELLOW}⚠ Warning: $install_dir is not in your PATH${NC}"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "${CYAN}export PATH=\"$install_dir:\$PATH\"${NC}"
    echo ""
fi

# Test the installation
echo "Testing installation..."
if command -v prs &> /dev/null; then
    echo -e "${GREEN}✓ PRS is now available globally${NC}"
    echo ""
    echo -e "${CYAN}🚀 Quick start:${NC}"
    echo -e "  ${YELLOW}prs --help${NC}           # Show help"
    echo -e "  ${YELLOW}prs${NC}                  # List your PRs"
    echo -e "  ${YELLOW}prs config set git.username YOUR_USERNAME${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ PRS installed but not in PATH${NC}"
    echo "You can run it directly: $destination"
fi

echo -e "${GREEN}Happy PR monitoring! 🎉${NC}"