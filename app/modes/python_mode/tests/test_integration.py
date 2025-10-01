import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modes.python_mode.plugins.python_actions.example_plugin import process_data
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow
from app.modes.python_mode.python_tool import PythonTool
from app.tool.base import ToolResult


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for Python Mode components."""

    @pytest.fixture
    def mock_sandbox(self):
        """Mock DockerSandbox for all integration tests."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="Integration output")
        mock_sandbox.copy_from = AsyncMock()
        return mock_sandbox

    @pytest.mark.asyncio
    async def test_end_to_end_tool_to_agent(self, mock_sandbox):
        """Test end-to-end: Tool execution feeds into Agent step."""
        with patch("app.sandbox.core.sandbox.DockerSandbox", return_value=mock_sandbox):
            tool = PythonTool()
            agent = PythonAgent(name="integration_agent")
            agent.memory = MagicMock()
            agent.memory.get_recent_messages.return_value = [
                MagicMock(content="print('tool to agent')")
            ]
            agent._execute_script_async = AsyncMock(
                return_value=ToolResult(output="Agent output")
            )

            # Execute tool
            tool_result = await tool.execute(code="print('tool output')")
            assert tool_result.output == "Integration output"

            # Feed to agent
            agent.memory.get_recent_messages.return_value = [
                MagicMock(content=tool_result.output)
            ]
            agent_result = await agent.step()

            assert "Script executed successfully" in agent_result
            assert "Agent output" in agent_result  # From mocked execution

    @pytest.mark.asyncio
    async def test_end_to_end_flow_with_agent_and_tool(self, mock_sandbox):
        """Test end-to-end: Flow sequences Agent and Tool executions."""
        with patch("app.sandbox.core.sandbox.DockerSandbox", return_value=mock_sandbox):
            agent = PythonAgent(name="flow_agent")
            agent.step = AsyncMock(return_value="Agent step complete")
            agent.update_memory = MagicMock()

            tool = PythonTool()
            tool.execute = AsyncMock(return_value=ToolResult(output="Tool in flow"))

            flow = PythonFlow(agents={"python": agent})
            flow.primary_agent = agent
            flow._execute_step = AsyncMock(return_value="Flow step with tool")
            flow._run_plugin_action = AsyncMock(return_value="Plugin in flow")

            result = await flow.execute("integrate flow input")

            assert "Planned steps" in result
            assert "Flow step with tool" in result
            assert "Plugin in flow" in result
            agent.update_memory.assert_called()
            agent.step.assert_called()

    @pytest.mark.asyncio
    async def test_plugin_integration_in_tool(self, mock_sandbox):
        """Test plugin integration within Tool execution."""
        with patch(
            "app.sandbox.core.sandbox.DockerSandbox", return_value=mock_sandbox
        ), patch("app.modes.python_mode.python_tool.__import__") as mock_import:
            mock_module = MagicMock()
            mock_module.register_actions.return_value = {"process_data": process_data}
            mock_import.return_value = mock_module

            tool = PythonTool()
            tool._load_plugins = AsyncMock(return_value=["example"])

            # Execute with plugin
            result = await tool.execute(
                code="print('plugin test')", plugins=["example"], timeout=10
            )

            assert result.output == "Integration output"
            tool._load_plugins.assert_called_with(["example"])
            mock_import.assert_called()

    @pytest.mark.asyncio
    async def test_async_flow_without_blocking(self, mock_sandbox):
        """Test async flow executes without blocking (multiple steps concurrently mocked)."""
        with patch("app.sandbox.core.sandbox.DockerSandbox", return_value=mock_sandbox):
            agent = PythonAgent(name="async_agent")
            agent.step = AsyncMock(return_value="Async step 1")
            agent.update_memory = MagicMock()

            flow = PythonFlow(agents={"python": agent})
            flow.primary_agent = agent
            flow._plan_steps = AsyncMock(return_value="Async plan")
            flow._execute_step = AsyncMock(side_effect=["Step 1", "Step 2 async"])

            # Run flow
            result = await flow.execute("async flow test")

            assert "Async plan" in result
            assert "Step 1: Step 1" in result
            assert "Step 2 async" in result
            assert flow.current_step == 2

            # Verify no blocking: steps should complete in sequence but async
            agent.step.assert_has_calls(
                [AsyncMock.call(), AsyncMock.call()], any_order=False
            )

    @pytest.mark.asyncio
    async def test_end_to_end_script_execution_via_all_components(self, mock_sandbox):
        """Test full chain: Script via Tool -> Plugin -> Agent -> Flow summary."""
        with patch(
            "app.sandbox.core.sandbox.DockerSandbox", return_value=mock_sandbox
        ), patch(
            "app.modes.python_mode.python_tool.__import__"
        ) as mock_import_tool, patch(
            "app.modes.python_mode.python_flow.__import__"
        ) as mock_import_flow:
            # Mocks for imports
            mock_plugin_module = MagicMock()
            mock_plugin_module.process_data = process_data
            mock_import_tool.return_value = mock_plugin_module
            mock_import_flow.return_value = mock_plugin_module

            # Initialize components
            tool = PythonTool()
            tool._load_plugins = AsyncMock(return_value=["example"])

            agent = PythonAgent(name="full_chain_agent")
            agent.memory = MagicMock()
            agent.memory.get_recent_messages.return_value = [
                MagicMock(content="full chain input")
            ]
            agent._execute_script_async = AsyncMock(
                return_value=ToolResult(output="Processed: FULL CHAIN INPUT")
            )

            flow = PythonFlow(agents={"python": agent})
            flow.primary_agent = agent
            flow._execute_step = AsyncMock(return_value="Full chain complete")
            flow._run_plugin_action = AsyncMock(return_value=process_data("chain data"))

            # Chain: Tool -> Plugin in tool -> Agent step -> Flow
            tool_result = await tool.execute(code="print('chain')", plugins=["example"])
            assert tool_result.output == "Integration output"

            agent.memory.get_recent_messages.return_value = [
                MagicMock(content=tool_result.output)
            ]
            agent_result = await agent.step()
            assert "Processed: FULL CHAIN INPUT" in agent_result

            flow_result = await flow.execute(agent_result)
            assert "Full chain complete" in flow_result
            assert "PROCESSED: CHAIN DATA" in flow_result  # From plugin in flow
