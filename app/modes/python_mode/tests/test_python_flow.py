import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow


@pytest.mark.asyncio
class TestPythonFlow:
    """Unit tests for PythonFlow."""

    @pytest.fixture
    def flow(self):
        """Fixture for a basic PythonFlow instance."""
        flow = PythonFlow()
        flow.primary_agent = MagicMock(spec=PythonAgent)
        flow.primary_agent.step = AsyncMock(return_value="Step result")
        flow.primary_agent.update_memory = MagicMock()
        return flow

    def test_inheritance_from_base_flow(self):
        """Test that PythonFlow inherits from BaseFlow."""
        assert issubclass(PythonFlow, BaseFlow)
        flow = PythonFlow()
        assert isinstance(flow, BaseFlow)

    def test_init_with_default_agents(self):
        """Test __init__ creates default agents if none provided."""
        flow = PythonFlow()

        assert "python" in flow.agents
        assert isinstance(flow.agents["python"], PythonAgent)
        assert "planner" in flow.agents
        assert isinstance(flow.agents["planner"], BaseAgent)
        assert flow.planning_enabled is True
        assert flow.max_steps == 5
        assert flow.current_step == 0

    def test_init_with_provided_agents(self):
        """Test __init__ uses provided agents."""
        mock_agent1 = MagicMock(spec=PythonAgent)
        mock_agent2 = MagicMock(spec=BaseAgent)
        agents = {"custom1": mock_agent1, "custom2": mock_agent2}

        flow = PythonFlow(agents=agents)

        assert flow.agents == agents
        assert flow.primary_agent == mock_agent1  # Assumes first is primary

    @pytest.mark.asyncio
    async def test_execute_with_planning_success(self, flow):
        """Test execute() with planning enabled: plans and executes steps."""
        flow._plan_steps = AsyncMock(return_value="Planned: 1. Validate; 2. Execute")
        flow._execute_step = AsyncMock(
            side_effect=["Step 1", "complete", "Step 3"]
        )  # Early break

        result = await flow.execute("test input")

        assert "Planned steps: Planned: 1. Validate; 2. Execute" in result
        assert "Step 1: Step 1" in result
        assert "Step 2: complete" in result
        assert "Step 3" not in result  # Should break early
        flow.primary_agent.update_memory.assert_called_with("user", "test input")
        assert flow.current_step == 2  # Executed 2 steps

    @pytest.mark.asyncio
    async def test_execute_without_planning(self, flow):
        """Test execute() with planning disabled."""
        flow.planning_enabled = False
        flow._execute_step = AsyncMock(return_value="Step result")
        flow.current_step = 0

        result = await flow.execute("test input")

        assert "Planned steps" not in result
        assert "Step 1: Step result" in result
        flow.primary_agent.update_memory.assert_called_with("user", "test input")

    @pytest.mark.asyncio
    async def test_execute_max_steps(self, flow):
        """Test execute() reaches max_steps without early break."""
        flow._execute_step = AsyncMock(return_value="Step result")
        flow.max_steps = 2

        result = await flow.execute("test input")

        assert flow.current_step == 2
        assert "Step 1: Step result" in result
        assert "Step 2: Step result" in result

    @pytest.mark.asyncio
    async def test_execute_no_primary_agent(self, flow):
        """Test execute() without primary agent."""
        flow.primary_agent = None
        flow._execute_step = AsyncMock(return_value="No agent")

        result = await flow.execute("test input")

        assert "No primary agent configured for execution." in result

    @pytest.mark.asyncio
    async def test_execute_with_error(self, flow):
        """Test execute() handles general exception."""
        flow._execute_step = AsyncMock(side_effect=Exception("Flow error"))

        result = await flow.execute("test input")

        assert "Error in Python flow execution: Flow error" == result

    @pytest.mark.asyncio
    async def test_plan_steps(self, flow):
        """Test _plan_steps returns planned steps."""
        result = await flow._plan_steps("test input")

        expected = "1. Validate input; 2. Execute Python script; 3. Process output with plugins if needed"
        assert result == expected

    @pytest.mark.asyncio
    async def test_execute_step_with_plugin(self, flow):
        """Test _execute_step uses agent and runs plugin if 'data' in input."""
        flow._run_plugin_action = AsyncMock(return_value="Plugin processed")

        result = await flow._execute_step("process data input")

        assert "Step result; Plugin result: Plugin processed" == result
        flow.primary_agent.step.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_no_plugin(self, flow):
        """Test _execute_step without plugin trigger."""
        result = await flow._execute_step("no data input")

        assert "Step result" == result
        flow.primary_agent.step.assert_called_once()
        flow._run_plugin_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_plugin_action_success(self, flow):
        """Test _run_plugin_action with valid action."""
        mock_module = MagicMock()
        mock_action = MagicMock(return_value="Processed data")
        mock_module.process_data = mock_action

        with patch(
            "app.modes.python_mode.python_flow.__import__", return_value=mock_module
        ), patch(
            "app.modes.python_mode.python_flow.asyncio.to_thread",
            AsyncMock(return_value="Processed data"),
        ):
            result = await flow._run_plugin_action("process_data", {"data": "test"})

        assert result == "Processed data"
        mock_action.assert_called_with(data="test")

    @pytest.mark.asyncio
    async def test_run_plugin_action_not_found(self, flow):
        """Test _run_plugin_action with missing action."""
        mock_module = MagicMock()
        setattr(mock_module, "process_data", None)

        with patch(
            "app.modes.python_mode.python_flow.__import__", return_value=mock_module
        ):
            result = await flow._run_plugin_action("process_data", {"data": "test"})

        assert "Action 'process_data' not found." == result

    @pytest.mark.asyncio
    async def test_run_plugin_action_import_error(self, flow):
        """Test _run_plugin_action with import error."""
        with patch(
            "app.modes.python_mode.python_flow.__import__", side_effect=ImportError
        ):
            result = await flow._run_plugin_action("invalid_action", {})

        assert "Plugin action failed: Import error." == result
