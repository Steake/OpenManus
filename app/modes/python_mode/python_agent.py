import ast
import asyncio
import os
import sys
import tempfile
from typing import Any, Dict, Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.config import Config
from app.logger import logger
from app.sandbox.core.sandbox import DockerSandbox
from app.schema import Message
from app.tool import (
    Bash,
    BrowserUseTool,
    Crawl4aiTool,
    CreateChatCompletion,
    PlanningTool,
    StrReplaceEditor,
    Terminate,
    WebSearch,
)
from app.tool.base import ToolResult
from app.tool.python_execute import PythonExecute
from app.tool.tool_collection import ToolCollection


class PythonAgent(BaseAgent):
    """
    A basic agent for executing Python scripts as tools in a sandboxed environment.

    Inherits from BaseAgent and implements step() for Python-specific execution.
    Supports async execution, script validation, and tool handling.
    """

    # Agent-specific fields
    tools: ToolCollection = Field(default_factory=ToolCollection)
    sandbox_config: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=30, description="Default script timeout in seconds")

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize tools if none configured or empty
        if not getattr(self, "tools", None) or not getattr(self.tools, "tools", ()):
            self.tools = ToolCollection(
                Bash(),
                BrowserUseTool(),
                Crawl4aiTool(),
                CreateChatCompletion(),
                PlanningTool(),
                StrReplaceEditor(),
                Terminate(),
                WebSearch(),
                PythonExecute(),
            )
            logger.info("Loaded tools: " + ", ".join(t.name for t in self.tools.tools))
        # Load config if available
        self.config = Config()
        logger.info(f"Initialized PythonAgent: {self.name}")

    async def step(self) -> str:
        """
        Execute a single step: Parse user request, validate and run Python script,
        handle tool calls, and return ToolResult.
        """
        try:
            # Get recent messages
            recent_messages = self.memory.get_recent_messages(5)
            if not recent_messages or not recent_messages[-1].role == "user":
                return "No user input to process."

            user_input = recent_messages[-1].content
            logger.info(f"Processing Python step with input: {user_input[:100]}...")

            # Basic script extraction/validation (in real impl, use LLM to generate script)
            # For prototype, assume input is a script snippet
            if not self._validate_script(user_input):
                error_msg = "Invalid Python script provided."
                self.update_memory("assistant", error_msg)
                return error_msg

            # Execute in sandbox
            result = await self._execute_script_async(user_input, timeout=self.timeout)

            # Update memory with result
            self.update_memory(
                "tool",
                str(result),
                tool_call_id="python_exec_1",
                name="python_tool",  # Placeholder
            )

            # Add assistant response
            response = f"Script executed successfully. Output: {result.output if result.output else 'No output'}"
            if result.error:
                response = f"Script error: {result.error}"
            self.update_memory("assistant", response)

            return response

        except Exception as e:
            error_msg = f"Error in Python agent step: {str(e)}"
            logger.error(error_msg)
            self.update_memory("assistant", error_msg)
            return error_msg

    def _validate_script(self, script: str) -> bool:
        """
        Validate Python script using ast.parse.

        Args:
            script: Python code snippet.

        Returns:
            True if valid, False otherwise.
        """
        try:
            ast.parse(script)
            return True
        except SyntaxError as e:
            logger.warning(f"Script syntax error: {e}")
            return False

    async def _execute_script_async(self, script: str, timeout: int) -> ToolResult:
        """
        Execute Python script, preferring Docker sandbox when enabled and available,
        otherwise fall back to local execution.

        Args:
            script: Python code to execute.
            timeout: Execution timeout.

        Returns:
            ToolResult with execution output or error.
        """
        # Log script source for observability
        try:
            logger.info(
                f"=== Begin Python script ===\n{script}\n=== End Python script ==="
            )
        except Exception:
            pass

        # Decide whether to use sandbox from config, default False if unavailable
        try:
            use_sandbox = getattr(self.config.sandbox, "use_sandbox", False)
        except Exception:
            use_sandbox = False

        logger.info(f"Sandbox enabled: {use_sandbox}")

        if not use_sandbox:
            logger.info("Sandbox disabled; executing locally")
            return await self._execute_script_local_async(script, timeout)

        # Try sandbox; on any Docker-related failure, fall back locally
        try:
            async with DockerSandbox() as sandbox:
                await sandbox.write_file("temp_script.py", script)

                logger.info("Executing in Docker sandbox: python -u temp_script.py")
                cmd = f"python -u temp_script.py"
                try:
                    output = await asyncio.wait_for(
                        sandbox.run_command(cmd, timeout=timeout), timeout=timeout
                    )
                    return ToolResult(output=output)
                except asyncio.TimeoutError:
                    return ToolResult(error=f"Script timed out after {timeout}s")
                except Exception as e:
                    return ToolResult(error=str(e))
        except Exception as e:
            logger.warning(
                f"Docker sandbox unavailable, falling back to local execution: {e}"
            )
            return await self._execute_script_local_async(script, timeout)

    async def _execute_script_local_async(
        self, script: str, timeout: int
    ) -> ToolResult:
        """
        Execute Python script locally using the current interpreter with timeout.
        Stream stdout/stderr live to logs and return aggregated output.
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "temp_script.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(script)

                logger.info(
                    f"Executing locally with interpreter: {sys.executable}, timeout: {timeout}s"
                )
                logger.info(f"Temp script path: {path}")

                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-u",
                    path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout_lines = []
                stderr_lines = []

                async def _forward(reader, prefix, buf, level: str = "info"):
                    try:
                        while True:
                            line = await reader.readline()
                            if not line:
                                break
                            text = line.decode("utf-8", errors="replace").rstrip()
                            buf.append(text + "\n")
                            if level == "error":
                                logger.error(f"[python {prefix}] {text}")
                            else:
                                logger.info(f"[python {prefix}] {text}")
                    except Exception as e:
                        logger.warning(f"Stream forwarding error ({prefix}): {e}")

                t_out = asyncio.create_task(
                    _forward(proc.stdout, "stdout", stdout_lines, "info")
                )
                t_err = asyncio.create_task(
                    _forward(proc.stderr, "stderr", stderr_lines, "error")
                )

                try:
                    await asyncio.wait_for(proc.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    await proc.wait()
                    for t in (t_out, t_err):
                        if not t.done():
                            t.cancel()
                    return ToolResult(error=f"Script timed out after {timeout}s")

                await asyncio.gather(t_out, t_err, return_exceptions=True)

                rc = proc.returncode
                out = "".join(stdout_lines)
                err = "".join(stderr_lines)
                if rc != 0:
                    return ToolResult(error=err or f"Non-zero exit status {rc}")

                return ToolResult(output=out)
        except Exception as e:
            return ToolResult(error=str(e))

    async def run_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Run a specific tool from the collection.

        Args:
            tool_name: Name of the tool to run.
            **kwargs: Tool parameters.

        Returns:
            ToolResult from tool execution.
        """
        tool = self.tools.get_tool(tool_name)
        if not tool:
            return ToolResult(error=f"Tool '{tool_name}' not found.")

        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(error=str(e))
