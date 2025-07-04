#!/usr/bin/env bash
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source utilities
source "$SCRIPT_DIR/_core/utils.sh"

# Main menu display
show_main_menu() {
    clear
    echo ""
    header "🎨 VS Code Font Installer"
    echo ""
    
    # Show selected fonts prominently at the top
    show_selected_fonts
    
    # Show available fonts first
    header "📚 Available Fonts"
    echo ""
    local i=1
    for font in "${fonts[@]}"; do
        echo "  $(highlight "$i)") $font"
        ((i++))
    done
    echo ""
    
    # Show menu options
    header "📋 Menu"
    echo ""
    echo "  $(highlight "1)") Select fonts"
    echo "  $(highlight "2)") Install fonts"
    echo "  $(highlight "3)") Install custom font"
    echo "  $(highlight "4)") Exit"
    echo ""
}

# Main script execution
main() {
    # Initialize font data
    load_available_fonts
    
    # Try to load from config file first, fallback to CSS parsing
    load_font_config
    if [ ${#selected_font_variants[@]} -eq 0 ]; then
        get_selected_fonts_from_css
    fi
    
    # Handle first run vs subsequent runs
    if [ ${#selected_font_variants[@]} -eq 0 ]; then
        # First run - no fonts selected yet
        clear
        echo ""
        header "🎨 VS Code Font Installer"
        echo ""
        info "Welcome! Let's select some fonts to install."
        echo ""
        
        # Go directly to font selection
        select_fonts
        
        # Show main menu after selection
        show_main_menu
    else
        # Subsequent runs - show main menu with current selection
        show_main_menu
    fi
    
    # Main menu loop
    while true; do
        read -p "$(echo -e "${CYAN}Enter your choice [1-4]:${NC} ")" choice
        
        case $choice in
            1)
                echo ""
                select_fonts
                show_main_menu
                ;;
            2)
                if [ ${#selected_font_variants[@]} -eq 0 ]; then
                    echo ""
                    error "No fonts selected. Please select fonts first."
                    echo ""
                else
                    install_fonts
                    echo ""
                    success "Installation complete!"
                    echo ""
                    
                    # Show detailed post-installation instructions
                    header "📋 Next Steps"
                    echo ""
                    
                    # VS Code Web Browser Setup
                    info "VS Code Web Browser Setup:"
                    echo "  1. $(highlight "Open Developer Console"): Press Ctrl+Shift+J (or Cmd+Option+J on Mac)"
                    echo "  2. $(highlight "Hard Reload"): Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
                    echo "  3. $(highlight "Alternative"): Navigate to Settings > Appearance > Font Family and reselect your font"
                    echo ""
                    
                    # VS Code Settings Configuration
                    info "VS Code Settings Configuration:"
                    echo "  Add these settings to your settings.json:"
                    echo ""
                    echo "  {"
                    echo "    \"editor.fontFamily\": \"JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace\","
                    echo "    \"editor.fontSize\": 14,"
                    echo "    \"editor.fontLigatures\": true,"
                    echo "    \"terminal.integrated.fontFamily\": \"JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace\","
                    echo "    \"terminal.integrated.fontSize\": 14"
                    echo "  }"
                    echo ""
                    
                    # Quick access tip
                    info "Quick Access Tip:"
                    echo "  Add this alias to your shell profile for easy font management:"
                    echo "  $(highlight "alias update-fonts=\"cd ~/.fonts && ./install.sh\"")"
                    echo ""
                    
                    echo "Press any key to continue..."
                    read -n 1 -s
                    show_main_menu
                fi
                ;;
            3)
                install_custom_font
                show_main_menu
                ;;
            4)
                echo ""
                info "Goodbye!"
                exit 0
                ;;
            *)
                echo ""
                error "Invalid choice. Please select 1-4."
                echo ""
                ;;
        esac
    done
}

# Run main function
main "$@"