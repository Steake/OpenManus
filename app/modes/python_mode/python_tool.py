import ast
import asyncio
import base64
from typing import Any, Dict, Optional

from pydantic import Field

from app.config import Config
from app.logger import logger
from app.sandbox.core.sandbox import DockerSandbox
from app.tool.base import BaseTool, ToolResult


class PythonTool(BaseTool):
    """
    A tool for executing Python code snippets in a sandboxed environment.

    Inherits from BaseTool. Supports plugin loading and returns structured outputs
    including stdout, errors, and optional base64 images for visualizations.
    Uses DockerSandbox for isolation with default memory limits.
    """

    name: str = "python_execute"
    description: str = (
        "Execute Python code in a secure sandbox. Supports data processing and simple visualizations."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "plugins": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of plugin names to load",
            },
            "timeout": {
                "type": "number",
                "description": "Execution timeout in seconds",
                "default": 30,
            },
            "generate_image": {
                "type": "boolean",
                "description": "Generate visualization image if applicable",
                "default": False,
            },
        },
        "required": ["code"],
    }

    def __init__(self, **data):
        super().__init__(**data)
        logger.info(f"Initialized PythonTool")

    async def execute(
        self,
        code: str,
        plugins: Optional[list] = None,
        timeout: int = 30,
        generate_image: bool = False,
    ) -> ToolResult:
        """
        Execute the Python code in sandbox.

        Args:
            code: Python code snippet.
            plugins: List of plugins to load (e.g., ['data_process']).
            timeout: Execution timeout.
            generate_image: If True, attempt to generate a base64 image (e.g., from matplotlib).

        Returns:
            ToolResult with output, error, or base64_image.
        """
        try:
            # Validate code
            if not self._validate_code(code):
                return ToolResult(error="Invalid Python syntax.")

            # Load plugins if provided
            if plugins:
                loaded_plugins = await self._load_plugins(plugins)
                logger.info(f"Loaded plugins: {loaded_plugins}")

            # Execute in sandbox
            sandbox = DockerSandbox()  # Uses default config with memory limits
            async with sandbox:
                # Write code to file
                await sandbox.write_file("script.py", code)

                # Run script, capture stdout/stderr
                cmd = f"python script.py"
                output = await asyncio.wait_for(
                    sandbox.run_command(cmd, timeout=timeout), timeout=timeout
                )

                # Handle image generation if requested (basic matplotlib example)
                base64_image = None
                if generate_image and "matplotlib" in code.lower():
                    base64_image = await self._generate_visualization(sandbox)

                logger.info("Python execution successful")
                return ToolResult(output=output, base64_image=base64_image)

        except asyncio.TimeoutError:
            logger.warning("Python execution timed out")
            return ToolResult(error=f"Execution timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Python tool execution error: {e}")
            return ToolResult(error=str(e))

    def _validate_code(self, code: str) -> bool:
        """Validate Python code using ast.parse."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.warning(f"Code validation failed: {e}")
            return False

    async def _load_plugins(self, plugin_names: list) -> list:
        """Load and register plugins dynamically."""
        loaded = []
        for name in plugin_names:
            try:
                # Assume plugins are in plugins/python_actions/
                module = __import__(
                    f"app.modes.python_mode.plugins.python_actions.{name}",
                    fromlist=[""],
                )
                # Register actions (placeholder for prototype)
                loaded.append(name)
                logger.info(f"Loaded plugin: {name}")
            except ImportError:
                logger.warning(f"Failed to load plugin: {name}")
        return loaded

    async def _generate_visualization(self, sandbox: DockerSandbox) -> Optional[str]:
        """Generate base64 image from sandbox (e.g., save plot and encode)."""
        try:
            # Assume plot saved as 'plot.png' in code
            await sandbox.copy_from("plot.png", "/tmp/sandbox_plot.png")
            with open("/tmp/sandbox_plot.png", "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{image_data}"
        except Exception as e:
            logger.warning(f"Image generation failed: {e}")
            return None
