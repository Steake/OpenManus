from unittest.mock import MagicMock

import pytest

from app.modes.python_mode.plugins.python_actions.example_plugin import (
    process_data,
    register_actions,
)


class TestExamplePlugin:
    """Unit tests for example_plugin.py."""

    def test_process_data_basic(self):
        """Test process_data with basic input."""
        result = process_data(data="hello world", prefix="TEST:")

        assert result == "TEST: HELLO WORLD"

    def test_process_data_default_prefix(self):
        """Test process_data with default prefix."""
        result = process_data(data="default test")

        assert result == "PROCESSED: DEFAULT TEST"

    def test_process_data_extra_kwargs(self):
        """Test process_data ignores extra kwargs."""
        result = process_data(data="extra", prefix="EXTRA:", unused="ignored")

        assert result == "EXTRA: EXTRA"
        # Extra kwargs should not affect output

    def test_register_actions_returns_dict(self):
        """Test register_actions returns a dictionary of actions."""
        actions = register_actions()

        assert isinstance(actions, dict)
        assert "process_data" in actions
        assert callable(actions["process_data"])

    def test_register_actions_process_data_callable(self):
        """Test that registered process_data is callable."""
        actions = register_actions()
        process_func = actions["process_data"]

        result = process_func(data="registered test")

        assert result == "PROCESSED: REGISTERED TEST"
