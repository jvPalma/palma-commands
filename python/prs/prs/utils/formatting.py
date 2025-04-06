# prs/utils/formatting.py

ANSI_CODES = {
    "reset": "\033[0m",  # color is: default
    "black": "\033[30m",  # color is: #000000
    "red": "\033[31m",  # color is: #800000
    "green": "\033[32m",  # color is: #008000
    "yellow": "\033[33m",  # color is: #808000
    "blue": "\033[34m",  # color is: #000080
    "magenta": "\033[35m",  # color is: #800080
    "cyan": "\033[36m",  # color is: #008080
    "white": "\033[37m",  # color is: #ffffff
    "brblack": "\033[90m",  # color is: #808080
    "brred": "\033[91m",  # color is: #ff0000
    "brgreen": "\033[92m",  # color is: #00ff00
    "bryellow": "\033[93m",  # color is: #ffff00
    "brblue": "\033[94m",  # color is: #0000ff
    "brmagenta": "\033[95m",  # color is: #ff00ff
    "brcyan": "\033[96m",  # color is: #00ffff
    "brwhite": "\033[97m",  # color is: #ffffff
    "gray-1": "\033[38;5;250m",  # color is: #d3d3d3
    "gray-2": "\033[38;5;248m",  # color is: #c0c0c0
    "gray-3": "\033[38;5;246m",  # color is: #a9a9a9
    "gray-4": "\033[38;5;244m",  # color is: #808080
    "gray-5": "\033[38;5;238m",  # color is: #555555
}


def color_text_bg(text: str, fg: str, bg: str) -> str:
    """
    Returns the given text wrapped in ANSI codes for the specified foreground and background colors.
    """
    ANSI_FG = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "brblack": "90",
        "brred": "91",
        "brgreen": "92",
        "bryellow": "93",
        "brblue": "94",
        "brmagenta": "95",
        "brcyan": "96",
        "brwhite": "97",
    }
    ANSI_BG = {
        "black": "40",
        "red": "41",
        "green": "42",
        "yellow": "43",
        "blue": "44",
        "magenta": "45",
        "cyan": "46",
        "white": "47",
        "brblack": "100",
        "brred": "101",
        "brgreen": "102",
        "bryellow": "103",
        "brblue": "104",
        "brmagenta": "105",
        "brcyan": "106",
        "brwhite": "107",
    }
    fg_code = ANSI_FG.get(fg, "")
    bg_code = ANSI_BG.get(bg, "")
    reset = "\033[0m"
    return f"\033[{fg_code};{bg_code}m{text}{reset}"


def color_text(text: str, color: str) -> str:
    """
    Wrap the given text in ANSI codes for the specified color.
    If the color is not found, return the original text.
    """
    return f"{ANSI_CODES.get(color, '')}{text}{ANSI_CODES['reset']}"


class OutputBuilder:
    """
    Helper class to build multi-line output in a structured way.
    Mimics the fish functions add_line and add_same_line.
    """

    def __init__(self):
        self.lines = []

    def add_line(self, *args, sep=" "):
        """
        Adds a new line by concatenating the arguments with a separator.
        """
        line = sep.join(str(arg) for arg in args)
        self.lines.append(line)

    def add_same_line(self, *args, sep=" "):
        """
        Appends the given text to the current (last) line.
        If no line exists, creates a new one.
        """
        text = sep.join(str(arg) for arg in args)
        if self.lines:
            self.lines[-1] += sep + text
        else:
            self.lines.append(text)

    def get_output(self) -> str:
        """
        Returns the complete accumulated output as a single string.
        """
        return "\n".join(self.lines)

    def clear(self):
        """
        Clears all accumulated output.
        """
        self.lines = []
