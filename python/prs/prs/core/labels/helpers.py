from prs.core.models import PullRequest
from prs.utils.formatting import color_text

# Define the label category lists
DANG_LIST = ["skip-ci", "conflict", "do-not-merge"]
WARN_LIST = ["ignore-fe-cache", "skip-second-review"]
GOOD_LIST = [
    "ready-after-ci",
    "ready-to-merge",
]


def analyze_labels(pr: PullRequest):
    """
    Analyzes the labels on the given PR.

    Returns a list of tuples (label, color), where the color is determined by:
      - "red" if the label is in DANG_LIST
      - "yellow" if the label is in WARN_LIST
      - "green" if the label is in GOOD_LIST
      - "grey42" otherwise.
    """
    # create multiple lists to categorize labels
    # and in the end, return all of the lists as one, starting with the DANG_LIST
    # then WARN_LIST, GOOD_LIST, ending with the neutral labels
    errorList = []
    warnList = []
    goodList = []
    neutralList = []

    for label in pr.labels:
        if label in DANG_LIST:
            errorList.append((label, "red1"))
        elif label in WARN_LIST:
            warnList.append((label, "yellow"))
        elif label in GOOD_LIST:
            goodList.append((label, "green"))
        else:
            neutralList.append((label, "grey42"))

    # Return all categorized labels as a single list
    return errorList + goodList + warnList + neutralList


def get_labels(pr: PullRequest, mode: str) -> str:
    """
    Formats the PR labels based on the provided mode.

    Modes:
      - "none": returns an empty string.
      - "short" or "normal": returns a comma-separated list of colored labels.
      - "long": returns each colored label on its own line (with indent).

    If there are no labels, returns a message in "grey42" color.

    Raises:
      ValueError: if an unknown mode is provided.
    """
    if mode == "none":
        return ""
    details = analyze_labels(pr)

    if not details:
        result = color_text("No relevant labels to show", "grey42")
    else:
        if mode == "short":
            if not details:
                return color_text("Label", "grey42")
            label, color = details[0]
            return color_text("Label", color)
        elif mode == "normal":
            result = ", ".join(
                [
                    color_text(label, color)
                    for label, color in details
                    if color != "grey42"
                ]
            )
        elif mode == "long":
            result = "\n\t\t".join(
                [color_text(label, color) for label, color in details]
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
    return result
