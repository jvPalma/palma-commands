"""
Help modal for TUI.

Provides comprehensive help information, keyboard shortcuts,
and usage guides for the TUI interface.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Tabs, TabPane
from textual.widgets import (
    Button, Label, Static, TabbedContent, Tab, Markdown, Tree
)
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen


@dataclass
class HelpSection:
    """Represents a help section."""
    title: str
    content: str
    category: str


class HelpModal(ModalScreen):
    """
    Help modal for the TUI interface.
    
    Features:
    - Keyboard shortcuts reference
    - Feature documentation
    - Usage examples
    - Troubleshooting guide
    """
    
    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }
    
    #help_container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #help_title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #help_tabs {
        height: 85%;
        margin-bottom: 1;
    }
    
    #button_container {
        height: auto;
        align: center middle;
    }
    
    .help_section {
        padding: 1;
        height: 100%;
    }
    
    .help_content {
        height: 100%;
        overflow-y: auto;
    }
    
    .shortcut_table {
        width: 100%;
        border: solid $secondary;
        margin-bottom: 1;
    }
    
    .shortcut_row {
        padding: 1;
        border-bottom: solid $secondary;
    }
    
    .shortcut_key {
        width: 30%;
        text-style: bold;
        color: $accent;
    }
    
    .shortcut_desc {
        width: 70%;
    }
    
    .feature_item {
        margin-bottom: 1;
        padding: 1;
        border: solid $secondary;
    }
    
    .feature_title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .code_block {
        background: $surface-lighten-1;
        padding: 1;
        border: solid $secondary;
        margin: 1 0;
    }
    """
    
    class HelpClosed(Message):
        """Message sent when help is closed."""
        pass
    
    def __init__(self):
        super().__init__()
        self.shortcuts = self._get_keyboard_shortcuts()
        self.features = self._get_feature_help()
        self.troubleshooting = self._get_troubleshooting_guide()
    
    def compose(self) -> ComposeResult:
        """Compose the help modal."""
        with Container(id="help_container"):
            yield Label("❓ PRS TUI Help", id="help_title")
            
            with TabbedContent(id="help_tabs"):
                # Keyboard Shortcuts Tab
                with TabPane("Shortcuts", id="shortcuts_tab"):
                    yield self._create_shortcuts_content()
                
                # Features Tab
                with TabPane("Features", id="features_tab"):
                    yield self._create_features_content()
                
                # Usage Examples Tab
                with TabPane("Examples", id="examples_tab"):
                    yield self._create_examples_content()
                
                # Troubleshooting Tab
                with TabPane("Troubleshooting", id="troubleshooting_tab"):
                    yield self._create_troubleshooting_content()
                
                # About Tab
                with TabPane("About", id="about_tab"):
                    yield self._create_about_content()
            
            with Horizontal(id="button_container"):
                yield Button("Close", variant="primary", id="close_button")
    
    def _create_shortcuts_content(self) -> Container:
        """Create keyboard shortcuts content."""
        container = Container(classes="help_section")
        
        with container:
            yield Label("Keyboard Shortcuts", classes="feature_title")
            
            # Group shortcuts by category
            categories = {}
            for shortcut in self.shortcuts:
                category = shortcut.get('category', 'General')
                if category not in categories:
                    categories[category] = []
                categories[category].append(shortcut)
            
            for category, shortcuts in categories.items():
                yield Label(f"\n{category}", classes="feature_title")
                
                for shortcut in shortcuts:
                    with Horizontal(classes="shortcut_row"):
                        yield Label(shortcut['key'], classes="shortcut_key")
                        yield Label(shortcut['description'], classes="shortcut_desc")
        
        return container
    
    def _create_features_content(self) -> Container:
        """Create features help content."""
        container = Container(classes="help_section")
        
        with container:
            yield Label("Features Overview", classes="feature_title")
            
            for feature in self.features:
                with Container(classes="feature_item"):
                    yield Label(feature['title'], classes="feature_title")
                    yield Static(feature['description'])
                    
                    if feature.get('usage'):
                        yield Label("Usage:", classes="feature_title")
                        yield Static(feature['usage'], classes="code_block")
        
        return container
    
    def _create_examples_content(self) -> Container:
        """Create usage examples content."""
        container = Container(classes="help_section")
        
        with container:
            yield Label("Usage Examples", classes="feature_title")
            
            examples = [
                {
                    'title': 'Basic Navigation',
                    'content': '''
• Use Tab/Shift+Tab to move between UI elements
• Use Enter to activate buttons and select items
• Use Escape to close modals and return to main view
• Use arrow keys to navigate lists and tables
                    '''
                },
                {
                    'title': 'Search and Filtering',
                    'content': '''
• Press Ctrl+F to open advanced search
• Use filters to narrow down PR results
• Save commonly used search filters
• Combine multiple search criteria with AND/OR logic
                    '''
                },
                {
                    'title': 'Real-time Updates',
                    'content': '''
• Press F5 to manually refresh data
• Enable watch mode for automatic updates
• CI status updates happen in background
• Green indicators show recently updated items
                    '''
                },
                {
                    'title': 'Configuration',
                    'content': '''
• Press Ctrl+, to open configuration
• Modify display verbosity settings
• Change TUI theme and appearance
• Save settings for future sessions
                    '''
                }
            ]
            
            for example in examples:
                with Container(classes="feature_item"):
                    yield Label(example['title'], classes="feature_title")
                    yield Static(example['content'])
        
        return container
    
    def _create_troubleshooting_content(self) -> Container:
        """Create troubleshooting content."""
        container = Container(classes="help_section")
        
        with container:
            yield Label("Troubleshooting Guide", classes="feature_title")
            
            for issue in self.troubleshooting:
                with Container(classes="feature_item"):
                    yield Label(f"❌ {issue['problem']}", classes="feature_title")
                    yield Label("Solution:")
                    yield Static(issue['solution'])
                    
                    if issue.get('additional_info'):
                        yield Label("Additional Information:")
                        yield Static(issue['additional_info'])
        
        return container
    
    def _create_about_content(self) -> Container:
        """Create about content."""
        container = Container(classes="help_section")
        
        with container:
            yield Label("About PRS TUI", classes="feature_title")
            
            about_text = """
PRS (Pull Request Status) TUI is an interactive terminal interface for managing and monitoring GitHub pull requests.

**Version:** 2.0.0
**Author:** PRS Development Team
**License:** MIT

**Features:**
• Real-time PR monitoring
• Advanced search and filtering
• CI/CD status tracking
• Interactive configuration
• Multiple display formats
• Keyboard-driven navigation

**GitHub Repository:**
https://github.com/your-org/prs

**Documentation:**
Visit the GitHub repository for complete documentation, examples, and contribution guidelines.

**Support:**
For issues and questions, please create an issue on the GitHub repository.
            """
            
            yield Static(about_text)
        
        return container
    
    def _get_keyboard_shortcuts(self) -> List[Dict]:
        """Get keyboard shortcuts list."""
        return [
            {
                'key': 'F1',
                'description': 'Show this help dialog',
                'category': 'General'
            },
            {
                'key': 'F5',
                'description': 'Refresh data',
                'category': 'General'
            },
            {
                'key': 'Ctrl+Q',
                'description': 'Quit application',
                'category': 'General'
            },
            {
                'key': 'Escape',
                'description': 'Close modal/dialog',
                'category': 'General'
            },
            {
                'key': 'Tab',
                'description': 'Next UI element',
                'category': 'Navigation'
            },
            {
                'key': 'Shift+Tab',
                'description': 'Previous UI element',
                'category': 'Navigation'
            },
            {
                'key': 'Arrow Keys',
                'description': 'Navigate lists and tables',
                'category': 'Navigation'
            },
            {
                'key': 'Enter',
                'description': 'Activate/Select',
                'category': 'Navigation'
            },
            {
                'key': 'Ctrl+F',
                'description': 'Open search dialog',
                'category': 'Search'
            },
            {
                'key': 'Ctrl+G',
                'description': 'Find next search result',
                'category': 'Search'
            },
            {
                'key': 'Ctrl+Shift+G',
                'description': 'Find previous search result',
                'category': 'Search'
            },
            {
                'key': 'Ctrl+,',
                'description': 'Open configuration',
                'category': 'Settings'
            },
            {
                'key': 'Ctrl+W',
                'description': 'Toggle watch mode',
                'category': 'View'
            },
            {
                'key': 'Ctrl+T',
                'description': 'Switch display format',
                'category': 'View'
            },
            {
                'key': 'Ctrl+D',
                'description': 'Toggle draft PRs',
                'category': 'View'
            },
            {
                'key': 'Space',
                'description': 'Toggle item selection',
                'category': 'Selection'
            },
            {
                'key': 'Ctrl+A',
                'description': 'Select all items',
                'category': 'Selection'
            },
            {
                'key': 'Ctrl+N',
                'description': 'Clear selection',
                'category': 'Selection'
            }
        ]
    
    def _get_feature_help(self) -> List[Dict]:
        """Get features help information."""
        return [
            {
                'title': 'Real-time Updates',
                'description': 'Automatically refresh PR data and CI status in the background without blocking the UI.',
                'usage': 'Enable watch mode with Ctrl+W or configure auto-refresh interval in settings.'
            },
            {
                'title': 'Advanced Search',
                'description': 'Powerful search and filtering system with multiple criteria and saved filters.',
                'usage': 'Press Ctrl+F to open search dialog. Create complex filters using AND/OR logic.'
            },
            {
                'title': 'CI/CD Integration',
                'description': 'Monitor CI status from GitHub Actions, Buildkite, and other providers.',
                'usage': 'CI status is automatically fetched and displayed with color-coded indicators.'
            },
            {
                'title': 'Interactive Configuration',
                'description': 'Modify all settings through the TUI without editing configuration files.',
                'usage': 'Press Ctrl+, to open configuration dialog with validation and preview.'
            },
            {
                'title': 'Multiple Display Formats',
                'description': 'Switch between panels and table view for different information density.',
                'usage': 'Press Ctrl+T to toggle between display formats.'
            },
            {
                'title': 'Keyboard Navigation',
                'description': 'Fully keyboard-driven interface for efficient navigation and control.',
                'usage': 'Use Tab, arrow keys, and shortcuts for all operations.'
            }
        ]
    
    def _get_troubleshooting_guide(self) -> List[Dict]:
        """Get troubleshooting guide."""
        return [
            {
                'problem': 'TUI not starting or crashing',
                'solution': 'Check that your terminal supports the required features. Ensure Python 3.7+ and required dependencies are installed.',
                'additional_info': 'Try running with --debug flag to see detailed error messages.'
            },
            {
                'problem': 'GitHub authentication failing',
                'solution': 'Ensure GitHub CLI (gh) is installed and authenticated. Run "gh auth status" to check.',
                'additional_info': 'PRS uses the same authentication as GitHub CLI.'
            },
            {
                'problem': 'Data not refreshing',
                'solution': 'Check your internet connection and GitHub API rate limits. Try manual refresh with F5.',
                'additional_info': 'Rate limits reset hourly. Authenticated users have higher limits.'
            },
            {
                'problem': 'CI status not showing',
                'solution': 'Verify that your repository has CI/CD configured and that you have access to view the workflows.',
                'additional_info': 'Some CI providers require additional authentication setup.'
            },
            {
                'problem': 'Configuration not saving',
                'solution': 'Check file permissions for the PRS configuration directory (~/.prsconfig).',
                'additional_info': 'Ensure the directory is writable by your user account.'
            },
            {
                'problem': 'Performance issues',
                'solution': 'Reduce auto-refresh frequency, limit the number of PRs displayed, or disable animations.',
                'additional_info': 'Large repositories with many PRs may require adjusted settings.'
            },
            {
                'problem': 'Colors not displaying correctly',
                'solution': 'Ensure your terminal supports 256 colors or true color. Try switching themes in configuration.',
                'additional_info': 'Some terminals may require specific environment variables (TERM, COLORTERM).'
            }
        ]
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close_button":
            self.post_message(self.HelpClosed())
            self.dismiss()