"""
Tool for simulating agent swarms for testing scenarios using pyautogen.
Deploys a group of agents to interact, test target (code/file/URL), detect issues emerging from collective behavior.
Supports scenarios like 'api_load' (concurrent calls), 'bug_hunt' (collaborative search).
Uses LLM for agent chats, limits rounds/agents for safety.
"""

from typing import Any, Dict, List

from autogen import GroupChat, GroupChatManager
from autogen.agentchat import AssistantAgent, UserProxyAgent

import app.tool as tool_module  # To avoid circular import
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class AgentSwarmTester(BaseTool):
    name: str = "agent_swarm_tester"
    description: str = (
        "Deploy a swarm of AI agents to test a target via simulated interactions. "
        "Scenarios: 'api_load' for concurrency, 'bug_hunt' for issue discovery. "
        "Outputs test report with issues and logs."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "test_scenario": {
                "type": "string",
                "description": "Scenario: 'api_load', 'bug_hunt' or custom.",
                "default": "bug_hunt",
            },
            "num_agents": {
                "type": "integer",
                "description": "Number of agents (default 3, max 5).",
                "default": 3,
            },
            "test_target": {
                "type": "string",
                "description": "Target: file path, URL, or code snippet to test.",
            },
            "interaction_rounds": {
                "type": "integer",
                "description": "Number of interaction rounds (default 5).",
                "default": 5,
            },
            "env_config": {
                "type": "object",
                "description": "Config: {'llm_config': dict, 'timeout': int}.",
                "default": {"timeout": 30},
            },
        },
        "required": ["test_target", "test_scenario"],
    }

    def __init__(self):
        super().__init__()
        # Use object.__setattr__ to bypass Pydantic validation for runtime attribute
        object.__setattr__(
            self,
            "llm_config",
            {"config_list": [{"model": "gpt-3.5-turbo", "api_key": "dummy"}]},
        )  # Assume set globally or from config

    def create_agents(self, num_agents: int, scenario: str) -> List[AssistantAgent]:
        """Create agents: e.g., coordinator, testers, observer based on scenario."""
        agents = []
        roles = ["coordinator", "tester"] * (num_agents // 2) + ["observer"] * (
            num_agents % 2
        )
        for i, role in enumerate(roles):
            agent = AssistantAgent(
                name=f"{role.capitalize()}_{i}",
                system_message=f"You are a {role} agent for {scenario} testing the target. Collaborate via chat.",
                llm_config=self.llm_config,
            )
            agents.append(agent)
        return agents

    async def execute(self, **kwargs) -> ToolResult:
        try:
            scenario = kwargs.get("test_scenario", "bug_hunt")
            num_agents = min(kwargs.get("num_agents", 3), 5)  # Limit
            test_target = kwargs["test_target"]
            rounds = kwargs.get("interaction_rounds", 5)
            env_config = kwargs.get("env_config", {"timeout": 30})

            # Create agents
            agents = self.create_agents(num_agents, scenario)
            manager = GroupChatManager(
                groupchat=GroupChat(agents=agents, messages=[], max_round=rounds),
                llm_config=self.llm_config,
            )

            # Initial message
            user_proxy = UserProxyAgent("user", code_execution_config=False)
            task = f"Test the {scenario} on target: {test_target}. Run {rounds} rounds of collaboration, find issues, measure coverage. Report at end."
            await user_proxy.initiate_chat(manager, message=task)

            # Aggregate results - from chat messages
            chat_history = manager.groupchat.messages
            issues = []
            for msg in chat_history[-5:]:  # Last messages for summary
                if "issue" in str(msg).lower() or "error" in str(msg).lower():
                    issues.append(
                        {
                            "type": scenario,
                            "description": str(msg).strip()[:100],
                            "agent_report": str(msg),
                        }
                    )

            # Mock coverage: based on target type
            coverage = {
                "files_touched": (
                    [test_target]
                    if isinstance(test_target, str) and test_target.endswith(".py")
                    else []
                ),
                "errors": len(issues),
            }

            logs = "\n".join([str(msg) for msg in chat_history[-10:]])  # Last 10 logs

            result = {
                "test_summary": {"agents_active": num_agents, "issues_found": issues},
                "coverage_metrics": coverage,
                "logs": logs,
            }

            logger.info(
                f"Agent swarm test complete for {scenario}: {len(issues)} issues"
            )
            return self.success_response(result)

        except Exception as e:
            logger.error(f"AgentSwarmTester failed: {str(e)}")
            return self.fail_response(f"Swarm testing failed: {str(e)}")
