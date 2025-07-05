#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Utility functions
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
header() { echo -e "\n${MAGENTA}${1}${NC}"; }
highlight() { echo -e "${CYAN}${1}${NC}"; }

# Common utility functions
check_jq_installed() {
  if ! command -v jq &>/dev/null; then
    error "jq is required but not installed. Please install jq to use this script."
    echo "  Ubuntu/Debian: sudo apt install jq"
    echo "  CentOS/RHEL: sudo yum install jq"
    echo "  macOS: brew install jq"
    exit 1
  fi
}

get_script_dir() {
  echo "$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
}

get_config_file() {
  local script_dir="${1:-$(get_script_dir)}"
  echo "$script_dir/font-config.json"
}

save_font_config() {
  local config_file="${1:-$(get_config_file)}"

  # Create config directory if it doesn't exist
  mkdir -p "$(dirname "$config_file")"

  # Create JSON config
  echo '{' >"$config_file"
  echo '  "selectedFontVariants": [' >>"$config_file"

  local first=true
  for variant in "${selected_font_variants[@]}"; do
    if [ "$first" = true ]; then
      first=false
    else
      echo ',' >>"$config_file"
    fi
    echo -n "    \"$variant\"" >>"$config_file"
  done

  echo '' >>"$config_file"
  echo '  ]' >>"$config_file"
  echo '}' >>"$config_file"
}

load_font_config() {
  local config_file="${1:-$(get_config_file)}"
  selected_font_variants=()

  if [ -f "$config_file" ]; then
    # Extract font variants from JSON
    while IFS= read -r line; do
      if [[ "$line" == *'"'*':'*'"'* ]]; then
        local variant=$(echo "$line" | sed 's/.*"\([^"]*\)".*/\1/' | xargs)
        if [ -n "$variant" ] && [[ "$variant" == *":"* ]]; then
          selected_font_variants+=("$variant")
        fi
      fi
    done <"$config_file"
  fi
}

# Global variables
declare -a fonts
declare -a selected_font_variants

# Common paths
WEB_PATH="$HOME/.vscode/cli/serve-web"
LOCAL_PATH="/usr/share/code/resources/app/out/vs/workbench"

# Font management functions
load_available_fonts() {
  fonts=()
  local script_dir="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

  # Determine the fonts directory (where install.sh is located)
  local font_dir="$script_dir"
  if [ "$(basename "$script_dir")" = "_core" ]; then
    font_dir="$(dirname "$script_dir")"
  fi

  # Save current directory and change to font directory
  local current_dir="$(pwd)"
  cd "$font_dir"

  for dir in */; do
    if [ -d "$dir" ] && [ "$(basename "$dir")" != "_core" ]; then
      fonts+=("$(basename "$dir")")
    fi
  done

  # Return to original directory
  cd "$current_dir"

  if [ ${#fonts[@]} -eq 0 ]; then
    error "No font directories found"
    exit 1
  fi
}

get_selected_fonts_from_css() {
  selected_font_variants=()
  if [ -f "nerdFonts.css" ]; then
    local current_font=""

    # Process each line without using while loop to avoid stdin issues
    {
      while IFS= read -r line || [ -n "$line" ]; do
        # Look for font name comments like /* JetbrainsNerdFonts */
        case "$line" in
        "/* "*" */"*)
          if [[ "$line" != *"Generated"* ]]; then
            current_font=$(echo "$line" | sed 's|^/\*[[:space:]]*\([^*]*\)[[:space:]]*\*/.*|\1|' | xargs)
          fi
          ;;
        *"@import"*"url"*)
          if [ -n "$current_font" ]; then
            local css_file=$(echo "$line" | sed 's|.*/\([^"]*\).*|\1|')
            if [ -n "$css_file" ]; then
              selected_font_variants+=("$current_font:$css_file")
            fi
          fi
          ;;
        esac
      done
    } <nerdFonts.css
  fi
}

show_available_fonts() {
  header "📚 Available Fonts"
  echo ""

  local i=1
  for font in "${fonts[@]}"; do
    echo "  $(highlight "$i)") $font"
    i=$((i + 1))
  done
  echo ""
}

show_font_variants() {
  local font="$1"
  if [ ! -d "$font" ]; then
    error "Font directory $font not found"
    return 1
  fi

  header "🎨 Select CSS variants for $font"
  echo ""
  echo "  $(success "Available variants:")"
  echo ""

  local variants=()
  local descriptions=()

  # Dynamically discover all _*.css files
  for css_file in "$font"/_*.css; do
    if [ -f "$css_file" ]; then
      local filename=$(basename "$css_file")
      variants+=("$filename")

      # Generate description based on filename
      local description="CSS variant"
      case "$filename" in
      "_font.css") description="Standard Font" ;;
      "_fontMono.css") description="Monospace Font" ;;
      "_fontPropo.css") description="Proportional Font" ;;
      "_nlFont.css") description="Standard Font (no ligatures)" ;;
      "_nlFontMono.css") description="Monospace Font (no ligatures)" ;;
      "_nlFontPropo.css") description="Proportional Font (no ligatures)" ;;
      *) description="Custom variant" ;;
      esac
      descriptions+=("$description")
    fi
  done

  if [ ${#variants[@]} -eq 0 ]; then
    error "No CSS variants found in $font directory"
    return 1
  fi

  # Display options
  for i in "${!variants[@]}"; do
    local num=$((i + 1))
    echo "  $(highlight "$num)") ${variants[$i]} - ${descriptions[$i]}"
  done

  echo ""
  echo "  $(highlight "Select variants (comma-separated numbers, 'a' for all, or 'c' to cancel):")"
}

show_selected_fonts_array() {
  if [ ${#selected_fonts[@]} -gt 0 ]; then
    header "🎯 Currently Selected Fonts"
    echo ""

    # Show detailed information about each font including CSS files
    for font in "${selected_fonts[@]}"; do
      echo "  $(success "✓") $font"

      # Show CSS files for this font if they exist
      if [ -d "$font" ]; then
        for css_file in "$font"/_*.css; do
          if [ -f "$css_file" ]; then
            local css_name=$(basename "$css_file")
            local description=""

            # Add description based on file name
            case "$css_name" in
            "_font.css")
              description=" (Standard Font)"
              ;;
            "_fontMono.css")
              description=" (Monospace Font)"
              ;;
            "_fontPropo.css")
              description=" (Proportional Font)"
              ;;
            "_nlFont.css")
              description=" (No Ligatures Font)"
              ;;
            "_nlFontMono.css")
              description=" (No Ligatures Monospace)"
              ;;
            "_nlFontPropo.css")
              description=" (No Ligatures Proportional)"
              ;;
            esac

            echo "    $(echo -e "${CYAN}→${NC}") $font/$css_name$description"
          fi
        done
      fi
      echo ""
    done

    success "Total fonts configured: ${#selected_fonts[@]}"
    echo ""
  else
    warning "No fonts configured yet"
    echo ""
  fi
}

generate_css() {
  if [ ${#selected_font_variants[@]} -eq 0 ]; then
    error "No font variants selected"
    return 1
  fi

  info "Generating nerdFonts.css..."
  cat >nerdFonts.css <<'EOF'
/* Generated nerdFonts.css */

EOF

  # Process variants for all selected fonts
  local font_count=0
  local current_font=""

  # Process each variant (already have them in array)
  local i=0
  while [ $i -lt ${#selected_font_variants[@]} ]; do
    local variant="${selected_font_variants[$i]}"
    local font="${variant%:*}"
    local css_file="${variant#*:}"

    # If new font, add header
    if [ "$font" != "$current_font" ]; then
      if [ -n "$current_font" ]; then
        echo "" >>nerdFonts.css
      fi
      echo "/* $font */" >>nerdFonts.css
      current_font="$font"
      font_count=$((font_count + 1))
    fi

    # Add the import
    echo "@import url(\"./$font/$css_file\");" >>nerdFonts.css

    i=$((i + 1))
  done

  echo "" >>nerdFonts.css

  # Save configuration
  save_font_config

  success "nerdFonts.css generated with $font_count font(s) and ${#selected_font_variants[@]} variant(s)"
}

select_fonts() {
  # Reset selected font variants for fresh selection
  selected_font_variants=()

  local done_selecting=false

  while [ "$done_selecting" = false ]; do
    # Show available fonts menu
    clear
    header "🎨 VS Code Font Installer - Select Fonts"
    echo ""

    # Show currently selected if any
    if [ ${#selected_font_variants[@]} -gt 0 ]; then
      info "Currently selected variants:"
      # Simple display of current selections
      local k=0
      while [ $k -lt ${#selected_font_variants[@]} ]; do
        local variant="${selected_font_variants[$k]}"
        local font="${variant%:*}"
        local css="${variant#*:}"
        echo "  • $font - $css"
        k=$((k + 1))
      done
      echo ""
    fi

    header "📚 Available Fonts"
    echo ""
    local i=1
    for font in "${fonts[@]}"; do
      echo "  $(highlight "$i)") $font"
      i=$((i + 1))
    done
    echo ""
    echo "  $(highlight "q)") Done selecting - proceed with current selection"
    echo ""

    read -p "$(echo -e "${CYAN}Select a font number (or 'q' to finish):${NC} ")" font_choice

    # Handle quit
    if [ "$font_choice" = "q" ] || [ "$font_choice" = "Q" ]; then
      done_selecting=true
      continue
    fi

    # Validate font choice
    if [[ ! "$font_choice" =~ ^[0-9]+$ ]] || [ "$font_choice" -lt 1 ] || [ "$font_choice" -gt "${#fonts[@]}" ]; then
      error "Invalid font selection"
      echo "Press any key to continue..."
      read
      continue
    fi

    # Get the selected font
    local selected_font="${fonts[$((font_choice - 1))]}"

    # Show variant selection for this font
    show_font_variants "$selected_font"
    read -p "$(echo -e "${CYAN}Choice: ${NC}")" variant_selection

    # Handle cancel
    if [ "$variant_selection" = "c" ]; then
      warning "Cancelled selection for $selected_font"
      echo "Press any key to continue..."
      read
      continue
    fi

    # Get available variants for this font (dynamically discover like show_font_variants does)
    local available_variants=()
    local num_variants=0

    # Dynamically discover all _*.css files (same logic as show_font_variants)
    for css_file in "$selected_font"/_*.css; do
      if [ -f "$css_file" ]; then
        local filename=$(basename "$css_file")
        available_variants+=("$filename")
        num_variants=$((num_variants + 1))
      fi
    done

    # Parse variant selection
    if [ "$variant_selection" = "a" ]; then
      # Add all available variants
      local j=0
      while [ $j -lt ${#available_variants[@]} ]; do
        selected_font_variants+=("$selected_font:${available_variants[$j]}")
        j=$((j + 1))
      done
      success "Added all $num_variants variants for $selected_font"
    else
      # Parse specific variant numbers using proper comma-separated parsing
      local added_count=0

      # Split input by comma and process each variant number
      IFS=',' read -ra variant_numbers <<<"$variant_selection"

      for variant_num in "${variant_numbers[@]}"; do
        # Trim whitespace
        variant_num=$(echo "$variant_num" | tr -d ' ')

        # Validate it's a number
        if [[ "$variant_num" =~ ^[0-9]+$ ]]; then
          # Convert to array index (1-based to 0-based)
          local index=$((variant_num - 1))

          # Check if index is valid
          if [ $index -ge 0 ] && [ $index -lt $num_variants ]; then
            selected_font_variants+=("$selected_font:${available_variants[$index]}")
            added_count=$((added_count + 1))
          else
            warning "Invalid variant number: $variant_num (valid range: 1-$num_variants)"
          fi
        else
          warning "Invalid variant number: '$variant_num' (must be a number)"
        fi
      done

      if [ $added_count -gt 0 ]; then
        success "Added $added_count variant(s) for $selected_font"
      else
        warning "No valid variants selected"
      fi
    fi

    echo "Press Enter to continue..."
    read -r
  done

  if [ ${#selected_font_variants[@]} -eq 0 ]; then
    error "No font variants selected"
    return 1
  fi

  # Clear previous selections and generate fresh CSS
  generate_css
}

# Installation functions
install_to_web() {
  header "🌐 Installing to Web VS Code"

  if [ ! -d "$WEB_PATH" ]; then
    error "Web VS Code path not found: $WEB_PATH"
    return 1
  fi

  local installed=false
  for commit_hash_dir in "$WEB_PATH"/*; do
    if [ -d "$commit_hash_dir" ]; then
      local commit_hash=$(basename "$commit_hash_dir")
      # Only install to valid commit hashes (exclude test-instance and similar)
      if [[ ! "$commit_hash" =~ ^[a-f0-9]{40}$ ]]; then
        warning "Skipping invalid commit hash: $commit_hash"
        continue
      fi

      local target="$commit_hash_dir/out/vs/code/browser/workbench"
      if [ ! -d "$target" ]; then
        warning "Workbench directory not found in $commit_hash, skipping..."
        continue
      fi

      echo "Installing to commit hash: $commit_hash"

      # Copy CSS
      cp nerdFonts.css "$target/"

      # Copy selected font directories and track what was copied
      local unique_fonts=($(printf '%s\n' "${selected_font_variants[@]}" | sed 's/:.*$//' | sort -u))
      local total_ttf_files=0
      local copied_variants=()

      for font in "${unique_fonts[@]}"; do
        if [ -d "$font" ]; then
          cp -r "$font" "$target/"

          # Count TTF files in this font directory
          local ttf_count=$(find "$font" -name "*.ttf" | wc -l)
          total_ttf_files=$((total_ttf_files + ttf_count))

          # Collect variant files for this font
          for variant_combo in "${selected_font_variants[@]}"; do
            if [[ "$variant_combo" == "$font:"* ]]; then
              local css_file="${variant_combo#*:}"
              copied_variants+=("$font:$css_file")
            fi
          done
        fi
      done

      # Add import to workbench.css if not present
      local workbench_css="$target/workbench.css"
      if [ -f "$workbench_css" ] && ! grep -q 'nerdFonts.css' "$workbench_css"; then
        sed -i '1i@import "nerdFonts.css";' "$workbench_css"
      fi

      success "Installed to commit hash: $commit_hash"
      echo ""
      echo "  $(highlight "Target:") $target"
      echo "  • $(success "${#unique_fonts[@]} fonts") with $(success "$total_ttf_files TTF files")"
      echo "  • $(success "${#copied_variants[@]} CSS variants") installed"
      echo ""
      installed=true
    fi
  done

  if [ "$installed" = false ]; then
    warning "No valid VS Code web instances found in $WEB_PATH"
  fi
}

install_to_local() {
  if [ ! -d "$LOCAL_PATH" ]; then
    error "Local VS Code path not found: $LOCAL_PATH"
    return 1
  fi

  # Copy CSS
  sudo cp nerdFonts.css "$LOCAL_PATH/"

  # Copy selected font directories and track what was copied
  local unique_fonts=($(printf '%s\n' "${selected_font_variants[@]}" | sed 's/:.*$//' | sort -u))
  local total_ttf_files=0
  local copied_variants=()

  for font in "${unique_fonts[@]}"; do
    if [ -d "$font" ]; then
      sudo cp -r "$font" "$LOCAL_PATH/"

      # Count TTF files in this font directory
      local ttf_count=$(find "$font" -name "*.ttf" | wc -l)
      total_ttf_files=$((total_ttf_files + ttf_count))

      # Collect variant files for this font
      for variant_combo in "${selected_font_variants[@]}"; do
        if [[ "$variant_combo" == "$font:"* ]]; then
          local css_file="${variant_combo#*:}"
          copied_variants+=("$font:$css_file")
        fi
      done
    fi
  done

  # Add import to workbench CSS if not present
  local workbench_css="$LOCAL_PATH/workbench.desktop.main.css"
  if [ -f "$workbench_css" ] && ! sudo grep -q 'nerdFonts.css' "$workbench_css"; then
    sudo sed -i '1i@import "nerdFonts.css";' "$workbench_css"
  fi

  clear

  # Display detailed installation summary
  header "💻 Installing to Local VS Code Summary 📋"
  echo ""
  success "Installation Complete!"
  echo ""
  echo "  $(highlight "Installation Path:") $LOCAL_PATH"
  echo ""
  echo "  $(highlight "Files Installed:")"
  echo "  ├── nerdFonts.css"

  # Display tree view of installed fonts and variants
  local font_index=0
  for font in "${unique_fonts[@]}"; do
    font_index=$((font_index + 1))
    local is_last_font=false
    if [ $font_index -eq ${#unique_fonts[@]} ]; then
      is_last_font=true
    fi

    # Count TTF files for this font
    local font_ttf_count=$(find "$font" -name "*.ttf" 2>/dev/null | wc -l)

    if [ "$is_last_font" = true ]; then
      echo "  └── $font/ ($font_ttf_count TTF files)"
    else
      echo "  ├── $font/ ($font_ttf_count TTF files)"
    fi

    # Display variant files for this font
    local variant_index=0
    local font_variants=()
    for variant_combo in "${copied_variants[@]}"; do
      if [[ "$variant_combo" == "$font:"* ]]; then
        font_variants+=("${variant_combo#*:}")
      fi
    done

    for variant_file in "${font_variants[@]}"; do
      variant_index=$((variant_index + 1))
      local is_last_variant=false
      if [ $variant_index -eq ${#font_variants[@]} ]; then
        is_last_variant=true
      fi

      if [ "$is_last_font" = true ]; then
        if [ "$is_last_variant" = true ]; then
          echo "      └── $variant_file"
        else
          echo "      ├── $variant_file"
        fi
      else
        if [ "$is_last_variant" = true ]; then
          echo "  │   └── $variant_file"
        else
          echo "  │   ├── $variant_file"
        fi
      fi
    done
  done

  echo ""
  echo "  $(highlight "Summary:")"
  echo "  • $(success "${#unique_fonts[@]} font directories") installed"
  echo "  • $(success "${#copied_variants[@]} CSS variant files") installed"
  echo "  • $(success "$total_ttf_files TTF font files") copied"
  echo ""
}

install_fonts() {
  if [ ${#selected_font_variants[@]} -eq 0 ]; then
    error "No fonts selected. Select fonts first."
    return 1
  fi

  clear
  header "📦 Install Fonts"
  echo ""

  # Show currently selected fonts
  show_selected_fonts

  # Check what installation options are available
  local web_available=false
  local local_available=false

  # Check for web VS Code (exclude test instances, only real commit hashes)
  if [ -d "$WEB_PATH" ]; then
    for commit_hash_dir in "$WEB_PATH"/*; do
      if [ -d "$commit_hash_dir" ]; then
        local commit_hash=$(basename "$commit_hash_dir")
        # Only consider valid commit hashes (exclude test-instance and similar)
        if [[ "$commit_hash" =~ ^[a-f0-9]{40}$ ]] && [ -d "$commit_hash_dir/out/vs/code/browser/workbench" ]; then
          web_available=true
          break
        fi
      fi
    done
  fi

  # Check for local VS Code
  if [ -d "$LOCAL_PATH" ]; then
    local_available=true
  fi

  header "📋 Installation Options"
  echo ""

  local option_count=0
  local web_option=""
  local local_option=""
  local both_option=""

  # Build available options
  if [ "$web_available" = true ]; then
    option_count=$((option_count + 1))
    web_option="$option_count"
    echo "  $(highlight "$option_count)") Install to Web VS Code ($WEB_PATH)"
  else
    echo "  $(error "✗") Web VS Code not available ($WEB_PATH not found)"
  fi

  if [ "$local_available" = true ]; then
    option_count=$((option_count + 1))
    local_option="$option_count"
    echo "  $(highlight "$option_count)") Install to Local VS Code ($LOCAL_PATH)"
  else
    echo "  $(error "✗") Local VS Code not available ($LOCAL_PATH not found)"
  fi

  if [ "$web_available" = true ] && [ "$local_available" = true ]; then
    option_count=$((option_count + 1))
    both_option="$option_count"
    echo "  $(highlight "$option_count)") Install to both Web and Local VS Code"
  fi

  option_count=$((option_count + 1))
  local return_option="$option_count"
  echo "  $(highlight "$option_count)") Return to main menu"
  echo ""

  if [ $option_count -eq 1 ]; then
    error "No VS Code installations found!"
    echo "Press any key to return..."
    read
    return 1
  fi

  read -p "$(echo -e "${CYAN}Enter your choice [1-$option_count]:${NC} ")" choice

  case $choice in
  "$web_option")
    if [ "$web_available" = true ]; then
      install_to_web
    fi
    ;;
  "$local_option")
    if [ "$local_available" = true ]; then
      install_to_local
    fi
    ;;
  "$both_option")
    if [ "$web_available" = true ] && [ "$local_available" = true ]; then
      install_to_web
      echo ""
      install_to_local
    fi
    ;;
  "$return_option")
    return 0
    ;;
  *)
    error "Invalid choice"
    return 1
    ;;
  esac
}

# Font display function that parses CSS directly (as requested)
show_selected_fonts() {
  # Check if any font variants are selected
  if [ ${#selected_font_variants[@]} -eq 0 ]; then
    warning "No fonts configured yet"
    echo ""
    return
  fi

  header "🎯 Currently Selected Fonts"
  echo ""

  # Group variants by font name for display
  local font_count=0
  local variant_count=${#selected_font_variants[@]}

  # Get unique font names from selected variants
  local unique_fonts=()
  for variant_combo in "${selected_font_variants[@]}"; do
    local font="${variant_combo%:*}"
    # Check if font already in unique_fonts array
    local found=false
    for existing_font in "${unique_fonts[@]}"; do
      if [ "$existing_font" = "$font" ]; then
        found=true
        break
      fi
    done
    if [ "$found" = false ]; then
      unique_fonts+=("$font")
    fi
  done

  # Display each font and its variants
  for font in "${unique_fonts[@]}"; do
    echo "  $(success "$font")"

    # Show all variants for this font
    for variant_combo in "${selected_font_variants[@]}"; do
      if [[ "$variant_combo" == "$font:"* ]]; then
        local css_file="${variant_combo#*:}"
        local description=""
        case "$css_file" in
        "_font.css") description=" (Standard)" ;;
        "_fontMono.css") description=" (Monospace)" ;;
        "_fontPropo.css") description=" (Proportional)" ;;
        "_nlFont.css") description=" (No Ligatures)" ;;
        "_nlFontMono.css") description=" (No Ligatures Monospace)" ;;
        "_nlFontPropo.css") description=" (No Ligatures Proportional)" ;;
        esac
        echo "    $(echo -e "${CYAN}→${NC}") $css_file$description"
      fi
    done
    font_count=$((font_count + 1))
  done

  success "Total fonts configured: $font_count ($variant_count variants)"
  echo ""
}

install_custom_font() {
  clear
  header "📦 Install Custom Font"
  header "📋 How it works"
  echo ""
  echo "The script will automatically:"
  echo "  • Download the font from the Nerd Fonts repository"
  echo "  • Analyze the font structure (subfolders vs main directory)"
  echo "  • Create appropriate CSS variant files (_font.css, _bold.css, etc.)"
  echo "  • Set up proper @font-face declarations"
  echo "  • Provide a summary of what was imported"
  echo ""

  header "💡 Usage Steps"
  echo "1) Browse available fonts at:"
  echo "  $(highlight "https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts")"
  echo ""
  echo "2) Use the automated import script:"
  echo ""
  echo "  $(highlight "./_core/import-font.sh <FontName>")"
  echo ""
  echo "Examples:"
  echo "  $(highlight "./_core/import-font.sh Hack")" " # Clean monospace font"
  echo "  $(highlight "./_core/import-font.sh FiraCode")" " # Ligature-heavy coding font"
  echo "  $(highlight "./_core/import-font.sh RobotoMono")" " # Google's monospace font"
  echo "  $(highlight "./_core/import-font.sh CascadiaCode")" " # Microsoft's coding font"
  echo "  $(highlight "./_core/import-font.sh DejaVuSansMono")" " # Classic readable font"
  echo ""
  echo "3) Wait for the download and setup to complete"
  echo "4) Return to the main menu and select fonts"
  echo "5) Your new font will appear in the available fonts list"
  echo ""
  warning "Note: Font names are case-sensitive and must match exactly!"

  exit 0
}
