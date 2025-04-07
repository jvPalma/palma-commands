from prs.config import get
from prs.utils.formatting import color_text, color_text_bg

# Global mapping and candidate colors for non‑own users
AUTHOR_COLOR_MAP = {}
CANDIDATE_COLORS = [
    "brgreen",
    "bryellow",
    "brcyan",
    "brmagenta",
    "brwhite",
    "brblack",
    "brred",
    "yellow",
    "cyan",
    "blue",
    "magenta",
    "green",
    "white",
    "red",
    "gray-1",
]


def get_author_color(username: str, config_username: str):
    """
    Returns a tuple (fg, bg) for the given username.
    For the own user, returns ("black", "green") to indicate black text on green background.
    For other users, assigns a candidate foreground color (with no background) in round-robin fashion.
    """
    if username == config_username:
        return ("black", "green")
    else:
        if username not in AUTHOR_COLOR_MAP:
            # Assign the next candidate color in order.
            candidate = CANDIDATE_COLORS[len(AUTHOR_COLOR_MAP) % len(CANDIDATE_COLORS)]
            AUTHOR_COLOR_MAP[username] = (candidate, None)
        return AUTHOR_COLOR_MAP[username]


def compute_author_status(pr):
    """
    Returns the formatted username using unique colors.
    Own user: black text on green background.
    Others: colored with their assigned unique foreground color.
    """
    config_username = get("git", "username")
    user = pr.author
    fg, bg = get_author_color(user, config_username)
    if bg:
        return color_text_bg(user, fg, bg)
    else:
        return color_text(user, fg)


def get_author(pr, mode: str) -> str:
    # mode "none" returns an empty string,
    # mode "any other value" return the username,

    if mode == "none":
        return ""
    elif mode == "short":
        return compute_author_status(pr)
    else:
        return compute_author_status(pr)
