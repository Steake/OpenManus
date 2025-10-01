"""Unit tests for AgentSwarmTester tool."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.tool.agent_swarm_tester import AgentSwarmTester
from app.tool.base import ToolResult


@pytest.fixture
def swarm_tester():
    return AgentSwarmTester()


@pytest.mark.asyncio
async def test_agent_swarm_tester_basic(swarm_tester):
    """Test basic swarm execution with mocked autogen."""
    test_target = "test_api.py"

    with patch("pyautogen.AssistantAgent", Mock()), patch(
        "pyautogen.GroupChatManager", Mock()
    ), patch("pyautogen.GroupChat", Mock()), patch(
        "pyautogen.UserProxyAgent", Mock()
    ) as mock_proxy:

        mock_chat = MagicMock()
        mock_chat.messages = [
            MagicMock(content="Found issue: timeout"),
            MagicMock(content="Coverage: 80%"),
            MagicMock(content="No more issues"),
        ]
        mock_manager = MagicMock(groupchat=MagicMock(messages=mock_chat.messages))
        mock_proxy.initiate_chat.return_value = mock_manager

        result = await swarm_tester.execute(
            test_scenario="bug_hunt",
            test_target=test_target,
            num_agents=2,
            interaction_rounds=3,
        )

    assert isinstance(result, ToolResult)
    assert result.error is None
    import json

    data = json.loads(result.output)
    assert "test_summary" in data
    assert len(data["test_summary"]["issues_found"]) >= 1  # Mocked issue
    assert "coverage_metrics" in data
    assert test_target in data["coverage_metrics"]["files_touched"]
    assert "logs" in data


@pytest.mark.asyncio
async def test_agent_swarm_tester_limit_agents(swarm_tester):
    """Test num_agents limiting."""
    with patch("pyautogen.AssistantAgent"):
        result = await swarm_tester.execute(
            test_scenario="api_load", test_target="url", num_agents=10  # Exceed limit
        )

    data = json.loads(result.output)
    assert data["test_summary"]["agents_active"] == 5  # Max 5


@pytest.mark.asyncio
async def test_agent_swarm_tester_invalid_target(swarm_tester):
    """Test with invalid target - error on exec."""
    with patch(
        "pyautogen.UserProxyAgent.initiate_chat",
        side_effect=Exception("Invalid target"),
    ):
        result = await swarm_tester.execute(
            test_scenario="bug_hunt", test_target=""  # Invalid
        )

    assert result.error is not None
    assert "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_agent_swarm_tester_create_agents(swarm_tester):
    """Test agent creation."""
    agents = swarm_tester.create_agents(3, "load")
    assert len(agents) == 3
    assert all(isinstance(a, Mock) for a in agents)  # Since mocked


if __name__ == "__main__":
    pytest.main([__file__])
