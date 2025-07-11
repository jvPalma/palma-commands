#!/usr/bin/env python3
"""
Example usage of the PRS TUI application.

This script demonstrates how to use the new TUI interface.
"""

import sys
import os

# Add the PRS package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prs'))

def main():
    """Main function to demonstrate TUI usage."""
    
    print("=== PRS TUI (Terminal User Interface) Example ===\n")
    
    print("The PRS TUI provides an interactive terminal interface for browsing pull requests.")
    print("Features include:")
    print("  • Real-time PR list with status indicators")
    print("  • Interactive filtering and searching")
    print("  • Keyboard navigation (vim-like keys supported)")
    print("  • Auto-refresh functionality")
    print("  • Multiple themes (dark, light, blue, high-contrast)")
    print("  • Responsive layout for different terminal sizes")
    print()
    
    print("Usage examples:")
    print("  # Launch TUI mode")
    print("  nprs --tui")
    print()
    print("  # Use TUI subcommand with options")
    print("  nprs tui")
    print("  nprs tui --theme light")
    print("  nprs tui --auto-refresh 60")
    print()
    
    print("Keyboard shortcuts in TUI mode:")
    print("  q, Ctrl+C    - Quit")
    print("  r            - Refresh PRs") 
    print("  f            - Focus filter bar")
    print("  d            - Toggle draft PRs")
    print("  a            - Toggle auto-refresh")
    print("  ↑↓, j/k      - Navigate PR list")
    print("  Enter        - Open PR in browser")
    print("  o            - Open PR in browser")
    print("  Space        - Select PR")
    print("  Esc          - Clear selection")
    print("  ?, h         - Show help")
    print()
    
    print("Filter bar usage:")
    print("  • Type text to search PRs by title, author, or labels")
    print("  • Use 'Drafts' checkbox to include/exclude draft PRs")
    print("  • Press Esc to clear search")
    print()
    
    try:
        # Try to import and run TUI
        from prs.tui.app import run_tui_app
        
        print("TUI is available! You can now run:")
        print("  python -m prs.tui.app")
        print("  or")
        print("  nprs --tui")
        print("  or")  
        print("  nprs tui")
        print()
        
        response = input("Would you like to launch the TUI now? (y/N): ").strip().lower()
        if response in ('y', 'yes'):
            print("\nLaunching PRS TUI...")
            print("Press 'q' or Ctrl+C to quit when done.\n")
            run_tui_app()
        else:
            print("TUI launch cancelled.")
            
    except ImportError as e:
        print(f"TUI not available: {e}")
        print("Install textual with: pip install textual")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())