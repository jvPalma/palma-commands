"""
Help screen for PRS TUI application.

Provides comprehensive help documentation, keyboard shortcuts,
and usage instructions.
"""

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Markdown, TabbedContent, TabPane
from textual.binding import Binding

from ..widgets.header import HeaderWidget
from ..widgets.footer import FooterWidget


class HelpScreen(Screen):
    """
    Help and documentation screen.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │ Header (Help title)                             │
    ├─────────────────────────────────────────────────┤
    │ [Shortcuts] [Usage] [About]                     │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │                Help Content                     │
    │                                                 │
    │                                                 │
    │                                                 │
    ├─────────────────────────────────────────────────┤
    │ Footer (navigation)                             │
    └─────────────────────────────────────────────────┘
    """
    
    CSS = """
    HelpScreen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: auto auto 1fr auto;
    }
    
    #header {
        height: 3;
    }
    
    #help-content {
        border: solid $primary;
        padding: 1;
    }
    
    #footer {
        height: 2;
    }
    
    .help-section {
        margin: 1;
        padding: 1;
    }
    
    .shortcut-table {
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    .shortcut-row {
        layout: horizontal;
        height: 1;
        margin-bottom: 1;
    }
    
    .shortcut-key {
        width: 20%;
        color: $accent;
        text-style: bold;
    }
    
    .shortcut-desc {
        width: 80%;
    }
    """
    
    BINDINGS = [
        Binding("escape,q", "close", "Close", show=True),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "prev_tab", "Prev Tab", show=False),
    ]
    
    def compose(self):
        """Compose the help screen layout."""
        yield HeaderWidget(id="header")
        
        with TabbedContent(id="help-content"):
            with TabPane("Shortcuts", id="shortcuts"):
                yield self.create_shortcuts_content()
            
            with TabPane("Usage Guide", id="usage"):
                yield self.create_usage_content()
            
            with TabPane("About", id="about"):
                yield self.create_about_content()
        
        yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize help screen."""
        header = self.query_one("#header", HeaderWidget)
        header.repo_name = "Help"
        header.owner = "Documentation"
    
    def create_shortcuts_content(self) -> Container:
        """Create keyboard shortcuts tab."""
        container = Container()
        
        with container:
            yield Static("[bold cyan]Global Shortcuts[/bold cyan]", classes="help-section")
            
            with Container(classes="shortcut-table"):
                shortcuts = [
                    ("q, Ctrl+C", "Quit application"),
                    ("r", "Refresh data"),
                    ("f", "Focus filter input"),
                    ("d", "Toggle draft PRs"),
                    ("?", "Show this help"),
                    ("Tab", "Toggle detail panel"),
                    ("Esc", "Clear selection/focus"),
                ]
                
                for key, desc in shortcuts:
                    with Container(classes="shortcut-row"):
                        yield Static(key, classes="shortcut-key")
                        yield Static(desc, classes="shortcut-desc")
            
            yield Static("[bold cyan]Navigation Shortcuts[/bold cyan]", classes="help-section")
            
            with Container(classes="shortcut-table"):
                nav_shortcuts = [
                    ("↑, k", "Move up in list"),
                    ("↓, j", "Move down in list"),
                    ("Page Up", "Move up one page"),
                    ("Page Down", "Move down one page"),
                    ("Home, g", "Go to first item"),
                    ("End, G", "Go to last item"),
                    ("Enter", "Open PR details"),
                    ("o", "Open PR in browser"),
                ]
                
                for key, desc in nav_shortcuts:
                    with Container(classes="shortcut-row"):
                        yield Static(key, classes="shortcut-key")
                        yield Static(desc, classes="shortcut-desc")
            
            yield Static("[bold cyan]Selection Shortcuts[/bold cyan]", classes="help-section")
            
            with Container(classes="shortcut-table"):
                selection_shortcuts = [
                    ("Space", "Toggle selection"),
                    ("v", "Toggle multi-select mode"),
                    ("a", "Select all/none"),
                    ("Esc", "Clear selection"),
                ]
                
                for key, desc in selection_shortcuts:
                    with Container(classes="shortcut-row"):
                        yield Static(key, classes="shortcut-key")
                        yield Static(desc, classes="shortcut-desc")
            
            yield Static("[bold cyan]Detail View Shortcuts[/bold cyan]", classes="help-section")
            
            with Container(classes="shortcut-table"):
                detail_shortcuts = [
                    ("1-6", "Switch between tabs"),
                    ("Tab", "Next tab"),
                    ("Shift+Tab", "Previous tab"),
                    ("c", "Copy PR URL"),
                    ("Esc", "Return to list"),
                ]
                
                for key, desc in detail_shortcuts:
                    with Container(classes="shortcut-row"):
                        yield Static(key, classes="shortcut-key")
                        yield Static(desc, classes="shortcut-desc")
        
        return container
    
    def create_usage_content(self) -> Markdown:
        """Create usage guide tab."""
        usage_text = """
# PRS TUI Usage Guide

## Getting Started

PRS TUI provides an interactive terminal interface for viewing and managing GitHub pull requests. The interface consists of several main components:

### Main Interface

- **Header**: Shows repository information and connection status
- **Filter Bar**: Allows searching and filtering PRs
- **Status Bar**: Displays loading status, PR counts, and messages
- **PR List**: Interactive list of pull requests
- **Detail Panel**: Optional detailed view of selected PR
- **Footer**: Shows available keyboard shortcuts

## Filtering and Search

### Text Search
- Type in the filter box to search PR titles, authors, and labels
- Search is case-insensitive and supports partial matches
- Use `#123` to search for specific PR numbers

### Quick Filters
- **My PRs**: Show only PRs authored by you
- **Needs Review**: Show PRs awaiting review
- **Failed CI**: Show PRs with failing checks
- **Approved**: Show PRs that have been approved

### Advanced Filtering
Use special syntax for advanced filtering:
- `author:username` - Filter by author
- `label:bug` - Filter by label
- `ci:failed` - Filter by CI status
- `review:approved` - Filter by review status

## Navigation

### List Navigation
- Use arrow keys or `j`/`k` (vim-style) to navigate
- `Page Up`/`Page Down` for page-wise navigation
- `Home`/`End` or `g`/`G` to go to first/last item

### Multi-Selection
- Press `v` to enter multi-select mode
- Use `Space` to toggle selection of current item
- Press `a` to select/deselect all items
- `Esc` to clear selection and exit multi-select mode

## Detail Views

### Inline Detail Panel
- Toggle with `Tab` key
- Shows summary information for selected PR
- Automatically updates as you navigate

### Full Detail Screen
- Press `Enter` to open full detail view
- Use number keys `1-6` to switch between tabs:
  1. Overview - Basic PR information
  2. Checks - CI/CD status and results
  3. Reviews - Review status and comments
  4. Comments - Discussion comments
  5. Commits - List of commits
  6. Files - Changed files (when available)

## Configuration

Access settings with the configuration menu to customize:
- Display preferences
- Default filters
- Auto-refresh settings
- Repository information

## Tips and Tricks

1. **Use Quick Filters**: The quick filter buttons provide fast access to common filter combinations
2. **Keyboard Navigation**: Learn the vim-style `j`/`k` keys for faster navigation
3. **Auto-Refresh**: Enable auto-refresh to keep PR status up-to-date
4. **Multi-Select**: Use multi-select mode for batch operations
5. **Detail Panel**: Keep the detail panel open for quick PR overview without leaving the list
"""
        return Markdown(usage_text)
    
    def create_about_content(self) -> Markdown:
        """Create about tab."""
        about_text = """
# About PRS TUI

## Overview

PRS (Pull Request Status) TUI is an interactive terminal user interface for viewing and managing GitHub pull requests. It provides a modern, efficient way to monitor PR status, reviews, and CI/CD checks directly from your terminal.

## Features

### Core Features
- **Interactive PR List**: Browse pull requests with real-time status indicators
- **Advanced Filtering**: Search and filter PRs by various criteria
- **Detail Views**: Comprehensive PR information in multiple formats
- **Real-time Updates**: Auto-refresh capabilities to stay current
- **Keyboard Navigation**: Efficient vim-style keyboard shortcuts

### Status Indicators
- **Health Dots**: Visual indicators for overall PR health (●●●, ●●○, ●○○, ●××)
- **Check Status**: CI/CD pipeline status with clear pass/fail indicators
- **Review Status**: Review approval and change request indicators
- **Label Display**: Easy-to-read label information

### Display Modes
- **Normal Mode**: Full-featured interface with detail panel
- **Compact Mode**: Streamlined interface for smaller terminals
- **Table View**: Alternative layout optimized for data scanning

## Technology

### Built With
- **Textual**: Modern Python TUI framework with reactive programming
- **Rich**: Advanced terminal formatting and styling
- **GitHub CLI**: Integration with GitHub's official command-line tool

### Architecture
- **Reactive Design**: Automatic UI updates based on data changes
- **Modular Widgets**: Reusable components for different UI sections
- **Async Operations**: Non-blocking data fetching and updates
- **Caching System**: Efficient data management for better performance

## Integration

### GitHub Integration
- Uses GitHub CLI (`gh`) for authenticated API access
- Supports GitHub Enterprise and github.com
- Respects existing GitHub CLI authentication

### Configuration
- Integrates with existing PRS configuration files
- Supports organization-specific settings
- Customizable display preferences

## Version Information

- **Framework**: Textual (Modern Python TUI)
- **Python**: 3.6+ required
- **GitHub CLI**: Required for API access
- **Platform**: Cross-platform (Linux, macOS, Windows)

## Support

For issues, feature requests, and contributions, please visit the project repository.

---

*Built with ❤️ for developers who live in the terminal*
"""
        return Markdown(about_text)
    
    # Action handlers
    def action_close(self) -> None:
        """Close help screen."""
        self.app.pop_screen()
    
    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        tabs.next_tab()
    
    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one(TabbedContent)
        tabs.previous_tab()