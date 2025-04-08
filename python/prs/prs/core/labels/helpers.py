from prs.core.models import PullRequest
from prs.utils.formatting import color_text

# Define the label category lists
DANG_LIST = ["skip-ci", "conflict", "do-not-merge", "no-reviewers"]
WARN_LIST = ["force-ci", "ignore-fe-cache", "skip-second-review"]
GOOD_LIST = [
    "ready-after-ci",
    "ready-to-merge",
    "deploy-pr-backoffice",
    "deploy-pr-frontoffice",
]


def analyze_labels(pr: PullRequest):
    """
    Analyzes the labels on the given PR.

    Returns a list of tuples (label, color), where the color is determined by:
      - "red" if the label is in DANG_LIST
      - "yellow" if the label is in WARN_LIST
      - "green" if the label is in GOOD_LIST
      - "brblack" otherwise.
    """
    details = []
    for label in pr.labels:
        if label in DANG_LIST:
            color = "brred"
        elif label in WARN_LIST:
            color = "yellow"
        elif label in GOOD_LIST:
            color = "green"
        else:
            color = "brblack"
        details.append((label, color))
    return details


def get_labels(pr: PullRequest, mode: str) -> str:
    """
    Formats the PR labels based on the provided mode.

    Modes:
      - "none": returns an empty string.
      - "short" or "normal": returns a comma-separated list of colored labels.
      - "long": returns each colored label on its own line (with indent).

    If there are no labels, returns a message in "brblack" color.

    Raises:
      ValueError: if an unknown mode is provided.
    """
    if mode == "none":
        return ""
    details = analyze_labels(pr)

    if not details:
        result = color_text("No relevant labels to show", "brblack")
    else:
        if mode == "short":
            if not details:
                return color_text("[LABL]", "brblack")
            label, color = details[0]
            return color_text("[LABL]", color)
        elif mode == "normal":
            result = ", ".join(
                [
                    color_text(label, color)
                    for label, color in details
                    if color != "brblack"
                ]
            )
        elif mode == "long":
            result = "\n\t\t".join(
                [color_text(label, color) for label, color in details]
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
    return result
