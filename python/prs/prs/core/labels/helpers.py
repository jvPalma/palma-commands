from prs.utils.formatting import color_text

DANG_LIST = ["skip-ci", "conflict", "do-not-merge", "no-reviewers"]
WARN_LIST = ["force-ci", "ignore-fe-cache", "skip-second-review"]
GOOD_LIST = [
    "ready-after-ci",
    "ready-to-merge",
    "deploy-pr-backoffice",
    "deploy-pr-frontoffice",
]


def format_labels(pr, mode: str) -> str:
    """
    Returns a formatted string for the labels.
    Mode can be "none", "short", or "long".
    For short mode, labels are displayed in one line; for long, each label is on its own line.
    """
    if mode == "none":
        return ""
    labels = pr.labels
    formatted_labels = []
    for label in labels:
        if label in DANG_LIST:
            color = "red"
        elif label in WARN_LIST:
            color = "yellow"
        elif label in GOOD_LIST:
            color = "green"
        else:
            color = "brblack"
        formatted_labels.append(color_text(label, color))
    if not formatted_labels:
        result = color_text("No relevant labels to show", "brblack")
    else:
        result = ", ".join(formatted_labels)
    if mode == "long":
        result = "\n\t\t" + "\n\t\t".join(formatted_labels)
    return result


def compute_labels_status(pr):
    for label in pr.labels:
        if label in ["skip-ci", "conflict", "do-not-merge", "no-reviewers"]:
            return "LABL", "red"
    for label in pr.labels:
        if label in [
            "ready-after-ci",
            "ready-to-merge",
            "deploy-pr-backoffice",
            "deploy-pr-frontoffice",
        ]:
            return "LABL", "green"
    return "LABL", "yellow"
