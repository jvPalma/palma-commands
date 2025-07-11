from prs.utils.formatting import color_text
from typing import Optional

from prs.core.models import PullRequest


def analyze_checks(pr: PullRequest):
    """
    Analyzes the checks on the given PR including GitHub Actions workflows.
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
    github_actions_checks = []
    
    for check in pr.checks:
        state = check.get("state", "").upper()
        context = check.get("context", "")
        ci_provider = check.get("ci_provider", "")
        
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
                    
                # Enhanced detail for GitHub Actions
                if ci_provider == "github_actions":
                    workflow_name = check.get("name", context.replace("github-actions/", ""))
                    run_number = check.get("run_number", "")
                    duration = check.get("duration", "")
                    
                    display_text = workflow_name
                    if run_number:
                        display_text += f" #{run_number}"
                    if duration:
                        display_text += f" ({_format_duration(duration)})"
                    
                    details.append((state, display_text, color))
                    github_actions_checks.append(check)
                else:
                    details.append((state, context, color))
    
    return total, success_count, pending_count, failing_count, details


def _format_duration(duration: Optional[int]) -> str:
    """Format duration in seconds to human-readable format."""
    if not duration:
        return "N/A"
    
    if duration < 60:
        return f"{duration}s"
    elif duration < 3600:
        minutes = duration // 60
        seconds = duration % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        return f"{hours}h {minutes}m"


def get_checks(pr: PullRequest, mode: str):
    """
    Formats the PR checks based on the mode, with enhanced GitHub Actions support.

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
    
    # Check if we have GitHub Actions data for enhanced display
    has_github_actions = any(check.get("ci_provider") == "github_actions" for check in pr.checks)
    
    if mode == "none":
        return ""
    elif mode == "short":
        if total == 0:
            return color_text("[CHKS]", "yellow")
        
        if has_github_actions:
            # Enhanced short mode for GitHub Actions
            if failing_count > 0:
                return color_text("[GHA]", "red")
            elif pending_count > 0:
                return color_text("[GHA]", "yellow")
            else:
                return color_text("[GHA]", "green")
        else:
            # Standard short mode
            if failing_count > 0:
                return color_text("[CHKS]", "red")
            elif pending_count > 0:
                return color_text("[CHKS]", "yellow")
            else:
                return color_text("[CHKS]", "green")
    elif mode == "normal":
        if has_github_actions:
            # Enhanced normal mode for GitHub Actions
            if total == success_count:
                return color_text("GITHUB ACTIONS PASSED", "green")
            elif failing_count > 0:
                return color_text(f"GHA FAILURE #{failing_count}", "red")
            elif pending_count > 0:
                return color_text(f"GHA PENDING #{pending_count}", "yellow")
            else:
                return color_text("GITHUB ACTIONS PASSED", "green")
        else:
            # Standard normal mode
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
            # Group GitHub Actions checks separately
            github_actions_details = []
            other_details = []
            
            for state, context, color in details:
                if any(check.get("ci_provider") == "github_actions" 
                      and check.get("name", "").lower() in context.lower() 
                      for check in pr.checks):
                    github_actions_details.append((state, context, color))
                else:
                    other_details.append((state, context, color))
            
            output_lines = []
            
            # Show GitHub Actions first
            if github_actions_details:
                output_lines.append(color_text("GitHub Actions:", "cyan"))
                for state, context, color in github_actions_details:
                    output_lines.append(f"  {color_text(state.ljust(12), color)} {context}")
            
            # Show other checks
            if other_details:
                if github_actions_details:
                    output_lines.append("")  # Empty line separator
                output_lines.append(color_text("Other Checks:", "cyan"))
                for state, context, color in other_details:
                    output_lines.append(f"  {color_text(state.ljust(12), color)} {context}")
            
            return "\n".join(output_lines)
        else:
            return "No checks available"
    else:
        raise ValueError(f"Unknown mode: {mode}")
