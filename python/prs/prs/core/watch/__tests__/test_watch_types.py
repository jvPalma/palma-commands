"""
Unit tests for watch_types module.
"""

import pytest
from datetime import datetime

from ..watch_types import ModeChangeCommand, ChangeType, WatchConfig, PRSnapshot, Change, ChangeSet, WatchState


class TestModeChangeCommand:
    """Test cases for ModeChangeCommand dataclass."""
    
    def test_mode_change_command_creation(self):
        """Test creating a ModeChangeCommand."""
        timestamp = datetime.now().isoformat()
        command = ModeChangeCommand(
            feature="checks",
            new_mode="long",
            timestamp=timestamp
        )
        
        assert command.feature == "checks"
        assert command.new_mode == "long"
        assert command.timestamp == timestamp
    
    def test_mode_change_command_equality(self):
        """Test ModeChangeCommand equality comparison."""
        timestamp = "2024-01-01T12:00:00"
        
        command1 = ModeChangeCommand("checks", "long", timestamp)
        command2 = ModeChangeCommand("checks", "long", timestamp)
        command3 = ModeChangeCommand("reviews", "long", timestamp)
        
        assert command1 == command2
        assert command1 != command3
    
    def test_mode_change_command_valid_features(self):
        """Test ModeChangeCommand with valid feature names."""
        valid_features = ["checks", "reviews", "labels"]
        timestamp = datetime.now().isoformat()
        
        for feature in valid_features:
            command = ModeChangeCommand(feature, "normal", timestamp)
            assert command.feature == feature
    
    def test_mode_change_command_valid_modes(self):
        """Test ModeChangeCommand with valid mode names."""
        valid_modes = ["none", "short", "normal", "long"]
        timestamp = datetime.now().isoformat()
        
        for mode in valid_modes:
            command = ModeChangeCommand("checks", mode, timestamp)
            assert command.new_mode == mode


class TestExistingTypes:
    """Test cases for existing watch types to ensure they still work."""
    
    def test_change_type_enum(self):
        """Test ChangeType enum values."""
        assert ChangeType.NEW_PR.value == "new_pr"
        assert ChangeType.STATUS_CHANGE.value == "status_change"
        assert ChangeType.CHECKS_CHANGE.value == "checks_change"
        assert ChangeType.REVIEWS_CHANGE.value == "reviews_change"
        assert ChangeType.LABELS_CHANGE.value == "labels_change"
        assert ChangeType.PR_CLOSED.value == "pr_closed"
        assert ChangeType.PR_MERGED.value == "pr_merged"
    
    def test_watch_config_defaults(self):
        """Test WatchConfig default values."""
        config = WatchConfig()
        
        assert config.interval == 30
        assert config.show_update_time == True
        assert config.highlight_changes == True
        assert config.max_cache_size == 1000
    
    def test_watch_config_custom_values(self):
        """Test WatchConfig with custom values."""
        config = WatchConfig(
            interval=60,
            show_update_time=False,
            highlight_changes=False,
            max_cache_size=500
        )
        
        assert config.interval == 60
        assert config.show_update_time == False
        assert config.highlight_changes == False
        assert config.max_cache_size == 500
    
    def test_change_named_tuple(self):
        """Test Change named tuple creation."""
        change = Change(
            pr_id="123",
            change_type=ChangeType.STATUS_CHANGE,
            old_value="OPEN",
            new_value="CLOSED",
            description="PR was closed"
        )
        
        assert change.pr_id == "123"
        assert change.change_type == ChangeType.STATUS_CHANGE
        assert change.old_value == "OPEN"
        assert change.new_value == "CLOSED"
        assert change.description == "PR was closed"
    
    def test_change_set_creation(self):
        """Test ChangeSet creation and methods."""
        changes = [
            Change("123", ChangeType.STATUS_CHANGE, "OPEN", "CLOSED", "Closed")
        ]
        
        changeset = ChangeSet(
            changes=changes,
            new_prs=["456"],
            removed_prs=["789"],
            timestamp="2024-01-01T12:00:00"
        )
        
        assert changeset.changes == changes
        assert changeset.new_prs == ["456"]
        assert changeset.removed_prs == ["789"]
        assert changeset.timestamp == "2024-01-01T12:00:00"
    
    def test_change_set_has_changes(self):
        """Test ChangeSet.has_changes() method."""
        # Empty changeset
        empty_changeset = ChangeSet([], [], [], "")
        assert not empty_changeset.has_changes()
        
        # Changeset with changes
        changes = [Change("123", ChangeType.STATUS_CHANGE, "OLD", "NEW", "Changed")]
        changeset_with_changes = ChangeSet(changes, [], [], "")
        assert changeset_with_changes.has_changes()
        
        # Changeset with new PRs
        changeset_with_new = ChangeSet([], ["456"], [], "")
        assert changeset_with_new.has_changes()
        
        # Changeset with removed PRs
        changeset_with_removed = ChangeSet([], [], ["789"], "")
        assert changeset_with_removed.has_changes()
    
    def test_change_set_get_changed_pr_ids(self):
        """Test ChangeSet.get_changed_pr_ids() method."""
        changes = [
            Change("123", ChangeType.STATUS_CHANGE, "OLD", "NEW", "Changed"),
            Change("456", ChangeType.CHECKS_CHANGE, "OLD", "NEW", "Changed")
        ]
        
        changeset = ChangeSet(
            changes=changes,
            new_prs=["789", "101"],
            removed_prs=[],
            timestamp=""
        )
        
        changed_ids = changeset.get_changed_pr_ids()
        expected_ids = {"123", "456", "789", "101"}
        
        assert changed_ids == expected_ids
    
    def test_watch_state_defaults(self):
        """Test WatchState default values."""
        state = WatchState()
        
        assert state.is_running == False
        assert state.update_count == 0
        assert state.last_update is None
        assert state.last_error is None
        assert state.connection_status == "disconnected"
    
    def test_watch_state_custom_values(self):
        """Test WatchState with custom values."""
        state = WatchState(
            is_running=True,
            update_count=5,
            last_update="2024-01-01T12:00:00",
            last_error="Connection failed",
            connection_status="error"
        )
        
        assert state.is_running == True
        assert state.update_count == 5
        assert state.last_update == "2024-01-01T12:00:00"
        assert state.last_error == "Connection failed"
        assert state.connection_status == "error"