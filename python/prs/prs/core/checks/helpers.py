from prs.utils.formatting import color_text

from prs.core.models import PullRequest


def analyze_checks(pr: PullRequest):
    """
    Analyzes the checks on the given PR.
    Returns a tuple:
      (total, success_count, pending_count, failing_count, details)
    where details is a list of tuples (state, context, color)
    for each check with a non-empty context.
    """
    total = 0
    success_count = 0
    pending_count = 0
    failing_count = 0
    details = []
    for check in pr.checks:
        state = check.get("state", "").upper()
        context = check.get("context", "")
        if state:
            total += 1
            if state == "SUCCESS":
                success_count += 1
            elif state in ["FAILURE", "FAILED"]:
                failing_count += 1
            elif state == "PENDING":
                pending_count += 1
            if state and context:
                if state in ["FAILURE", "FAILED"]:
                    color = "red"
                elif state == "PENDING":
                    color = "yellow"
                else:
                    color = "green"
                details.append((state, context, color))
    return total, success_count, pending_count, failing_count, details


def get_checks(pr: PullRequest, mode: str):
    """
    Formats the PR checks based on the mode.

    Modes:
      - "none": returns an empty string.
      - "short": returns a tuple (label, color) for a summary.
         * If no checks, returns ("CHKS", "yellow").
         * If any failure exists, returns ("CHKS", "red").
         * Else if any pending exists, returns ("CHKS", "yellow").
         * Otherwise, returns ("CHKS", "green").
      - "normal": returns a colored short summary string.
         * For example, "ALL TESTS PASSED" in green, or "FAILURE #N" in red.
      - "long": returns detailed output, with each check on its own line.

    Raises:
      ValueError: if an unknown mode is provided.
    """
    total, success_count, pending_count, failing_count, details = analyze_checks(pr)

    if mode == "none":
        return ""
    elif mode == "short":
        if total == 0:
            return color_text("[CHKS]", "yellow")
        if failing_count > 0:
            return color_text("[CHKS]", "red")
        elif pending_count > 0:
            return color_text("[CHKS]", "yellow")
        else:
            return color_text("[CHKS]", "green")
    elif mode == "normal":
        if total == success_count:
            return color_text("ALL TESTS PASSED", "green")
        elif failing_count > 0:
            return color_text(f"FAILURE #{failing_count}", "red")
        elif pending_count > 0:
            return color_text(f"PENDING #{pending_count}", "yellow")
        else:
            return color_text("ALL TESTS PASSED", "green")
    elif mode == "long":
        if details:
            return "\n\t\t".join(
                [
                    f"{color_text(state.ljust(14), color)} {context}"
                    for state, context, color in details
                ]
            )
        else:
            return "No checks available"
    else:
        raise ValueError(f"Unknown mode: {mode}")
