#!/usr/bin/env bash
set -euo pipefail

# Colors for output
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

# Font processing helper functions
get_font_weight() {
    local style="$1"
    case "${style,,}" in
        *thin*) echo "100" ;;
        *extralight*|*ultra*light*) echo "200" ;;
        *light*) echo "300" ;;
        *regular*|*normal*) echo "400" ;;
        *medium*) echo "500" ;;
        *semibold*|*demi*bold*) echo "600" ;;
        *bold*) echo "700" ;;
        *extrabold*|*ultra*bold*) echo "800" ;;
        *black*|*heavy*) echo "900" ;;
        *) echo "400" ;;  # Default to normal
    esac
}

get_font_style() {
    local style="$1"
    if [[ "${style,,}" == *italic* ]]; then
        echo "italic"
    else
        echo "normal"
    fi
}

format_font_family() {
    local ttf_filename="$1"
    local style_suffix="$2"
    
    # Remove .ttf extension first
    local name_without_ext=$(echo "$ttf_filename" | sed 's/\.ttf$//')
    
    # Remove the style suffix (with hyphen) from the end
    local base_font_name=$(echo "$name_without_ext" | sed "s/-${style_suffix}$//")
    
    # Add spaces before capital letters (except the first one) for Nerd Font naming
    echo "$base_font_name" | sed 's/\([a-z]\)\([A-Z]\)/\1 \2/g'
}

extract_style_from_filename() {
    local filename="$1"
    local font_base="$2"
    
    # Remove .ttf extension first
    local name_no_ext=$(echo "$filename" | sed 's/\.ttf$//')
    
    # Extract style from the end (everything after the last hyphen)
    local style=$(echo "$name_no_ext" | sed 's/.*-\([^-]*\)$/\1/')
    
    # If no hyphen found, return empty (regular variant)
    if [ "$style" = "$name_no_ext" ]; then
        style=""
    fi
    
    echo "$style"
}

# Check if font name argument is provided
if [ $# -eq 0 ]; then
    error "Font name is required!"
    echo ""
    echo "Usage: $(highlight "./_core/import-font.sh <FontName>")"
    echo ""
    echo "Examples:"
    echo "  $(highlight "./_core/import-font.sh DejaVuSansMono")"
    echo "  $(highlight "./_core/import-font.sh FiraCode")"
    echo "  $(highlight "./_core/import-font.sh Hack")"
    echo ""
    echo "Available fonts can be found at:"
    echo "  $(highlight "https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts")"
    exit 1
fi

FONT_NAME="$1"

header "🔽 Custom Font Importer - $FONT_NAME"
echo ""

# Validate font name (basic check)
if [[ ! "$FONT_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    error "Invalid font name. Use only letters, numbers, hyphens, and underscores."
    exit 1
fi

# Check if font directory already exists
if [ -d "$FONT_NAME" ]; then
    warning "Font directory '$FONT_NAME' already exists!"
    echo ""
    read -p "$(echo -e "${CYAN}Do you want to overwrite it? (y/N):${NC} ")" -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Import cancelled."
        exit 0
    fi
    echo ""
    info "Removing existing directory..."
    rm -rf "$FONT_NAME"
fi

# Step 1: Download font from Nerd Fonts repository
header "📦 Step 1: Downloading $FONT_NAME"
echo ""

info "Cloning Nerd Fonts repository (sparse checkout)..."
if ! git clone --depth 1 --filter=blob:none --sparse https://github.com/ryanoasis/nerd-fonts.git temp-nerd-fonts; then
    error "Failed to clone repository. Check your internet connection."
    exit 1
fi

info "Setting up sparse checkout for patched-fonts/$FONT_NAME..."
cd temp-nerd-fonts
if ! git sparse-checkout set "patched-fonts/$FONT_NAME"; then
    error "Failed to setup sparse checkout."
    cd ..
    rm -rf temp-nerd-fonts
    exit 1
fi

# Check if the font exists in the repository
if [ ! -d "patched-fonts/$FONT_NAME" ]; then
    error "Font '$FONT_NAME' not found in the Nerd Fonts repository!"
    echo ""
    echo "Available fonts can be found at:"
    echo "  $(highlight "https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts")"
    echo ""
    echo "Make sure the font name matches exactly (case-sensitive)."
    cd ..
    rm -rf temp-nerd-fonts
    exit 1
fi

cd ..
mv "temp-nerd-fonts/patched-fonts/$FONT_NAME" "./$FONT_NAME"
rm -rf temp-nerd-fonts

success "Font downloaded successfully!"

# Step 2: Analyze font structure
header "🔍 Step 2: Analyzing font structure"
echo ""

cd "$FONT_NAME"

# Count TTF files in subdirectories and main directory
ttf_in_subdirs=$(find . -mindepth 2 -name "*.ttf" | wc -l)
ttf_in_main=$(find . -maxdepth 1 -name "*.ttf" | wc -l)

echo "  • TTF files in subdirectories: $ttf_in_subdirs"
echo "  • TTF files in main directory: $ttf_in_main"
echo ""

# Step 3: Create CSS variants
header "🎨 Step 3: Creating CSS variants"
echo ""

css_files_created=0

# Handle subdirectories with TTF files
if [ $ttf_in_subdirs -gt 0 ]; then
    info "Creating CSS files for font variants in subdirectories..."
    for dir in */; do
        if [ -d "$dir" ] && [ $(ls "$dir"/*.ttf 2>/dev/null | wc -l) -gt 0 ]; then
            variant_name=$(echo "$dir" | tr '[:upper:]' '[:lower:]' | sed 's|/||')
            css_file="_${variant_name}.css"
            
            echo "/* $FONT_NAME $variant_name variant */" > "$css_file"
            echo "" >> "$css_file"
            
            # Count TTF files in this variant
            ttf_count=$(ls "$dir"/*.ttf 2>/dev/null | wc -l)
            
            for ttf in "$dir"/*.ttf; do
                ttf_basename=$(basename "$ttf")
                ttf_name_no_ext=$(basename "$ttf" .ttf)
                
                # Extract style information from filename
                style=$(extract_style_from_filename "$ttf_name_no_ext" "${FONT_NAME}")
                weight=$(get_font_weight "$style")
                font_style=$(get_font_style "$style")
                
                # Get formatted font family name from the actual TTF filename
                formatted_font_name=$(format_font_family "$ttf_basename" "$style")
                
                # Generate proper @font-face declaration
                cat >> "$css_file" << EOF
@font-face {
    font-family: '$formatted_font_name';
    src: url('./${dir%/}/$ttf_basename') format('truetype');
    font-weight: $weight;
    font-style: $font_style;
}

EOF
            done
            
            success "Created $css_file ($ttf_count TTF files)"
            css_files_created=$((css_files_created + 1))
        fi
    done
fi

# Handle TTF files in main directory
if [ $ttf_in_main -gt 0 ]; then
    info "Creating CSS file for TTF files in main directory..."
    css_file="_font.css"
    
    echo "/* $FONT_NAME main variant */" > "$css_file"
    echo "" >> "$css_file"
    
    for ttf in *.ttf; do
        ttf_basename=$(basename "$ttf")
        ttf_name_no_ext=$(basename "$ttf" .ttf)
        
        # Extract style information from filename
        style=$(extract_style_from_filename "$ttf_name_no_ext" "${FONT_NAME}")
        weight=$(get_font_weight "$style")
        font_style=$(get_font_style "$style")
        
        # Get formatted font family name from the actual TTF filename
        formatted_font_name=$(format_font_family "$ttf_basename" "$style")
        
        # Generate proper @font-face declaration
        cat >> "$css_file" << EOF
@font-face {
    font-family: '$formatted_font_name';
    src: url('./$ttf_basename') format('truetype');
    font-weight: $weight;
    font-style: $font_style;
}

EOF
    done
    
    success "Created $css_file ($ttf_in_main TTF files)"
    css_files_created=$((css_files_created + 1))
fi

cd ..

# Step 4: Final summary
header "📋 Import Summary"
echo ""

total_ttf_files=$((ttf_in_subdirs + ttf_in_main))

echo "  $(highlight "Font Name:") $FONT_NAME"
echo "  $(highlight "Directory:") ./$FONT_NAME/"
echo "  $(highlight "CSS Variants Created:") $css_files_created"
echo "  $(highlight "Total TTF Files:") $total_ttf_files"
echo ""

if [ $css_files_created -gt 0 ]; then
    success "Font import completed successfully!"
    echo ""
    info "CSS variant files created:"
    for css_file in "$FONT_NAME"/_*.css; do
        if [ -f "$css_file" ]; then
            echo "  • $(basename "$css_file")"
        fi
    done
    echo ""
    info "To use this font:"
    echo "  1. Run $(highlight "./install.sh") to start the font installer"
    echo "  2. Select '1) Select fonts' from the main menu"
    echo "  3. Your new font '$FONT_NAME' should appear in the list"
    echo "  4. Select the variants you want to install"
    echo ""
else
    warning "No CSS files were created. This might indicate an issue with the font structure."
    info "Please check the downloaded font directory: ./$FONT_NAME/"
fi