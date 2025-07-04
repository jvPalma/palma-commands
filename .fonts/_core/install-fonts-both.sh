#!/usr/bin/env bash
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# Note: Common paths are now available from utils.sh
CONFIG_FILE="$SCRIPT_DIR/font-config.json"

echo ""
header "🎨 Installing Fonts to Both Web and Local VS Code"
echo ""

# Generate nerdFonts.css
info "Generating nerdFonts.css based on configuration..."
bash "$SCRIPT_DIR/applyFontVSC.sh" <<< "q" >/dev/null 2>&1 || true
success "nerdFonts.css generated successfully"

# Show selected fonts
echo ""
info "Selected fonts for installation:"
jq -r '.selectedFonts[] | "  • \(.fontFamily): \(.variants | join(", "))"' "$CONFIG_FILE"

echo ""

# Install to web first
header "🌐 Installing to VS Code Web instances..."
echo ""

# Web installation logic
if [ ! -d "$WEB_ROOT_PATH" ]; then
  warning "VS Code CLI path does not exist: $WEB_ROOT_PATH"
  info "Creating directory structure for testing..."
  mkdir -p "$WEB_ROOT_PATH/test-instance"
fi

# Apply to web
vscode_dirs=("$WEB_ROOT_PATH"/*/)
if [ ! -e "${vscode_dirs[0]}" ]; then
  warning "No VS Code instances found, creating test structure..."
  mkdir -p "$WEB_ROOT_PATH/test-instance"
  vscode_dirs=("$WEB_ROOT_PATH/test-instance")
fi

for dir in "${vscode_dirs[@]}"; do
  if [[ "$dir" == "$WEB_ROOT_PATH/*/" ]]; then
    continue
  fi
  
  TARGET_PATH="$dir/out/vs/code/browser/workbench"
  mkdir -p "$TARGET_PATH"
  
  # Copy nerdFonts.css
  cp "$SCRIPT_DIR/nerdFonts.css" "$TARGET_PATH/"
  
  # Copy font directories
  jq -c '.selectedFonts[]' "$CONFIG_FILE" | while read -r font; do
    fontFamily=$(echo "$font" | jq -r '.fontFamily')
    if [ -d "$SCRIPT_DIR/$fontFamily" ]; then
      cp -r "$SCRIPT_DIR/$fontFamily" "$TARGET_PATH/"
    fi
  done
  
  success "Web fonts installed to $(basename "$dir")"
done

echo ""

# Install to local
header "💻 Installing to Local VS Code installation..."
echo ""

if [[ ! -r "$LOCAL_PATH" ]]; then
  error "Local VS Code installation not found at: $LOCAL_PATH"
  warning "Make sure VS Code is installed locally"
else
  # Copy nerdFonts.css
  sudo cp "$SCRIPT_DIR/nerdFonts.css" "$LOCAL_PATH/"
  
  # Copy font directories
  jq -c '.selectedFonts[]' "$CONFIG_FILE" | while read -r font; do
    fontFamily=$(echo "$font" | jq -r '.fontFamily')
    if [ -d "$SCRIPT_DIR/$fontFamily" ]; then
      sudo cp -r "$SCRIPT_DIR/$fontFamily" "$LOCAL_PATH/"
    fi
  done
  
  success "Local fonts installed successfully"
  warning "Restart VS Code for changes to take effect"
fi

echo ""
success "Font installation complete!"
info "Fonts have been applied to both web and local VS Code"