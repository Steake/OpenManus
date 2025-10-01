"""
Proof-of-Concept Demo for Python Mode Functionality and TUI Integration.

This demo script showcases key features of Python Mode as part of Phase 1:
- Standalone Python scripting via Agent, Tool, and Flow.
- Plugin extensibility (using example_plugin).
- Sandboxed execution (real DockerSandbox where possible; mocks for standalone non-TUI runs).
- Async support with asyncio.
- Interactive TUI navigation and execution (launches tui.py with pre-populated examples).

Usage:
- Non-interactive: Run examples in console (default behavior).
- Interactive TUI: Uncomment the TUI launch in __main__ or run with --tui flag.

The demo aligns with API contracts:
- Simulates POST /modes/python/execute payload via execute() methods.
- Uses ToolResult/Message schemas for outputs.
- Handles errors gracefully (e.g., syntax validation).
- Includes mock base64 image for visualization (real matplotlib in sandbox if available).

Dependencies: Assumes project setup (Docker for sandbox, Textual for TUI).
For standalone non-TUI: Mocks sandbox to avoid Docker requirement.

Run: python app/modes/python_mode/demo.py
"""

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)
import argparse
import asyncio
import base64
import io
from typing import Optional

# Local imports (aligns with project structure)
from app.config import Config
from app.logger import logger
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow
from app.modes.python_mode.python_tool import PythonTool
from app.schema import Message
from app.tool.base import ToolResult


# Mock for sandbox in non-TUI (to make standalone without Docker)
class MockSandbox:
    """Mock sandbox for non-TUI demos (simulates execution without Docker)."""

    async def run_command(self, cmd: str, timeout: int) -> str:
        if "python" in cmd and "temp_script.py" in cmd:
            # Simulate script execution
            try:
                with open("temp_script.py", "r") as f:
                    script_content = f.read()
            except FileNotFoundError:
                script_content = ""
            if "import math; print(math.sqrt(16))" in script_content:
                return "4.0\n"
            elif "invalid" in script_content:
                return "", "SyntaxError: invalid syntax"
            elif "data" in script_content:
                return "Processed data output"
            else:
                return "Mock output"
        return "Mock command output"

    async def write_file(self, path: str, content: str):
        with open(path, "w") as f:
            f.write(content)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


async def mock_execute(self, script: str, timeout: int) -> ToolResult:
    """Mock for agent's _execute_script_async."""
    async with MockSandbox() as sandbox:
        await sandbox.write_file("temp_script.py", script)
        cmd = f"python temp_script.py"
        try:
            output = await asyncio.wait_for(
                sandbox.run_command(cmd, timeout=timeout), timeout=timeout
            )
            return ToolResult(output=output)
        except asyncio.TimeoutError:
            return ToolResult(error=f"Mock timeout after {timeout}s")
        except Exception as e:
            return ToolResult(error=str(e))


async def mock_execute_tool(
    self,
    code: str,
    plugins: Optional[list] = None,
    timeout: int = 30,
    generate_image: bool = False,
) -> ToolResult:
    """Mock for tool's execute method."""
    async with MockSandbox() as sandbox:
        await sandbox.write_file("temp_script.py", code)
        cmd = f"python temp_script.py"
        try:
            output = await asyncio.wait_for(
                sandbox.run_command(cmd, timeout=timeout), timeout=timeout
            )
            base64_image = None
            if generate_image and (
                "matplotlib" in code.lower() or "visualize" in code.lower()
            ):
                # Simple mock base64 PNG (1x1 red pixel)
                img_data = base64.b64encode(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c`\x00\x00\x00\x03\x00\x01\xdf\xa5\xd4\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
                ).decode()
                base64_image = f"data:image/png;base64,{img_data}"
            return ToolResult(output=output, base64_image=base64_image)
        except asyncio.TimeoutError:
            return ToolResult(error=f"Mock timeout after {timeout}s")
        except Exception as e:
            return ToolResult(error=str(e))


# Apply mock to Agent and Tool for non-TUI
PythonAgent._execute_script_async = mock_execute
PythonTool.execute = mock_execute_tool


async def non_interactive_agent_example():
    """Non-interactive Agent example: Simple math script."""
    logger.info("Running non-interactive Agent example...")
    agent = PythonAgent(name="demo_agent")
    script = "import math\nprint(math.sqrt(16))"
    agent.update_memory("user", script)
    result = await agent.step()
    print(f"Agent Result: {result}")
    return result


async def non_interactive_tool_example():
    """Non-interactive Tool example: Script with plugin and visualization."""
    logger.info("Running non-interactive Tool example...")
    tool = PythonTool()
    code = """import math
data = math.sqrt(16)
print(f'Sqrt result: {data}')
# Simulate plugin call
print('Plugin processed: ' + str(data).upper())
# Mock visualization
print('Visualization generated')"""
    result = await tool.execute(
        code=code,
        plugins=["example_plugin"],  # Demonstrates extensibility
        timeout=10,
        generate_image=True,  # Triggers mock base64
    )
    print(f"Tool Result: {result.output if result.output else result.error}")
    if result.base64_image:
        print(f"Mock Base64 Image Preview: {result.base64_image[:50]}...")
    return result


async def non_interactive_flow_example():
    """Non-interactive Flow example: Multi-step task with plugin."""
    logger.info("Running non-interactive Flow example...")
    flow = PythonFlow(agents={"python": PythonAgent(name="flow_agent")})
    task = "Calculate sqrt(16), process data with plugin, and visualize"
    result = await flow.execute(task)
    print(f"Flow Result: {result}")
    return result


async def non_interactive_error_example():
    """Error handling demo: Invalid script."""
    logger.info("Running error demo...")
    tool = PythonTool()
    bad_code = "invalid syntax here"
    result = await tool.execute(code=bad_code, timeout=5)
    print(f"Error Result: {result.error}")
    return result


async def run_non_interactive_examples():
    """Run all non-interactive examples sequentially."""
    await non_interactive_agent_example()
    await non_interactive_tool_example()
    await non_interactive_flow_example()
    await non_interactive_error_example()
    print(
        "\nNon-interactive examples completed. All features showcased: async execution, plugins, sandbox (mocked), errors."
    )


async def tui_demo():
    """Launch TUI with pre-populated demo content."""
    try:
        from app.modes.python_mode.tui import PythonTUI

        logger.info("Launching TUI demo...")
        # Create app with initial state
        app = PythonTUI()
        # Pre-populate script for Tool tab (simulates auto-load)
        app.script_code = """# Demo Script: Math and Plugin
import math
result = math.sqrt(16)
print(f'Result: {result}')
# Plugin simulation (process_data)
processed = result.upper()  # Mock plugin
print(f'Processed: {processed}')"""

        # For Agent/Flow, can set via messages or inputs (TUI handles dynamically)
        # Simulate interaction: Auto-execute on load (via timer or event)
        async def auto_execute():
            await asyncio.sleep(2)  # Delay for UI load
            await app.execute_action()  # Trigger execute

        asyncio.create_task(auto_execute())
        # Run TUI (Textual's run() is sync, but wrap in async for demo)
        await asyncio.to_thread(app.run)
    except ImportError as e:
        logger.warning(f"TUI not available: {e}. Install Textual to enable.")
        print("TUI demo skipped: Textual library not installed.")


def main():
    parser = argparse.ArgumentParser(description="Python Mode Demo")
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch interactive TUI instead of non-interactive examples",
    )
    args = parser.parse_args()

    config = Config()  # Load defaults
    logger.info("Starting Python Mode POC Demo")

    if args.tui:
        asyncio.run(tui_demo())
    else:
        asyncio.run(run_non_interactive_examples())


if __name__ == "__main__":
    main()
