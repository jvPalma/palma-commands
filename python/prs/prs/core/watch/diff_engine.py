"""
Diff Engine for detecting and categorizing changes between PR states.
"""

from typing import List, Dict, Set
from .watch_types import ChangeSet, Change, ChangeType, PRSnapshot


class DiffEngine:
    """
    Advanced diff engine for detecting changes between PR snapshots.
    
    Provides intelligent change categorization and detailed analysis.
    """
    
    def __init__(self):
        self.change_patterns = {
            'checks_improved': ['failing → passing', 'pending → success'],
            'checks_degraded': ['passing → failing', 'success → failure'],
            'review_approved': ['pending → approved', 'changes_requested → approved'],
            'review_requested_changes': ['approved → changes_requested', 'pending → changes_requested'],
        }
    
    def analyze_changeset(self, changeset: ChangeSet) -> Dict[str, any]:
        """
        Analyze a changeset to provide insights about the changes.
        
        Returns a dictionary with analysis results.
        """
        analysis = {
            'total_changes': len(changeset.changes),
            'new_prs_count': len(changeset.new_prs),
            'removed_prs_count': len(changeset.removed_prs),
            'change_types': {},
            'severity': 'low',
            'summary': '',
            'highlights': []
        }
        
        # Count changes by type
        for change in changeset.changes:
            change_type = change.change_type.value
            analysis['change_types'][change_type] = analysis['change_types'].get(change_type, 0) + 1
        
        # Determine severity
        analysis['severity'] = self._determine_severity(changeset)
        
        # Generate summary
        analysis['summary'] = self._generate_summary(changeset, analysis)
        
        # Generate highlights
        analysis['highlights'] = self._generate_highlights(changeset)
        
        return analysis
    
    def _determine_severity(self, changeset: ChangeSet) -> str:
        """Determine the overall severity of changes."""
        if changeset.removed_prs or len(changeset.new_prs) > 3:
            return 'high'
        
        # Check for significant status changes
        for change in changeset.changes:
            if change.change_type in [ChangeType.STATUS_CHANGE, ChangeType.CHECKS_CHANGE]:
                if 'fail' in change.new_value.lower() or 'error' in change.new_value.lower():
                    return 'high'
        
        if len(changeset.changes) > 5 or len(changeset.new_prs) > 1:
            return 'medium'
        
        return 'low'
    
    def _generate_summary(self, changeset: ChangeSet, analysis: Dict) -> str:
        """Generate a human-readable summary of changes."""
        parts = []
        
        if changeset.new_prs:
            parts.append(f"{len(changeset.new_prs)} new PR{'s' if len(changeset.new_prs) > 1 else ''}")
        
        if changeset.removed_prs:
            parts.append(f"{len(changeset.removed_prs)} PR{'s' if len(changeset.removed_prs) > 1 else ''} closed/merged")
        
        if changeset.changes:
            parts.append(f"{len(changeset.changes)} update{'s' if len(changeset.changes) > 1 else ''}")
        
        if not parts:
            return "No changes detected"
        
        return " • ".join(parts)
    
    def _generate_highlights(self, changeset: ChangeSet) -> List[str]:
        """Generate list of notable highlights."""
        highlights = []
        
        # Highlight new PRs
        if changeset.new_prs:
            if len(changeset.new_prs) == 1:
                highlights.append(f"New PR: #{changeset.new_prs[0]}")
            else:
                highlights.append(f"New PRs: {', '.join(f'#{pr_id}' for pr_id in changeset.new_prs[:3])}")
        
        # Highlight important changes
        for change in changeset.changes:
            if change.change_type == ChangeType.CHECKS_CHANGE:
                if 'success' in change.new_value.lower() and 'fail' in change.old_value.lower():
                    highlights.append(f"PR #{change.pr_id}: Checks now passing! ✅")
                elif 'fail' in change.new_value.lower():
                    highlights.append(f"PR #{change.pr_id}: Checks failing ❌")
            
            elif change.change_type == ChangeType.REVIEWS_CHANGE:
                if 'approved' in change.new_value.lower():
                    highlights.append(f"PR #{change.pr_id}: Got approval! 👍")
                elif 'changes_requested' in change.new_value.lower():
                    highlights.append(f"PR #{change.pr_id}: Changes requested 📝")
        
        return highlights[:5]  # Limit to 5 highlights
    
    def get_changed_pr_ids_by_type(self, changeset: ChangeSet, change_type: ChangeType) -> Set[str]:
        """Get PR IDs that have changes of a specific type."""
        return {
            change.pr_id for change in changeset.changes 
            if change.change_type == change_type
        }
    
    def filter_changes_by_severity(self, changes: List[Change], min_severity: str = 'low') -> List[Change]:
        """Filter changes based on severity level."""
        severity_order = {'low': 0, 'medium': 1, 'high': 2}
        min_level = severity_order.get(min_severity, 0)
        
        filtered_changes = []
        for change in changes:
            change_severity = self._assess_change_severity(change)
            if severity_order.get(change_severity, 0) >= min_level:
                filtered_changes.append(change)
        
        return filtered_changes
    
    def _assess_change_severity(self, change: Change) -> str:
        """Assess the severity of a single change."""
        if change.change_type == ChangeType.STATUS_CHANGE:
            if 'closed' in change.new_value.lower() or 'merged' in change.new_value.lower():
                return 'high'
        
        if change.change_type == ChangeType.CHECKS_CHANGE:
            if 'fail' in change.new_value.lower() or 'error' in change.new_value.lower():
                return 'high'
            elif 'success' in change.new_value.lower() and 'fail' in change.old_value.lower():
                return 'medium'
        
        if change.change_type == ChangeType.REVIEWS_CHANGE:
            if 'approved' in change.new_value.lower():
                return 'medium'
            elif 'changes_requested' in change.new_value.lower():
                return 'medium'
        
        return 'low'