"""
TUI widgets package for PRS application.
"""

from .header import HeaderWidget, CompactHeaderWidget
from .footer import FooterWidget, CompactFooterWidget, StatusBarWidget as FooterStatusBarWidget
from .filter_bar import FilterBarWidget, CompactFilterBarWidget
from .status_bar import StatusBarWidget, CompactStatusBarWidget
from .pr_list import PRListWidget, PRListItem, CompactPRListWidget, CompactPRListItem
from .navigation_sidebar import NavigationSidebar
from .pr_detail import PRDetailWidget, CompactPRDetailWidget

__all__ = [
    "HeaderWidget",
    "CompactHeaderWidget", 
    "FooterWidget",
    "CompactFooterWidget",
    "FooterStatusBarWidget",
    "FilterBarWidget",
    "CompactFilterBarWidget",
    "StatusBarWidget",
    "CompactStatusBarWidget",
    "PRListWidget",
    "PRListItem",
    "CompactPRListWidget",
    "CompactPRListItem",
    "NavigationSidebar",
    "PRDetailWidget",
    "CompactPRDetailWidget",
]