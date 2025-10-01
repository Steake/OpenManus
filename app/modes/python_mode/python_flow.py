import ast
import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.config import Config
from app.flow.base import BaseFlow
from app.flow.planning import PlanningFlow  # For integration with planning
from app.llm import LLM
from app.logger import logger
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_tool import PythonTool
from app.schema import Message


class PythonFlow(BaseFlow):
    """
    A simple flow for sequencing Python script executions.

    Inherits from BaseFlow. Integrates with planning for step sequencing,
    supports modular steps with plugin actions. Designed for lightweight
    Python scripting extensibility.
    """

    # Flow-specific fields
    planning_enabled: bool = Field(
        default=True, description="Enable planning integration"
    )
    max_steps: int = Field(default=5, description="Maximum flow steps")
    current_step: int = Field(default=0)

    def __init__(self, agents: Optional[Dict[str, BaseAgent]] = None, **data):
        # Default agents if not provided
        if not agents:
            agents = {
                "python": PythonAgent(name="python_agent"),
                "planner": PythonAgent(
                    name="planner_agent"
                ),  # Placeholder for planning
            }
        super().__init__(agents=agents, **data)
        logger.info(f"Initialized PythonFlow with agents: {list(agents.keys())}")

    async def execute(self, input_text: str) -> str:
        """
        Execute the Python flow: Plan steps if enabled, then sequence executions.

        Args:
            input_text: Initial input or task description.

        Returns:
            Summary of flow execution results.
        """
        try:
            results = []
            self.current_step = 0
            failed = False

            # Ensure we have executable Python (transform NL task if needed)
            script = await self._ensure_code(input_text)
            if self.primary_agent:
                self.primary_agent.update_memory("user", script)

            # Integrate planning if enabled
            if self.planning_enabled:
                plan = await self._plan_steps(input_text)
                results.append(f"Planned steps: {plan}")
                logger.info(f"Planning completed: {plan}")

            # Execute steps
            while self.current_step < self.max_steps:
                self.current_step += 1
                step_result = await self._execute_step(input_text)
                results.append(f"Step {self.current_step}: {step_result}")

                # Fail fast on error
                if "error" in step_result.lower():
                    failed = True
                    break

                # Stop on explicit success sentinel
                if "flow_ok" in step_result.lower():
                    break

            # Finalize
            final_msg = "\n".join(results)
            if failed:
                logger.error("PythonFlow executed with errors")
            else:
                logger.info("PythonFlow executed successfully")
            return final_msg

        except Exception as e:
            error_msg = f"Error in Python flow execution: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _plan_steps(self, input_text: str) -> str:
        """
        Integrate with planning to generate sequence of Python steps.

        Args:
            input_text: Task description.

        Returns:
            Planned steps as string.
        """
        # Basic planning integration (prototype: simple breakdown)
        # In full impl, use PlanningFlow or LLM for dynamic planning
        steps = [
            "1. Validate input",
            "2. Execute Python script",
            "3. Process output with plugins if needed",
        ]
        return "; ".join(steps)

    def _looks_like_python(self, text: str) -> bool:
        """Return True if text parses as valid Python, else False."""
        try:
            ast.parse(text)
            return True
        except SyntaxError:
            return False

    def _extract_code_block(self, text: str) -> str:
        """Extract first fenced code block; if none, return text if it parses as Python."""
        match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # If not fenced, return text only if it is valid Python
        try:
            ast.parse(text)
            return text
        except SyntaxError:
            return ""

    def _fallback_echo_script(self, task: str) -> str:
        """Safe minimal fallback script when LLM transform fails."""
        escaped = task.replace('"""', r"\"\"\"")
        return "\n".join(
            [
                "# Auto-generated fallback from natural-language task",
                f'TASK = """{escaped}"""',
                "print('Task:')",
                "print(TASK)",
                "print('FLOW_OK')",
            ]
        )

    async def _nl_to_python(self, task: str) -> str:
        """Use LLM to convert NL task into a self-contained Python script (generic, not hardcoded)."""
        try:
            llm = LLM()
            # Describe available tools to the generator and define the tool-call contract
            tools_info = ""
            try:
                if getattr(self, "primary_agent", None) and getattr(
                    self.primary_agent, "tools", None
                ):
                    tools_info = json.dumps(
                        self.primary_agent.tools.to_params(), indent=2
                    )
            except Exception:
                tools_info = ""

            system_msgs = [
                Message.system_message(
                    """You convert a natural-language task into a single self-contained Python 3.12 script.
Requirements:
- Offline only, standard library only (no network, no external packages)
- Produce tangible output relevant to the task (e.g., write to a file, print structured plan/results)
- Script must be runnable as-is
- End by printing exactly: FLOW_OK

Tool calling contract:
- You cannot import project internals or call tools directly.
- To request a tool call, print a single line beginning with:
  TOOL_CALL {"name": "<tool_name>", "args": { ... }}
- Available tools (OpenManus tool suite) with schemas:
"""
                    + (tools_info or "[no tools available]")
                )
            ]
            user_msgs = [
                Message.user_message(
                    f"""Task:
{task}

Generate only Python code. Prefer not to include Markdown fences; if you include fences, the content must be runnable as-is.
When you need web, bash, or editing capabilities, emit a TOOL_CALL line per the contract above."""
                )
            ]
            response = await llm.ask(
                messages=user_msgs,
                system_msgs=system_msgs,
                stream=False,
                temperature=0.1,
            )
            code = self._extract_code_block(response) or response.strip()
            if not code:
                logger.warning("LLM returned empty code; using fallback script")
                return self._fallback_echo_script(task)
            # Validate code parses
            try:
                ast.parse(code)
                return code
            except SyntaxError:
                logger.warning("LLM code did not parse; using fallback script")
                return self._fallback_echo_script(task)
        except Exception as e:
            logger.warning(f"LLM transform failed: {e}")
            return self._fallback_echo_script(task)

    async def _ensure_code(self, text: str) -> str:
        """Ensure the provided text is executable Python; transform via LLM if it is NL."""
        if self._looks_like_python(text):
            return text
        code = await self._nl_to_python(text)
        logger.info("Converted natural-language task to executable Python via LLM.")
        return code

    async def _execute_step(self, input_text: str) -> str:
        """
        Execute a single modular step, potentially using plugins.

        Args:
            input_text: Current input.

        Returns:
            Step result.
        """
        # Use primary agent (PythonAgent) for execution
        if self.primary_agent and isinstance(self.primary_agent, PythonAgent):
            step_result = await self.primary_agent.step()

            # Parse and execute any requested tool calls emitted by the script
            try:
                tool_outputs: List[str] = []
                for match in re.finditer(
                    r"^TOOL_CALL\s+(.*)$", step_result, flags=re.MULTILINE
                ):
                    payload = match.group(1).strip()
                    try:
                        data = json.loads(payload)
                        tool_name = data.get("name")
                        args = data.get("args") or {}
                        if tool_name:
                            tr = await self.primary_agent.run_tool(tool_name, **args)
                            tool_outputs.append(f"Tool '{tool_name}' => {str(tr)}")
                        else:
                            tool_outputs.append("Tool call missing 'name'")
                    except Exception as e:
                        tool_outputs.append(f"Tool call parse/exec error: {e}")
                if tool_outputs:
                    step_result += "\n" + "\n".join(tool_outputs)
            except Exception as e:
                step_result += f"\nTool handling error: {e}"

            # Simulate plugin action (e.g., data processing)
            if "data" in input_text.lower():
                plugin_result = await self._run_plugin_action(
                    "process_data", {"data": input_text}
                )
                step_result += f"; Plugin result: {plugin_result}"

            return step_result
        else:
            return "No primary agent configured for execution."

    async def _run_plugin_action(self, action_name: str, params: Dict[str, Any]) -> str:
        """
        Run a modular plugin action.

        Args:
            action_name: Name of the action (e.g., 'process_data').
            params: Action parameters.

        Returns:
            Action result.
        """
        try:
            # Dynamic import from plugins (prototype)
            module = __import__(
                f"app.modes.python_mode.plugins.python_actions.example_plugin",
                fromlist=[action_name],
            )
            action_func = getattr(module, action_name, None)
            if action_func:
                result = await asyncio.to_thread(action_func, **params)
                return str(result)
            else:
                return f"Action '{action_name}' not found."
        except ImportError:
            logger.warning(f"Plugin action '{action_name}' not available")
            return "Plugin action failed: Import error."
