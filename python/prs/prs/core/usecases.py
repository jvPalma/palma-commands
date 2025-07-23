"""
DEPRECATED: This module has been refactored.

The functionality from this module has been reorganized into:
- prs.core.printPullRequests (main orchestration)
- prs.core.display.panel_renderer (panel rendering)
- prs.core.display.feature_renderers (feature-specific rendering)
- prs.core.display.display_config (mode resolution and colors)

This file is kept for backward compatibility and will be removed in a future version.
Import from prs.core.printPullRequests instead.
"""

from prs.core.printPullRequests import list_pull_requests
from prs.core.display.display_config import get_panel_color

# Backward compatibility exports
__all__ = ["list_pull_requests", "get_panel_color"]
