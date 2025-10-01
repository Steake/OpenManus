import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from textual.app import App, ComposeResult, on
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical
    from textual.message import Message
    from textual.reactive import reactive
    from textual.widgets import (
        Button,
        Footer,
        Header,
        Input,
        Label,
        ListItem,
        ListView,
        NumberInput,
        OptionList,
        RichLog,
        Static,
        TabbedContent,
        TabPane,
        TextArea,
    )
except ImportError:
    pytest.skip("Textual not installed for TUI tests", allow_module_level=True)

from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow
from app.modes.python_mode.python_tool import PythonTool
from app.modes.python_mode.tui import OutputUpdate, PythonTUI
from app.tool.base import ToolResult


@pytest.mark.asyncio
class TestPythonTUI:
    """Integration tests for PythonTUI components."""

    @pytest.fixture
    def mock_app(self):
        """Mock Textual App and components."""
        mock_app = MagicMock()
        mock_app.query_one = MagicMock(
            side_effect=lambda cls, id=None: {
                "script-input": MagicMock(text="print('tui test')"),
                "agent-input": MagicMock(text="agent script"),
                "flow-input": MagicMock(value="flow task"),
                "timeout-input": MagicMock(value=20),
                TabbedContent: MagicMock(active="tool"),
                RichLog: MagicMock(),
                TextArea: MagicMock(),
                Input: MagicMock(),
                NumberInput: MagicMock(),
                Button: MagicMock(),
            }
        )
        mock_app.post_message = MagicMock()
        mock_app.notify = MagicMock()
        mock_app.styles = MagicMock(
            get=MagicMock(
                return_value=MagicMock(get=MagicMock(return_value=MagicMock()))
            )
        )
        return mock_app

    @pytest.fixture
    def tui(self, mock_app):
        """Fixture for PythonTUI with mocked dependencies."""
        with patch("textual.app.App", return_value=mock_app):
            tui = PythonTUI()
            tui.agent = MagicMock(spec=PythonAgent)
            tui.agent.step = AsyncMock(return_value="TUI agent result")
            tui.agent.update_memory = MagicMock()
            tui.tool = MagicMock(spec=PythonTool)
            tui.tool.execute = AsyncMock(
                return_value=ToolResult(output="TUI tool output")
            )
            tui.flow = MagicMock(spec=PythonFlow)
            tui.flow.execute = AsyncMock(return_value="TUI flow result")
            tui.load_plugins = MagicMock()
            tui.active_plugins = ["example"]
            return tui

    @pytest.mark.asyncio
    async def test_tui_init_and_compose(self, tui):
        """Test TUI initialization and compose method."""
        # Mock compose to avoid actual UI creation
        with patch.object(tui, "compose", return_value=[]):
            tui.on_mount()

        assert tui.current_mode == "tool"
        assert tui.timeout == 30
        assert (
            tui.script_code
            == "# Enter your Python script here\nprint('Hello, Python Mode!')"
        )
        tui.load_plugins.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_tool_mode(self, tui, mock_app):
        """Test execute_action in tool mode: handles script input, plugins, timeout."""
        mock_app.query_one.side_effect = lambda cls, id=None: {
            "script-input": MagicMock(text="print('tool mode')"),
            TabbedContent: MagicMock(active="tool"),
            RichLog: MagicMock(id="output"),
        }[id or cls.__name__]

        await tui.execute_action()

        tui.tool.execute.assert_called_with(
            code="print('tool mode')",
            plugins=["example"],
            timeout=30,
            generate_image=False,
        )
        tui.post_message.assert_called_with(OutputUpdate("TUI tool output"))

    @pytest.mark.asyncio
    async def test_execute_action_agent_mode(self, tui, mock_app):
        """Test execute_action in agent mode: updates memory and calls step."""
        mock_app.query_one.side_effect = lambda cls, id=None: {
            "agent-input": MagicMock(text="agent script"),
            TabbedContent: MagicMock(active="agent"),
        }[id or cls.__name__]

        await tui.execute_action()

        tui.agent.update_memory.assert_called_with("user", "agent script")
        tui.agent.step.assert_called_once()
        tui.post_message.assert_called_with(
            OutputUpdate("Agent Step Result: TUI agent result")
        )

    @pytest.mark.asyncio
    async def test_execute_action_flow_mode(self, tui, mock_app):
        """Test execute_action in flow mode: calls flow execute."""
        mock_app.query_one.side_effect = lambda cls, id=None: {
            "flow-input": MagicMock(value="flow task"),
            TabbedContent: MagicMock(active="flow"),
        }[id or cls.__name__]

        await tui.execute_action()

        tui.flow.execute.assert_called_with("flow task")
        tui.post_message.assert_called_with(
            OutputUpdate("Flow Result: TUI flow result")
        )

    @pytest.mark.asyncio
    async def test_execute_action_invalid_mode(self, tui, mock_app):
        """Test execute_action in invalid mode."""
        mock_app.query_one.return_value = MagicMock(active="invalid")

        await tui.execute_action()

        tui.post_message.assert_called_with(OutputUpdate("Invalid mode selected."))

    @pytest.mark.asyncio
    async def test_execute_action_with_error(self, tui, mock_app):
        """Test execute_action handles exceptions with error display."""
        mock_app.query_one.side_effect = lambda cls, id=None: {
            TabbedContent: MagicMock(active="tool"),
            "script-input": MagicMock(text="error script"),
            RichLog: MagicMock(id="output"),
        }[id or cls.__name__]
        tui.tool.execute = AsyncMock(side_effect=Exception("TUI execution error"))

        await tui.execute_action()

        tui.post_message.assert_called_with(
            OutputUpdate("Execution Error: TUI execution error", is_error=True)
        )

    @pytest.mark.asyncio
    async def test_update_output_success(self, tui):
        """Test _update_output for successful content."""
        mock_output = MagicMock()
        with patch.object(tui, "query_one", return_value=mock_output):
            await tui._update_output("Success message")

        mock_output.write.assert_called_with("Success message")
        mock_output.scroll_end.assert_called_with(animate=False)

    @pytest.mark.asyncio
    async def test_update_output_error(self, tui):
        """Test _update_output for error content with red markup."""
        mock_output = MagicMock()
        with patch.object(tui, "query_one", return_value=mock_output), patch.object(
            tui.app, "styles"
        ) as mock_styles:
            mock_styles.get.return_value.get.return_value = MagicMock(color="red")
            await tui._update_output("Error message")

        mock_output.write.assert_called_with("[red]Error message[/red]")
        mock_output.scroll_end.assert_called_with(animate=False)

    @pytest.mark.asyncio
    async def test_format_result_success(self, tui):
        """Test _format_result for successful ToolResult."""
        result = ToolResult(output="Formatted output", base64_image=None)
        formatted = tui._format_result(result)

        assert formatted == "Formatted output"

    @pytest.mark.asyncio
    async def test_format_result_error(self, tui):
        """Test _format_result for ToolResult with error."""
        result = ToolResult(error="Format error")
        formatted = tui._format_result(result)

        assert "[red]Error: Format error[/red]" == formatted

    @pytest.mark.asyncio
    async def test_format_result_with_image(self, tui):
        """Test _format_result for ToolResult with base64 image."""
        result = ToolResult(
            output="Output with image", base64_image="data:image/png;base64,abc123..."
        )
        formatted = tui._format_result(result)

        assert "Output with image" in formatted
        assert (
            "Image generated (base64 preview): data:image/png;base64,abc123..."
            in formatted
        )

    def test_update_timeout(self, tui):
        """Test update_timeout from NumberInput."""
        event = MagicMock(value=15)
        tui.update_timeout(event)

        assert tui.timeout == 15

    def test_clear_output(self, tui):
        """Test clear_output clears RichLog."""
        mock_output = MagicMock()
        with patch.object(tui, "query_one", return_value=mock_output):
            tui.clear_output()

        mock_output.clear.assert_called_once()

    def test_reload_plugins(self, tui):
        """Test reload_plugins reloads and updates lists."""
        mock_list_view = MagicMock()
        with patch.object(tui, "query", return_value=[mock_list_view]):
            tui.reload_plugins()

        tui.load_plugins.assert_called_once()
        mock_list_view.clear.assert_called_once()
        for plugin in ["example"]:
            mock_list_view.append.assert_any_call(MagicMock(Label=plugin))
        tui.notify.assert_called_with(
            "Plugins reloaded", title="Success", severity="information"
        )

    @pytest.mark.asyncio
    async def test_on_output_update(self, tui):
        """Test on_output_update handles message and sets bell for errors."""
        message = OutputUpdate(content="Update content", is_error=True)
        tui.on_output_update(message)

        assert tui.output_content == "Update content"
        assert tui.bell == "error"

        # Reset and test non-error
        tui.bell = None
        message.is_error = False
        tui.on_output_update(message)

        assert tui.bell is None

    def test_action_execute_binding(self, tui):
        """Test action_execute binding creates async task."""
        with patch("asyncio.create_task") as mock_create:
            tui.action_execute()

        mock_create.assert_called_with(tui.execute_action())

    def test_action_quit_binding(self, tui):
        """Test action_quit binding calls exit."""
        with patch.object(tui, "exit") as mock_exit:
            tui.action_quit()

        mock_exit.assert_called_once()
