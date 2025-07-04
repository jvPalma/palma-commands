#!/usr/bin/env bash
set -euo pipefail

# Example script showing how to add a new font family

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "This is an example of how to add a new font family."
echo "For demonstration, we'll create a template for 'MyCustomFont'"
echo ""

# Create example directory structure
FONT_DIR="$SCRIPT_DIR/MyCustomFont"

if [[ -d "$FONT_DIR" ]]; then
  echo "Directory $FONT_DIR already exists. Remove it first if you want to recreate."
  exit 1
fi

echo "Creating font directory: $FONT_DIR"
mkdir -p "$FONT_DIR"

# Create example CSS files
echo "Creating CSS variant files..."

cat > "$FONT_DIR/_font.css" <<'EOF'
/* My Custom Font - Standard */
@font-face {
    font-family: 'My Custom Font';
    src: url('MyCustomFont-Regular.ttf') format('truetype');
    font-weight: 400;
    font-style: normal;
}

@font-face {
    font-family: 'My Custom Font';
    src: url('MyCustomFont-Bold.ttf') format('truetype');
    font-weight: 700;
    font-style: normal;
}

/* Default styles with ligatures enabled */
* {
    -webkit-font-feature-settings: "liga" on, "calt" on;
    font-feature-settings: "liga" on, "calt" on;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
    font-family: 'My Custom Font', monospace;
}
EOF

cat > "$FONT_DIR/_fontMono.css" <<'EOF'
/* My Custom Font - Monospace */
@font-face {
    font-family: 'My Custom Font Mono';
    src: url('MyCustomFontMono-Regular.ttf') format('truetype');
    font-weight: 400;
    font-style: normal;
}

@font-face {
    font-family: 'My Custom Font Mono';
    src: url('MyCustomFontMono-Bold.ttf') format('truetype');
    font-weight: 700;
    font-style: normal;
}

/* Utility class for mono font */
.font-mono {
    font-family: 'My Custom Font Mono', monospace;
}
EOF

# Create placeholder TTF files (in real scenario, these would be actual font files)
echo "Creating placeholder font files (replace with actual TTF files)..."
touch "$FONT_DIR/MyCustomFont-Regular.ttf"
touch "$FONT_DIR/MyCustomFont-Bold.ttf"
touch "$FONT_DIR/MyCustomFontMono-Regular.ttf"
touch "$FONT_DIR/MyCustomFontMono-Bold.ttf"

echo ""
echo "✓ Example font structure created!"
echo ""
echo "Directory structure:"
echo "==================="
find "$FONT_DIR" -type f | sort

echo ""
echo "Next steps:"
echo "==========="
echo "1. Replace placeholder .ttf files with actual font files"
echo "2. Update CSS files with correct font-family names and file references"
echo "3. Run ./discover-fonts.sh to update configuration"
echo "4. Run ./select-fonts.sh to select your new font"
echo "5. Run ./applyFontVSC.sh to apply the fonts"

echo ""
echo "To remove this example:"
echo "rm -rf '$FONT_DIR'"