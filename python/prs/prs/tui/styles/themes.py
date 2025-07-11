"""
Theme management for PRS TUI.

Provides different color themes and styling options for the TUI interface.
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class ThemeType(Enum):
    """Available theme types."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    GITHUB = "github"
    HIGH_CONTRAST = "high_contrast"


@dataclass
class ThemeColors:
    """Theme color definitions."""
    # Base colors
    background: str
    surface: str
    surface_lighten_1: str
    surface_lighten_2: str
    surface_lighten_3: str
    
    # Primary colors
    primary: str
    primary_lighten_1: str
    primary_lighten_2: str
    primary_lighten_3: str
    primary_darken_1: str
    
    # Secondary colors
    secondary: str
    accent: str
    
    # Text colors
    text: str
    text_muted: str
    text_on_primary: str
    text_on_secondary: str
    text_on_accent: str
    text_on_success: str
    text_on_warning: str
    text_on_error: str
    text_on_info: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str


class ThemeManager:
    """Manages TUI themes and styling."""
    
    def __init__(self):
        self.themes = self._load_themes()
        self.current_theme = ThemeType.DEFAULT
    
    def _load_themes(self) -> Dict[ThemeType, ThemeColors]:
        """Load all available themes."""
        return {
            ThemeType.DEFAULT: self._get_default_theme(),
            ThemeType.DARK: self._get_dark_theme(),
            ThemeType.LIGHT: self._get_light_theme(),
            ThemeType.GITHUB: self._get_github_theme(),
            ThemeType.HIGH_CONTRAST: self._get_high_contrast_theme(),
        }
    
    def _get_default_theme(self) -> ThemeColors:
        """Get the default dark theme."""
        return ThemeColors(
            # Base colors
            background="#0d1117",
            surface="#161b22",
            surface_lighten_1="#21262d",
            surface_lighten_2="#30363d",
            surface_lighten_3="#40464d",
            
            # Primary colors
            primary="#238636",
            primary_lighten_1="#2ea043",
            primary_lighten_2="#46954a",
            primary_lighten_3="#57ab5a",
            primary_darken_1="#1f7e34",
            
            # Secondary colors
            secondary="#30363d",
            accent="#58a6ff",
            
            # Text colors
            text="#f0f6fc",
            text_muted="#8b949e",
            text_on_primary="#ffffff",
            text_on_secondary="#f0f6fc",
            text_on_accent="#ffffff",
            text_on_success="#ffffff",
            text_on_warning="#000000",
            text_on_error="#ffffff",
            text_on_info="#ffffff",
            
            # Status colors
            success="#238636",
            warning="#d29922",
            error="#da3633",
            info="#58a6ff"
        )
    
    def _get_dark_theme(self) -> ThemeColors:
        """Get the dark theme."""
        return ThemeColors(
            # Base colors
            background="#1a1a1a",
            surface="#2d2d2d",
            surface_lighten_1="#3d3d3d",
            surface_lighten_2="#4d4d4d",
            surface_lighten_3="#5d5d5d",
            
            # Primary colors
            primary="#007acc",
            primary_lighten_1="#1e90ff",
            primary_lighten_2="#4169e1",
            primary_lighten_3="#6495ed",
            primary_darken_1="#005a9e",
            
            # Secondary colors
            secondary="#404040",
            accent="#00d7ff",
            
            # Text colors
            text="#ffffff",
            text_muted="#cccccc",
            text_on_primary="#ffffff",
            text_on_secondary="#ffffff",
            text_on_accent="#000000",
            text_on_success="#ffffff",
            text_on_warning="#000000",
            text_on_error="#ffffff",
            text_on_info="#ffffff",
            
            # Status colors
            success="#28a745",
            warning="#ffc107",
            error="#dc3545",
            info="#17a2b8"
        )
    
    def _get_light_theme(self) -> ThemeColors:
        """Get the light theme."""
        return ThemeColors(
            # Base colors
            background="#ffffff",
            surface="#f8f9fa",
            surface_lighten_1="#e9ecef",
            surface_lighten_2="#dee2e6",
            surface_lighten_3="#ced4da",
            
            # Primary colors
            primary="#0066cc",
            primary_lighten_1="#3385d6",
            primary_lighten_2="#66a3e0",
            primary_lighten_3="#99c2ea",
            primary_darken_1="#0052a3",
            
            # Secondary colors
            secondary="#6c757d",
            accent="#007bff",
            
            # Text colors
            text="#212529",
            text_muted="#6c757d",
            text_on_primary="#ffffff",
            text_on_secondary="#ffffff",
            text_on_accent="#ffffff",
            text_on_success="#ffffff",
            text_on_warning="#000000",
            text_on_error="#ffffff",
            text_on_info="#ffffff",
            
            # Status colors
            success="#28a745",
            warning="#ffc107",
            error="#dc3545",
            info="#17a2b8"
        )
    
    def _get_github_theme(self) -> ThemeColors:
        """Get the GitHub-inspired theme."""
        return ThemeColors(
            # Base colors
            background="#0d1117",
            surface="#161b22",
            surface_lighten_1="#21262d",
            surface_lighten_2="#30363d",
            surface_lighten_3="#40464d",
            
            # Primary colors
            primary="#238636",
            primary_lighten_1="#2ea043",
            primary_lighten_2="#46954a",
            primary_lighten_3="#57ab5a",
            primary_darken_1="#1f7e34",
            
            # Secondary colors
            secondary="#30363d",
            accent="#58a6ff",
            
            # Text colors
            text="#f0f6fc",
            text_muted="#8b949e",
            text_on_primary="#ffffff",
            text_on_secondary="#f0f6fc",
            text_on_accent="#ffffff",
            text_on_success="#ffffff",
            text_on_warning="#000000",
            text_on_error="#ffffff",
            text_on_info="#ffffff",
            
            # Status colors
            success="#238636",
            warning="#d29922",
            error="#da3633",
            info="#58a6ff"
        )
    
    def _get_high_contrast_theme(self) -> ThemeColors:
        """Get the high contrast theme for accessibility."""
        return ThemeColors(
            # Base colors
            background="#000000",
            surface="#1a1a1a",
            surface_lighten_1="#333333",
            surface_lighten_2="#4d4d4d",
            surface_lighten_3="#666666",
            
            # Primary colors
            primary="#ffffff",
            primary_lighten_1="#f0f0f0",
            primary_lighten_2="#e0e0e0",
            primary_lighten_3="#d0d0d0",
            primary_darken_1="#cccccc",
            
            # Secondary colors
            secondary="#666666",
            accent="#ffff00",
            
            # Text colors
            text="#ffffff",
            text_muted="#cccccc",
            text_on_primary="#000000",
            text_on_secondary="#ffffff",
            text_on_accent="#000000",
            text_on_success="#000000",
            text_on_warning="#000000",
            text_on_error="#ffffff",
            text_on_info="#000000",
            
            # Status colors
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            info="#00ffff"
        )
    
    def get_theme(self, theme_type: ThemeType) -> ThemeColors:
        """Get a specific theme."""
        return self.themes.get(theme_type, self.themes[ThemeType.DEFAULT])
    
    def set_theme(self, theme_type: ThemeType) -> None:
        """Set the current theme."""
        if theme_type in self.themes:
            self.current_theme = theme_type
    
    def get_current_theme(self) -> ThemeColors:
        """Get the current theme."""
        return self.themes[self.current_theme]
    
    def get_theme_css_variables(self, theme_type: ThemeType = None) -> Dict[str, str]:
        """Get CSS variables for a theme."""
        if theme_type is None:
            theme_type = self.current_theme
        
        theme = self.get_theme(theme_type)
        
        return {
            # Base colors
            "$background": theme.background,
            "$surface": theme.surface,
            "$surface-lighten-1": theme.surface_lighten_1,
            "$surface-lighten-2": theme.surface_lighten_2,
            "$surface-lighten-3": theme.surface_lighten_3,
            
            # Primary colors
            "$primary": theme.primary,
            "$primary-lighten-1": theme.primary_lighten_1,
            "$primary-lighten-2": theme.primary_lighten_2,
            "$primary-lighten-3": theme.primary_lighten_3,
            "$primary-darken-1": theme.primary_darken_1,
            
            # Secondary colors
            "$secondary": theme.secondary,
            "$accent": theme.accent,
            
            # Text colors
            "$text": theme.text,
            "$text-muted": theme.text_muted,
            "$text-on-primary": theme.text_on_primary,
            "$text-on-secondary": theme.text_on_secondary,
            "$text-on-accent": theme.text_on_accent,
            "$text-on-success": theme.text_on_success,
            "$text-on-warning": theme.text_on_warning,
            "$text-on-error": theme.text_on_error,
            "$text-on-info": theme.text_on_info,
            
            # Status colors
            "$success": theme.success,
            "$warning": theme.warning,
            "$error": theme.error,
            "$info": theme.info
        }
    
    def generate_theme_css(self, theme_type: ThemeType = None) -> str:
        """Generate CSS with theme variables."""
        variables = self.get_theme_css_variables(theme_type)
        
        css_lines = [":root {"]
        for var_name, var_value in variables.items():
            css_lines.append(f"    {var_name}: {var_value};")
        css_lines.append("}")
        
        return "\n".join(css_lines)
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return [theme.value for theme in ThemeType]
    
    def apply_theme_to_app(self, app, theme_type: ThemeType = None):
        """Apply theme to a Textual app."""
        if theme_type is None:
            theme_type = self.current_theme
        
        # This would integrate with Textual's theming system
        # For now, we'll just set the theme type
        self.set_theme(theme_type)
        
        # In a real implementation, you might:
        # 1. Update the app's CSS variables
        # 2. Reload stylesheets
        # 3. Trigger a screen refresh
        
        return True


# Global theme manager instance
theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return theme_manager


def set_theme(theme_name: str) -> bool:
    """Set the current theme by name."""
    try:
        theme_type = ThemeType(theme_name)
        theme_manager.set_theme(theme_type)
        return True
    except ValueError:
        return False


def get_current_theme_colors() -> ThemeColors:
    """Get the current theme colors."""
    return theme_manager.get_current_theme()


def get_available_themes() -> List[str]:
    """Get list of available theme names."""
    return theme_manager.get_available_themes()