from prs.utils.formatting import color_text


def compute_checks_status(pr):
    total = 0
    success_count = 0
    pending_count = 0
    failing_count = 0
    for check in pr.checks:
        state = check.get("state", "").upper()
        if state:
            total += 1
            if state == "SUCCESS":
                success_count += 1
            elif state in ["FAILURE", "FAILED"]:
                failing_count += 1
            elif state == "PENDING":
                pending_count += 1
    if total == 0:
        return "CHKS", "yellow"
    if failing_count > 0:
        return "CHKS", "red"
    elif pending_count > 0:
        return "CHKS", "yellow"
    else:
        return "CHKS", "green"


def format_checks(pr, mode: str) -> str:
    """
    Returns a formatted string for the checks information.
    Mode can be "none", "short", or "long".
    """
    if mode == "none":
        return ""
    total = 0
    success_count = 0
    pending_count = 0
    failing_count = 0
    details = []
    for check in pr.checks:
        state = check.get("state", "").upper()
        context = check.get("context", "")
        if state and context:
            total += 1
            if state == "SUCCESS":
                success_count += 1
            elif state == "PENDING":
                pending_count += 1
            elif state in ["FAILURE", "FAILED"]:
                failing_count += 1
            if mode == "long":
                if state in ["FAILURE", "FAILED"]:
                    color = "red"
                elif state == "PENDING":
                    color = "yellow"
                else:
                    color = "green"
                details.append(f"{color_text(state.ljust(12), color)} {context}")
    if mode == "short":
        if total == success_count:
            return color_text("ALL TESTS PASSED", "green")
        elif failing_count > 0:
            return color_text(f"FAILURE #{failing_count}", "red")
        elif pending_count > 0:
            return color_text(f"PENDING #{pending_count}", "yellow")
        else:
            return color_text("ALL TESTS PASSED", "green")
    else:  # mode == "long"
        return "\n\t\t".join(details) if details else "No checks available"
