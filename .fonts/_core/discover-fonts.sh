#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/font-config.json"
TEMP_CONFIG="/tmp/font-config-new.json"

# Function to discover font variants in a directory
discover_font_variants() {
  local font_dir="$1"
  local font_name=$(basename "$font_dir")
  
  # Find all CSS files that start with underscore (variant files)
  local variants=()
  while IFS= read -r css_file; do
    if [[ -f "$css_file" ]]; then
      local variant_name=$(basename "$css_file")
      variants+=("\"$variant_name\"")
    fi
  done < <(find "$font_dir" -maxdepth 1 -name "_*.css" -type f | sort)
  
  echo "${variants[@]}"
}

# Function to analyze CSS file to extract description
extract_css_description() {
  local css_file="$1"
  local description=""
  
  # Try to extract the first comment as description
  if [[ -f "$css_file" ]]; then
    description=$(head -n 5 "$css_file" | grep -oP '^/\*\s*\K[^*]+(?=\s*\*/)' | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  fi
  
  if [[ -z "$description" ]]; then
    # Generate description based on filename
    local basename=$(basename "$css_file" .css)
    case "$basename" in
      "_font") description="Standard font with ligatures" ;;
      "_fontMono") description="Monospace variant" ;;
      "_fontPropo") description="Proportional variant" ;;
      "_nlFont") description="No ligatures variant" ;;
      "_nlFontMono") description="No ligatures monospace variant" ;;
      "_nlFontPropo") description="No ligatures proportional variant" ;;
      *) description="Font variant: $basename" ;;
    esac
  fi
  
  echo "$description"
}

# Function to generate display name from directory name
generate_display_name() {
  local dir_name="$1"
  # Convert camelCase/PascalCase to space-separated words
  echo "$dir_name" | sed -r 's/([a-z])([A-Z])/\1 \2/g' | sed 's/NerdFont/ Nerd Font/g'
}

echo "Discovering fonts in $SCRIPT_DIR..."

# Start building new configuration
cat > "$TEMP_CONFIG" <<EOF
{
  "selectedFonts": [],
  "availableFonts": {
EOF

first_font=true

# Discover all font directories
for font_dir in "$SCRIPT_DIR"/*/; do
  if [[ -d "$font_dir" ]] && [[ ! "$(basename "$font_dir")" =~ ^(\..*|node_modules|dist|build)$ ]]; then
    # Check if directory contains font files
    if ls "$font_dir"/*.ttf &>/dev/null || ls "$font_dir"/_*.css &>/dev/null; then
      font_name=$(basename "$font_dir")
      display_name=$(generate_display_name "$font_name")
      
      echo "Found font: $font_name"
      
      # Add comma if not first font
      if [[ "$first_font" != true ]]; then
        echo "," >> "$TEMP_CONFIG"
      fi
      first_font=false
      
      # Add font entry
      cat >> "$TEMP_CONFIG" <<EOF
    "$font_name": {
      "displayName": "$display_name",
      "variants": {
EOF
      
      # Discover variants
      first_variant=true
      while IFS= read -r css_file; do
        if [[ -f "$css_file" ]]; then
          variant_name=$(basename "$css_file")
          description=$(extract_css_description "$css_file")
          
          # Add comma if not first variant
          if [[ "$first_variant" != true ]]; then
            echo "," >> "$TEMP_CONFIG"
          fi
          first_variant=false
          
          echo "        \"$variant_name\": \"$description\"" >> "$TEMP_CONFIG"
        fi
      done < <(find "$font_dir" -maxdepth 1 -name "_*.css" -type f | sort)
      
      cat >> "$TEMP_CONFIG" <<EOF

      }
    }
EOF
    fi
  fi
done

cat >> "$TEMP_CONFIG" <<EOF

  }
}
EOF

# If original config exists, preserve selectedFonts
if [[ -f "$CONFIG_FILE" ]]; then
  # Extract selectedFonts from original config
  selected_fonts=$(jq -c '.selectedFonts' "$CONFIG_FILE" 2>/dev/null || echo '[]')
  
  # Update temp config with selectedFonts
  jq --argjson selected "$selected_fonts" '.selectedFonts = $selected' "$TEMP_CONFIG" > "${TEMP_CONFIG}.tmp"
  mv "${TEMP_CONFIG}.tmp" "$TEMP_CONFIG"
fi

# Format the JSON nicely
jq '.' "$TEMP_CONFIG" > "${TEMP_CONFIG}.formatted"
mv "${TEMP_CONFIG}.formatted" "$CONFIG_FILE"
rm -f "$TEMP_CONFIG"

echo "Font discovery complete!"
echo "Configuration updated in: $CONFIG_FILE"
echo ""
echo "Available fonts:"
jq -r '.availableFonts | to_entries[] | "- \(.key): \(.value.displayName)"' "$CONFIG_FILE"