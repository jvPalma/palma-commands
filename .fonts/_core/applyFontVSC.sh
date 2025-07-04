#!/usr/bin/env bash
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# Note: Common paths are now available from utils.sh
CONFIG_FILE="$SCRIPT_DIR/font-config.json"

# Function to generate nerdFonts.css based on configuration
generate_nerd_fonts_css() {
  local output_file="$1"
  local selected_fonts=$(jq -r '.selectedFonts' "$CONFIG_FILE" 2>/dev/null || echo '[]')
  
  if [ "$selected_fonts" = "[]" ]; then
    echo "Error: No fonts selected in font-config.json" >&2
    return 1
  fi
  
  # Start creating the CSS file
  echo "/* Generated nerdFonts.css based on font-config.json */" > "$output_file"
  echo "" >> "$output_file"
  
  # Iterate through selected fonts
  jq -c '.selectedFonts[]' "$CONFIG_FILE" | while read -r font; do
    local fontFamily=$(echo "$font" | jq -r '.fontFamily')
    local variants=$(echo "$font" | jq -r '.variants[]')
    
    # Add comment for the font family
    local displayName=$(jq -r ".availableFonts.\"$fontFamily\".displayName // \"$fontFamily\"" "$CONFIG_FILE")
    echo "/* $displayName */" >> "$output_file"
    
    # Add imports for each variant
    echo "$variants" | while read -r variant; do
      if [ -n "$variant" ]; then
        local description=$(jq -r ".availableFonts.\"$fontFamily\".variants.\"$variant\" // \"\"" "$CONFIG_FILE")
        if [ -n "$description" ]; then
          echo "/* - $description */" >> "$output_file"
        fi
        echo "@import url(\"./$fontFamily/$variant\");" >> "$output_file"
      fi
    done
    
    echo "" >> "$output_file"
  done
}

# Function to copy only required font files
copy_required_fonts() {
  local target_dir="$1"
  local use_sudo="${2:-false}"
  
  # Read selected fonts from config
  jq -c '.selectedFonts[]' "$CONFIG_FILE" | while read -r font; do
    local fontFamily=$(echo "$font" | jq -r '.fontFamily')
    local variants=$(echo "$font" | jq -r '.variants[]')
    
    # Create font family directory in target
    if [ "$use_sudo" = true ]; then
      sudo mkdir -p "$target_dir/$fontFamily"
    else
      mkdir -p "$target_dir/$fontFamily"
    fi
    
    # Copy CSS variants
    echo "$variants" | while read -r variant; do
      if [ -f "$SCRIPT_DIR/$fontFamily/$variant" ]; then
        if [ "$use_sudo" = true ]; then
          sudo cp "$SCRIPT_DIR/$fontFamily/$variant" "$target_dir/$fontFamily/"
        else
          cp "$SCRIPT_DIR/$fontFamily/$variant" "$target_dir/$fontFamily/"
        fi
      fi
    done
    
    # Determine which TTF files to copy based on variants
    echo "$variants" | while read -r variant; do
      case "$variant" in
        "_font.css")
          # Copy standard font files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*.ttf" ! -name "*NL*" ! -name "*Mono*" ! -name "*Propo*" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*.ttf" ! -name "*NL*" ! -name "*Mono*" ! -name "*Propo*" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
        "_fontMono.css")
          # Copy Mono variant files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*Mono*.ttf" ! -name "*NL*" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*Mono*.ttf" ! -name "*NL*" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
        "_fontPropo.css")
          # Copy Propo variant files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*Propo*.ttf" ! -name "*NL*" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*Propo*.ttf" ! -name "*NL*" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
        "_nlFont.css")
          # Copy NL variant files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*NL*.ttf" ! -name "*Mono*" ! -name "*Propo*" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*NL*.ttf" ! -name "*Mono*" ! -name "*Propo*" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
        "_nlFontMono.css")
          # Copy NL Mono variant files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*NLNerdFontMono*.ttf" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*NLNerdFontMono*.ttf" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
        "_nlFontPropo.css")
          # Copy NL Propo variant files
          if [ "$use_sudo" = true ]; then
            find "$SCRIPT_DIR/$fontFamily" -name "*NLNerdFontPropo*.ttf" -exec sudo cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          else
            find "$SCRIPT_DIR/$fontFamily" -name "*NLNerdFontPropo*.ttf" -exec cp {} "$target_dir/$fontFamily/" \; 2>/dev/null || true
          fi
          ;;
      esac
    done
  done
}

# Function to apply fonts to web VS Code instances
apply_to_web_vscode() {
  header "🌐 Applying fonts to VS Code Web instances..."
  
  # Check if WEB_ROOT_PATH exists
  if [ ! -d "$WEB_ROOT_PATH" ]; then
    error "VS Code CLI path does not exist: $WEB_ROOT_PATH"
    info "Please ensure VS Code CLI server is installed and running"
    return 1
  fi

  # Apply fonts to all VS Code instances
  vscode_dirs=("$WEB_ROOT_PATH"/*/)
  if [ ! -e "${vscode_dirs[0]}" ]; then
    error "No VS Code instances found in $WEB_ROOT_PATH"
    info "Please start VS Code CLI server first"
    return 1
  fi

  for dir in "${vscode_dirs[@]}"; do
    # Skip if it's the literal glob pattern (no directories found)
    if [[ "$dir" == "$WEB_ROOT_PATH/*/" ]]; then
      continue
    fi
    
    TARGET_PATH="$dir/out/vs/code/browser/workbench"
    FONT_CSS="$TARGET_PATH/nerdFonts.css"
    WORKBENCH_CSS="$TARGET_PATH/workbench.css"

    info "Processing VS Code instance: $(highlight $(basename "$dir"))"

    if [ -f "$WORKBENCH_CSS" ]; then
      # Add @import "nerdFonts.css"; to the first line if not present
      grep -qx '@import "nerdFonts.css";' "$WORKBENCH_CSS" ||
        sed -i '1i@import "nerdFonts.css";' "$WORKBENCH_CSS"
      success "Updated workbench.css"
    fi

    mkdir -p "$TARGET_PATH"
    
    # Copy nerdFonts.css
    cp "$SCRIPT_DIR/nerdFonts.css" "$TARGET_PATH/"
    success "Copied nerdFonts.css"
    
    # Copy only required fonts based on configuration
    info "Copying selected fonts to $TARGET_PATH..."
    copy_required_fonts "$TARGET_PATH" false
    success "Fonts copied successfully"
  done
}

# Function to apply fonts to local VS Code installation
apply_to_local_vscode() {
  header "💻 Applying fonts to local VS Code installation..."
  
  if [[ ! -r "$DESKTOP_LOCATION" ]]; then
    error "Local VS Code installation not found at: $DESKTOP_LOCATION"
    warning "Make sure VS Code is installed locally"
    return 1
  fi
  
  WORKBENCH_CSS="$DESKTOP_LOCATION/workbench.desktop.main.css"
  
  info "Processing local VS Code installation at: $(highlight "$DESKTOP_LOCATION")"
  
  if [ -f "$WORKBENCH_CSS" ]; then
    # Add @import "nerdFonts.css"; to the first line if not present
    grep -qx '@import "nerdFonts.css";' "$WORKBENCH_CSS" ||
      sudo sed -i '1i@import "nerdFonts.css";' "$WORKBENCH_CSS"
    success "Updated workbench.desktop.main.css"
  fi

  # Copy nerdFonts.css
  sudo cp "$SCRIPT_DIR/nerdFonts.css" "$DESKTOP_LOCATION/"
  success "Copied nerdFonts.css"
  
  # Copy only required fonts based on configuration
  info "Copying selected fonts to $DESKTOP_LOCATION..."
  copy_required_fonts "$DESKTOP_LOCATION" true
  success "Fonts copied successfully"
  
  warning "You may need to restart VS Code for changes to take effect"
}

# Function to prompt user for installation type
prompt_installation_type() {
  echo ""
  header "📦 Font Installation Options"
  echo ""
  echo "Choose where to install the fonts:"
  echo ""
  echo "  $(highlight "1)") Web VS Code (CLI server)"
  echo "  $(highlight "2)") Local VS Code installation"
  echo "  $(highlight "3)") Both web and local"
  echo "  $(highlight "q)") Quit without installing"
  echo ""
  
  local choice
  while true; do
    # Simple read without any special handling
    echo -ne "${CYAN}Enter your choice [1-3, q]:${NC} "
    read choice
    
    case "$choice" in
      1)
        return 1
        ;;
      2)
        return 2
        ;;
      3)
        return 3
        ;;
      [qQ])
        info "Installation cancelled"
        exit 0
        ;;
      *)
        error "Invalid choice. Please enter 1, 2, 3, or q"
        ;;
    esac
  done
}

# Check if jq is installed
check_jq_installed

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  error "Configuration file not found: $CONFIG_FILE"
  info "Run ./discover-fonts.sh to create the configuration file"
  exit 1
fi

# Check for command line arguments
installation_choice=""
if [ $# -gt 0 ]; then
  case "$1" in
    --web|web|1)
      installation_choice=1
      ;;
    --local|local|2)
      installation_choice=2
      ;;
    --both|both|3)
      installation_choice=3
      ;;
    --help|-h)
      echo "Usage: $0 [--web|--local|--both]"
      echo "  --web   : Install to Web VS Code only"
      echo "  --local : Install to Local VS Code only"
      echo "  --both  : Install to both Web and Local VS Code"
      exit 0
      ;;
    *)
      error "Invalid argument: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
fi

# Show header
echo ""
header "🎨 Dynamic Font Application System"
echo ""

# Generate nerdFonts.css
info "Generating nerdFonts.css based on configuration..."
generate_nerd_fonts_css "$SCRIPT_DIR/nerdFonts.css"
success "nerdFonts.css generated successfully"

# Show selected fonts
echo ""
info "Selected fonts for installation:"
jq -r '.selectedFonts[] | "  • \(.fontFamily): \(.variants | join(", "))"' "$CONFIG_FILE"

# Prompt user for installation type if not provided via command line
if [ -z "$installation_choice" ]; then
  prompt_installation_type
  installation_choice=$?
fi

echo ""

# Execute based on user choice
case $installation_choice in
  1)
    apply_to_web_vscode
    ;;
  2)
    apply_to_local_vscode
    ;;
  3)
    apply_to_web_vscode
    echo ""
    apply_to_local_vscode
    ;;
  *)
    error "Invalid installation choice: $installation_choice"
    exit 1
    ;;
esac

echo ""
success "Font installation complete!"
info "Selected fonts have been applied based on font-config.json"

# Final instructions
echo ""
header "📋 Next Steps:"
echo "  • Restart VS Code for changes to take effect"
echo "  • Use $(highlight "./select-fonts.sh") to change font selection"
echo "  • Use $(highlight "./discover-fonts.sh") to detect new fonts"

# Ensure script exits cleanly
exit 0