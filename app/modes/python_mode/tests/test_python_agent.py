import ast
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.base import BaseAgent
from app.modes.python_mode.python_agent import PythonAgent
from app.schema import Message
from app.tool.base import ToolResult
from app.tool.tool_collection import ToolCollection


@pytest.mark.asyncio
class TestPythonAgent:
    """Unit tests for PythonAgent."""

    @pytest.fixture
    def agent(self):
        """Fixture for a basic PythonAgent instance."""
        agent = PythonAgent(name="test_agent")
        agent.memory = MagicMock()  # Mock memory for update_memory
        agent.memory.get_recent_messages.return_value = [
            Message(role="user", content="print('hello')")
        ]
        return agent

    def test_inheritance_from_base_agent(self):
        """Test that PythonAgent inherits from BaseAgent."""
        assert issubclass(PythonAgent, BaseAgent)
        agent = PythonAgent(name="test")
        assert isinstance(agent, BaseAgent)

    @pytest.mark.asyncio
    async def test_step_valid_script(self, agent):
        """Test async step() with valid script: executes and returns output."""
        # Mock _execute_script_async to return successful ToolResult
        agent._execute_script_async = AsyncMock(
            return_value=ToolResult(output="hello\n")
        )

        result = await agent.step()

        assert "Script executed successfully" in result
        agent.memory.update_memory.assert_any_call(
            "tool", "hello\n", tool_call_id="python_exec_1"
        )
        agent.memory.update_memory.assert_any_call("assistant", result)

    @pytest.mark.asyncio
    async def test_step_invalid_script(self, agent):
        """Test async step() with invalid script: handles syntax error."""
        agent.memory.get_recent_messages.return_value = [
            Message(role="user", content="invalid syntax")
        ]

        with patch.object(agent, "_validate_script", return_value=False):
            result = await agent.step()

        assert "Invalid Python script provided." == result
        agent.memory.update_memory.assert_called_with("assistant", result)

    @pytest.mark.asyncio
    async def test_step_no_user_input(self, agent):
        """Test async step() with no user input."""
        agent.memory.get_recent_messages.return_value = []

        result = await agent.step()

        assert "No user input to process." == result
        agent.memory.update_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_step_with_error(self, agent):
        """Test async step() with execution error."""
        agent._execute_script_async = AsyncMock(side_effect=Exception("Test error"))

        result = await agent.step()

        assert "Error in Python agent step: Test error" in result
        agent.memory.update_memory.assert_called_with("assistant", result)

    @pytest.mark.asyncio
    async def test_validate_script_valid(self, agent):
        """Test _validate_script with valid Python code."""
        script = "print('valid')"
        is_valid = agent._validate_script(script)

        assert is_valid is True

    def test_validate_script_invalid(self, agent):
        """Test _validate_script with invalid Python code."""
        script = "invalid syntax"
        is_valid = agent._validate_script(script)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_execute_script_async_success(self, agent):
        """Test _execute_script_async with successful execution."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="output")

        with patch(
            "app.modes.python_mode.python_agent.DockerSandbox",
            return_value=mock_sandbox,
        ):
            result = await agent._execute_script_async("print('test')", timeout=10)

        assert result.output == "output"
        assert result.error is None
        mock_sandbox.write_file.assert_called_with("temp_script.py", "print('test')")
        mock_sandbox.run_command.assert_called_with("python temp_script.py", timeout=10)

    @pytest.mark.asyncio
    async def test_execute_script_async_timeout(self, agent):
        """Test _execute_script_async with timeout error."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch(
            "app.modes.python_mode.python_agent.DockerSandbox",
            return_value=mock_sandbox,
        ):
            result = await agent._execute_script_async("print('test')", timeout=10)

        assert "Script timed out after 10s" in result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_script_async_exception(self, agent):
        """Test _execute_script_async with general exception."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(side_effect=Exception("Exec error"))

        with patch(
            "app.modes.python_mode.python_agent.DockerSandbox",
            return_value=mock_sandbox,
        ):
            result = await agent._execute_script_async("print('test')", timeout=10)

        assert "Exec error" == result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_run_tool_success(self, agent):
        """Test run_tool with valid tool call."""
        mock_tool = MagicMock()
        mock_tool.execute = AsyncMock(return_value=ToolResult(output="tool output"))
        agent.tools = ToolCollection(tools=[mock_tool])
        agent.tools.get_tool.return_value = mock_tool

        result = await agent.run_tool("test_tool", param="value")

        assert result.output == "tool output"
        mock_tool.execute.assert_called_with(param="value")

    @pytest.mark.asyncio
    async def test_run_tool_not_found(self, agent):
        """Test run_tool with unknown tool."""
        agent.tools = ToolCollection(tools=[])
        agent.tools.get_tool.return_value = None

        result = await agent.run_tool("missing_tool")

        assert "Tool 'missing_tool' not found." == result.error

    @pytest.mark.asyncio
    async def test_run_tool_execution_error(self, agent):
        """Test run_tool with tool execution error."""
        mock_tool = MagicMock()
        mock_tool.execute = AsyncMock(side_effect=Exception("Tool error"))
        agent.tools = ToolCollection(tools=[mock_tool])
        agent.tools.get_tool.return_value = mock_tool

        result = await agent.run_tool("test_tool")

        assert "Tool error" == result.error
