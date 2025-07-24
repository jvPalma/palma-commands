"""
Username color management system for PRS.

Provides consistent, persistent color assignment for usernames based on:
1. Deterministic hash-based color selection
2. Persistent storage in config file
3. Terminal-friendly color palette
4. Conflict resolution and fallbacks
"""

import hashlib
import json
from typing import Tuple, Optional
from prs.config import get, set as config_set

# Terminal-friendly color palette optimized for readability
# Ordered by preference - brighter colors first for better visibility
TERMINAL_COLOR_PALETTE = [
    "brgreen",     # Bright green - high contrast
    "brcyan",      # Bright cyan - good visibility  
    "bryellow",    # Bright yellow - attention-grabbing
    "brmagenta",   # Bright magenta - distinctive
    "brblue",      # Bright blue - clear contrast
    "brwhite",     # Bright white - high contrast
    "green",       # Standard green
    "cyan",        # Standard cyan
    "yellow",      # Standard yellow
    "magenta",     # Standard magenta
    "blue",        # Standard blue
    "white",       # Standard white
    "gray-1",      # Light gray
    "gray-2",      # Medium-light gray
    "brblack",     # Bright black (gray)
    "gray-3",      # Medium gray
    "red",         # Standard red (lower priority)
    "brred",       # Bright red (lower priority)
    "gray-4",      # Dark gray
    "gray-5",      # Darker gray
]

# Reserved colors that should not be assigned to users
RESERVED_COLORS = {
    "black",   # Used for own username foreground
    "green",   # Used for own username background (when used as bg)
}

# Filter out reserved colors from the palette
AVAILABLE_COLORS = [color for color in TERMINAL_COLOR_PALETTE if color not in RESERVED_COLORS]


def _hash_username(username: str) -> int:
    """
    Generate a deterministic hash for a username.
    Uses SHA-256 for consistent results across sessions.
    """
    return int(hashlib.sha256(username.encode('utf-8')).hexdigest(), 16)


def _get_color_assignments() -> dict:
    """
    Get the current color assignments from config.
    Returns empty dict if none exist or if parsing fails.
    """
    try:
        assignments_json = get("user-colors", "assignments", fallback="{}")
        return json.loads(assignments_json) if assignments_json else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _save_color_assignments(assignments: dict) -> None:
    """
    Save color assignments to config file.
    """
    assignments_json = json.dumps(assignments, sort_keys=True)
    config_set("user-colors", "assignments", assignments_json)


def _find_available_color(assigned_colors: set) -> str:
    """
    Find the next available color from the palette.
    Returns the first color not in the assigned_colors set.
    If all colors are taken, cycles back to the beginning.
    """
    for color in AVAILABLE_COLORS:
        if color not in assigned_colors:
            return color
    
    # If all colors are taken, return the first one (fallback)
    return AVAILABLE_COLORS[0] if AVAILABLE_COLORS else "white"


def get_username_color(username: str, config_username: str) -> Tuple[str, Optional[str]]:
    """
    Get the color assignment for a username.
    
    Args:
        username: The username to get color for
        config_username: The current user's username (gets special treatment)
    
    Returns:
        Tuple of (foreground_color, background_color)
        - Own username: ("black", "green") 
        - Other users: (assigned_color, None)
    """
    # Special handling for own username
    if username == config_username:
        return ("black", "green")
    
    # Get current assignments
    assignments = _get_color_assignments()
    
    # If user already has a color assigned, return it
    if username in assignments:
        assigned_color = assignments[username]
        # Validate the color is still in our palette
        if assigned_color in AVAILABLE_COLORS:
            return (assigned_color, None)
    
    # Need to assign a new color
    assigned_colors = set(assignments.values())
    
    # Try to use hash-based selection first
    username_hash = _hash_username(username)
    preferred_index = username_hash % len(AVAILABLE_COLORS)
    preferred_color = AVAILABLE_COLORS[preferred_index]
    
    # Use preferred color if available, otherwise find next available
    if preferred_color not in assigned_colors:
        new_color = preferred_color
    else:
        new_color = _find_available_color(assigned_colors)
    
    # Save the new assignment
    assignments[username] = new_color
    _save_color_assignments(assignments)
    
    return (new_color, None)


def reset_color_assignments() -> None:
    """
    Clear all color assignments. Useful for testing or resetting the system.
    """
    config_set("user-colors", "assignments", "{}")


def get_all_color_assignments() -> dict:
    """
    Get all current color assignments for debugging/inspection.
    """
    return _get_color_assignments()


def preassign_username_color(username: str, color: str) -> bool:
    """
    Manually assign a specific color to a username.
    
    Args:
        username: Username to assign color to
        color: Color name to assign (must be in AVAILABLE_COLORS)
    
    Returns:
        True if assignment was successful, False if color is invalid
    """
    if color not in AVAILABLE_COLORS:
        return False
    
    assignments = _get_color_assignments()
    assignments[username] = color
    _save_color_assignments(assignments)
    return True


def get_color_stats() -> dict:
    """
    Get statistics about color usage for monitoring and debugging.
    """
    assignments = _get_color_assignments()
    assigned_colors = list(assignments.values())
    
    return {
        "total_users": len(assignments),
        "colors_used": len(set(assigned_colors)),
        "colors_available": len(AVAILABLE_COLORS),
        "most_common_colors": [
            (color, assigned_colors.count(color)) 
            for color in set(assigned_colors)
        ],
        "unused_colors": [
            color for color in AVAILABLE_COLORS 
            if color not in assigned_colors
        ]
    }