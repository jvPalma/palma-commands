#!/usr/bin/env python3
"""
Example usage of the new PRS columnar layout system.

This script demonstrates how to use the new layout system with sample data.
"""

from prs.core.models import PullRequest
from prs.core.layout import (
    build_pr_display,
    build_multiple_prs_display,
    build_compact_display,
    build_detailed_display,
    print_pr_display,
    get_display_preview
)


def create_sample_pr() -> PullRequest:
    """Create a sample PR with realistic data for testing."""
    return PullRequest(
        id=123456,
        title="Add new columnar layout system for enhanced PR display with responsive design",
        author="joaopalma", 
        labels=["enhancement", "ui-improvement", "ready-to-merge"],
        checks=[
            {"state": "SUCCESS", "context": "ci/github-actions"},
            {"state": "SUCCESS", "context": "ci/lint"}, 
            {"state": "PENDING", "context": "ci/security-scan"}
        ],
        reviews=[
            {"state": "APPROVED", "author": {"login": "reviewer1"}},
            {"state": "COMMENTED", "author": {"login": "reviewer2"}}
        ],
        comments=[
            {"author": {"login": "joaopalma"}, "body": "Updated the layout system to support responsive columns", "createdAt": "2024-01-15T10:30:00Z"},
            {"author": {"login": "reviewer1"}, "body": "Looks great! The columnar approach will make PRs much easier to scan.", "createdAt": "2024-01-15T14:45:00Z"}
        ],
        url="https://github.com/jvPalma/prs/pull/123456",
        branch="feature/columnar-layout",
        is_draft=False,
        additions=245,
        deletions=67,
        changed_files=8,
        created_at="2024-01-15T09:00:00Z",
        updated_at="2024-01-15T15:30:00Z"
    )


def create_draft_pr() -> PullRequest:
    """Create a sample draft PR."""
    return PullRequest(
        id=789012,
        title="Work in progress: refactor authentication system",
        author="contributor",
        labels=["wip", "security"],
        checks=[],
        reviews=[],
        comments=[],
        url="https://github.com/jvPalma/prs/pull/789012", 
        branch="draft/auth-refactor",
        is_draft=True,
        additions=89,
        deletions=134,
        changed_files=12
    )


def demo_single_pr():
    """Demonstrate single PR display."""
    print("=" * 80)
    print("SINGLE PR DISPLAY DEMO")
    print("=" * 80)
    
    pr = create_sample_pr()
    
    print("\n1. Standard Display:")
    print("-" * 40)
    display_text = build_pr_display(pr)
    print(display_text)
    
    print("\n2. Compact Display (Lines 1-2 only):")
    print("-" * 40)
    compact_text = build_compact_display(pr)
    print(compact_text)
    
    print("\n3. Detailed Display (Maximum columns):")
    print("-" * 40) 
    detailed_text = build_detailed_display(pr)
    print(detailed_text)


def demo_multiple_prs():
    """Demonstrate multiple PRs display."""
    print("\n\n" + "=" * 80)
    print("MULTIPLE PRS DISPLAY DEMO")
    print("=" * 80)
    
    prs = [create_sample_pr(), create_draft_pr()]
    
    display_text = build_multiple_prs_display(prs)
    print(display_text)


def demo_width_preview():
    """Demonstrate width preview functionality."""
    print("\n\n" + "=" * 80)
    print("WIDTH PREVIEW DEMO")
    print("=" * 80)
    
    pr = create_sample_pr()
    
    for width in [60, 80, 120]:
        print(f"\nPreview at {width} columns:")
        print("-" * width)
        preview = get_display_preview(pr, width)
        print(preview)


def demo_console_printing():
    """Demonstrate direct console printing."""
    print("\n\n" + "=" * 80) 
    print("CONSOLE PRINTING DEMO")
    print("=" * 80)
    
    pr = create_sample_pr()
    
    print("\nDirect console printing:")
    print("-" * 40)
    print_pr_display(pr)


if __name__ == "__main__":
    demo_single_pr()
    demo_multiple_prs()
    demo_width_preview() 
    demo_console_printing()
    
    print("\n\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nThe new columnar layout system provides:")
    print("• Responsive design that adapts to terminal width")
    print("• Rich text formatting with colors and emojis")
    print("• Structured information display with proper alignment")
    print("• Graceful overflow handling with truncation")
    print("• Support for multiple display modes (compact, standard, detailed)")
    print("• Easy integration with existing PRS codebase")