import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from prs.core.models import PullRequest


def generate_default_filename() -> str:
    """Generate a default filename with timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"prs_export_{timestamp}.json"


def export_pull_requests(
    pull_requests: List[PullRequest],
    ignored_prs: set,
    filters: dict,
    filename: Optional[str] = None
) -> None:
    """
    Export pull requests to a JSON file.
    
    Args:
        pull_requests: List of PullRequest objects to export
        ignored_prs: Set of PR IDs that are marked as ignored
        filters: Dictionary of filters applied during PR fetching
        filename: Optional filename for export (default: auto-generated)
    """
    # Determine output filename
    if filename is None or filename == "default":
        output_file = generate_default_filename()
    else:
        output_file = filename
    
    # Prepare PR data for export
    output_prs = []
    for pr in pull_requests:
        # Start with raw API data if available, otherwise create from model
        if pr.raw_data:
            pr_data = pr.raw_data.copy()
        else:
            # Fallback: construct from model fields
            pr_data = {
                "number": pr.id,
                "title": pr.title,
                "author": {"login": pr.author},
                "labels": [{"name": label} for label in pr.labels],
                "statusCheckRollup": pr.checks,
                "reviews": pr.reviews,
                "reviewRequests": pr.review_requests,
                "url": pr.url,
                "headRefName": pr.branch,
                "isDraft": pr.is_draft,
            }
        
        # Add our application-specific metadata
        pr_data["_metadata"] = {
            "ignored": pr.id in ignored_prs,
            "source": pr.source if pr.source else "unknown",
            "role": pr.role if pr.role else "unknown"
        }
        
        output_prs.append(pr_data)
    
    # Construct the final export object
    export_content = {
        "metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "filters": filters,
            "total_count": len(pull_requests),
            "ignored_count": sum(1 for pr in pull_requests if pr.id in ignored_prs),
            "source_breakdown": {
                "authored": sum(1 for pr in pull_requests if pr.source == "authored"),
                "reviewer_pending": sum(1 for pr in pull_requests if pr.source == "reviewer_pending"),
                "reviewer_completed": sum(1 for pr in pull_requests if pr.source == "reviewer_completed"),
                "both_pending": sum(1 for pr in pull_requests if pr.source == "both_pending"),
                "both_completed": sum(1 for pr in pull_requests if pr.source == "both_completed"),
            }
        },
        "pullRequests": output_prs
    }
    
    # Write to file with error handling
    try:
        # Create parent directory if it doesn't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_content, f, indent=2, ensure_ascii=False)
        
        # Success message to stderr (so it doesn't interfere with potential stdout)
        print(f"✅ Successfully exported {len(pull_requests)} pull requests to {output_file}", file=sys.stderr)
        if export_content["metadata"]["ignored_count"] > 0:
            print(f"   Including {export_content['metadata']['ignored_count']} ignored PRs", file=sys.stderr)
            
    except (IOError, OSError, PermissionError) as e:
        print(f"❌ Error: Could not write to file {output_file}", file=sys.stderr)
        print(f"   Reason: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during export: {e}", file=sys.stderr)
        sys.exit(1)