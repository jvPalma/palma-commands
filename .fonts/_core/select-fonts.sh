#!/usr/bin/env bash
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
CONFIG_FILE="$SCRIPT_DIR/font-config.json"

# Check if jq is installed
check_jq_installed

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
  warning "Configuration file not found. Running font discovery first..."
  "$SCRIPT_DIR/discover-fonts.sh"
fi

# Function to display available fonts
display_available_fonts() {
  header "📚 Available Fonts"
  echo ""
  
  local i=1
  while IFS= read -r font; do
    local font_name=$(echo "$font" | cut -d: -f1 | xargs)
    local display_name=$(echo "$font" | cut -d: -f2- | xargs)
    
    # Check if this font is selected
    local selected_indicator=""
    if echo "$selected_fonts" | jq -e ".[] | select(.fontFamily == \"$font_name\")" >/dev/null 2>&1; then
      selected_indicator=" ${GREEN}✓${NC}"
    fi
    
    echo "  $(highlight "$i)") $display_name $(echo -e "${BLUE}($font_name)${NC}$selected_indicator")"
    ((i++))
  done < <(jq -r '.availableFonts | to_entries[] | "\(.key): \(.value.displayName)"' "$CONFIG_FILE")
}

# Function to display variants for a font
display_font_variants() {
  local font_name="$1"
  echo ""
  header "🎨 Available Variants for $font_name"
  echo ""
  
  # Get currently selected variants for this font
  local selected_variants=$(echo "$selected_fonts" | jq -r ".[] | select(.fontFamily == \"$font_name\") | .variants[]" 2>/dev/null || echo "")
  
  local i=1
  while IFS= read -r variant; do
    local variant_file=$(echo "$variant" | cut -d: -f1 | xargs)
    local description=$(echo "$variant" | cut -d: -f2- | xargs)
    
    # Check if this variant is selected
    local selected_indicator=""
    if echo "$selected_variants" | grep -q "^$variant_file$"; then
      selected_indicator=" ${GREEN}✓${NC}"
    fi
    
    echo "  $(highlight "$i)") $(echo -e "${CYAN}$variant_file${NC}") - $description$selected_indicator"
    ((i++))
  done < <(jq -r ".availableFonts.\"$font_name\".variants | to_entries[] | \"\(.key): \(.value)\"" "$CONFIG_FILE")
}

# Function to get font name by index
get_font_by_index() {
  local index="$1"
  jq -r ".availableFonts | to_entries | .[$(($index-1))].key" "$CONFIG_FILE" 2>/dev/null
}

# Function to get variant by index
get_variant_by_index() {
  local font_name="$1"
  local index="$2"
  jq -r ".availableFonts.\"$font_name\".variants | to_entries | .[$(($index-1))].key" "$CONFIG_FILE" 2>/dev/null
}

clear
# Main selection process
echo ""
header "🎨 Font Selection Tool"
echo ""

# Initialize selected fonts array from config file
selected_fonts=$(jq -c '.selectedFonts' "$CONFIG_FILE" 2>/dev/null || echo '[]')

while true; do
  clear
  display_available_fonts
  echo ""
  
  # Show selected fonts if any
  if [ $(echo "$selected_fonts" | jq 'length') -gt 0 ]; then
    echo "$(header "📋 Currently Selected:")"
    echo "$selected_fonts" | jq -r '.[] | "  • \(.fontFamily): \(.variants | join(", "))"' | while read line; do
      echo -e "  ${GREEN}$line${NC}"
    done
    echo ""
  fi
  
  echo "$(highlight "Commands:")"
  echo "  • Enter font number to configure"
  echo "  • Type $(highlight "'q'") to quit without saving" 
  echo "  • Type $(highlight "'s'") to save and apply fonts"
  echo ""
  read -p "$(echo -e "${CYAN}Your choice:${NC} ")" font_choice
  
  if [[ "$font_choice" == "q" ]]; then
    info "Exiting without saving..."
    exit 0
  elif [[ "$font_choice" == "s" ]]; then
    break
  elif [[ "$font_choice" =~ ^[0-9]+$ ]]; then
    font_name=$(get_font_by_index "$font_choice")
    
    if [[ -n "$font_name" ]]; then
      clear
      display_font_variants "$font_name"
      echo ""
      echo "$(highlight "Variant Commands:")"
      echo "  • Enter numbers separated by commas (e.g., 1,2,3)"
      echo "  • Type $(highlight "'a'") to select all variants"
      echo "  • Type $(highlight "'b'") to go back to font list"
      echo ""

      read -p "$(echo -e "${CYAN}Select variants:${NC} ")" variant_choices
      
      if [[ "$variant_choices" == "b" ]]; then
        continue
      elif [[ "$variant_choices" == "a" ]]; then
        # Select all variants
        variants=$(jq -r ".availableFonts.\"$font_name\".variants | keys | @json" "$CONFIG_FILE")
      else
        # Parse selected variants
        variants="[]"
        IFS=',' read -ra choices <<< "$variant_choices"
        for choice in "${choices[@]}"; do
          choice=$(echo "$choice" | xargs)  # Trim whitespace
          if [[ "$choice" =~ ^[0-9]+$ ]]; then
            variant=$(get_variant_by_index "$font_name" "$choice")
            if [[ -n "$variant" ]]; then
              variants=$(echo "$variants" | jq ". + [\"$variant\"]")
            fi
          fi
        done
      fi
      
      # Add font to selected fonts
      font_obj=$(jq -n --arg family "$font_name" --argjson variants "$variants" '{fontFamily: $family, variants: $variants}')
      
      # Remove existing entry for this font if any
      selected_fonts=$(echo "$selected_fonts" | jq "map(select(.fontFamily != \"$font_name\"))")
      
      # Add new entry
      selected_fonts=$(echo "$selected_fonts" | jq ". + [$font_obj]")
      
      echo ""
      success "Added $font_name with selected variants"
      echo ""
    else
      error "Invalid selection. Please try again."
    fi
  else
    error "Invalid input. Please enter a number, 'q' to quit, or 's' to save."
  fi
done

# Save configuration
echo ""
info "Saving configuration..."

# Update config file with selected fonts
jq --argjson selected "$selected_fonts" '.selectedFonts = $selected' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

clear
info "Saving configuration..."
success "Configuration saved!"
echo ""
header "📋 Selected Fonts:"
jq -r '.selectedFonts[] | "  • \(.fontFamily): \(.variants | join(", "))"' "$CONFIG_FILE"

echo ""
read -p "$(echo -e "${CYAN}Do you want to apply the fonts now? [Y/n]:${NC} ")" apply_choice

if [[ "$apply_choice" == "y" || "$apply_choice" == "Y" || "$apply_choice" == "" ]]; then
  clear
  echo ""
  echo "Where would you like to install the fonts?"
  echo ""
  echo "  $(highlight "1)") Web VS Code (CLI server)"
  echo "  $(highlight "2)") Local VS Code installation"
  echo "  $(highlight "3)") Both web and local"
  echo "  $(highlight "q)") Cancel"
  echo ""
  read -p "$(echo -e "${CYAN}Enter your choice [1-3, q]:${NC} ")" install_choice
  
  case "$install_choice" in
    1)
      info "Installing to Web VS Code..."
      "$SCRIPT_DIR/applyFontVSC.sh" --web
      ;;
    2)
      info "Installing to Local VS Code..."
      "$SCRIPT_DIR/applyFontVSC.sh" --local
      ;;
    3)
      info "Installing to both Web and Local VS Code..."
      "$SCRIPT_DIR/applyFontVSC.sh" --both
      ;;
    [qQ])
      info "Installation cancelled"
      ;;
    *)
      error "Invalid choice"
      ;;
  esac
else
  echo ""
  info "Configuration saved. Run $(highlight "./applyFontVSC.sh") to apply the fonts."
fi