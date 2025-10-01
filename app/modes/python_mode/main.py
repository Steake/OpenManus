"""
Simple standalone test script for Python Mode prototype.

This script demonstrates independent usage of the core components:
- PythonAgent for script execution
- PythonTool for sandboxed code runs
- PythonFlow for sequenced executions
- Example plugin action

Run with: python app/modes/python_mode/main.py
Requires the app/ modules to be importable (e.g., run from project root).
"""

import asyncio

from app.modes.python_mode.plugins.python_actions.example_plugin import process_data
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow
from app.modes.python_mode.python_tool import PythonTool


async def test_agent():
    """Test PythonAgent standalone."""
    agent = PythonAgent(name="test_agent")
    result = await agent.run("Execute: print('Hello from Python Agent!')")
    print("Agent Test Result:")
    print(result)


async def test_tool():
    """Test PythonTool standalone."""
    tool = PythonTool()
    code = """
print("Hello from Python Tool!")
# Simple data manipulation
data = [1, 2, 3]
print(sum(data))
"""
    result = await tool.execute(code=code, timeout=10)
    print("Tool Test Result:")
    print(result)


async def test_flow():
    """Test PythonFlow standalone."""
    flow = PythonFlow()
    input_text = "Process data: hello world with plugin"
    result = await flow.execute(input_text)
    print("Flow Test Result:")
    print(result)


async def test_plugin():
    """Test example plugin standalone."""
    result = process_data("hello world", prefix="PLUGIN:")
    print("Plugin Test Result:")
    print(result)


async def main():
    """Run all tests."""
    print("Testing Python Mode Prototype...")
    await test_agent()
    await test_tool()
    await test_flow()
    await test_plugin()
    print("\nAll tests completed. Prototype is functional and standalone.")


if __name__ == "__main__":
    asyncio.run(main())
