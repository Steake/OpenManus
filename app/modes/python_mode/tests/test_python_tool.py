import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modes.python_mode.python_tool import PythonTool
from app.sandbox.core.sandbox import DockerSandbox
from app.tool.base import BaseTool, ToolResult


@pytest.mark.asyncio
class TestPythonTool:
    """Unit tests for PythonTool."""

    @pytest.fixture
    def tool(self):
        """Fixture for a basic PythonTool instance."""
        return PythonTool()

    def test_inheritance_from_base_tool(self):
        """Test that PythonTool inherits from BaseTool."""
        assert issubclass(PythonTool, BaseTool)
        tool = PythonTool()
        assert isinstance(tool, BaseTool)

    def test_name_and_description(self):
        """Test tool name and description."""
        tool = PythonTool()
        assert tool.name == "python_execute"
        assert "Execute Python code in a secure sandbox" in tool.description

    def test_parameters_schema(self):
        """Test the parameters schema."""
        tool = PythonTool()
        params = tool.parameters
        assert params["required"] == ["code"]
        assert "plugins" in params["properties"]
        assert "timeout" in params["properties"]
        assert "generate_image" in params["properties"]

    @pytest.mark.asyncio
    async def test_execute_valid_code_no_plugins(self, tool):
        """Test execute() with valid code, no plugins, default timeout."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="Hello from Python!")

        with patch(
            "app.modes.python_mode.python_tool.DockerSandbox", return_value=mock_sandbox
        ):
            result = await tool.execute(code="print('Hello from Python!')")

        assert isinstance(result, ToolResult)
        assert result.output == "Hello from Python!"
        assert result.error is None
        assert result.base64_image is None
        mock_sandbox.write_file.assert_called_with(
            "script.py", "print('Hello from Python!')"
        )
        mock_sandbox.run_command.assert_called_with("python script.py", timeout=30)

    @pytest.mark.asyncio
    async def test_execute_invalid_code(self, tool):
        """Test execute() with invalid Python syntax."""
        result = await tool.execute(code="invalid syntax")

        assert isinstance(result, ToolResult)
        assert "Invalid Python syntax." == result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_with_plugins(self, tool):
        """Test execute() with plugins loading."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="Output with plugins")

        with patch(
            "app.modes.python_mode.python_tool.DockerSandbox", return_value=mock_sandbox
        ), patch.object(tool, "_load_plugins", AsyncMock(return_value=["example"])):
            result = await tool.execute(
                code="print('test')", plugins=["example"], timeout=20
            )

        assert result.output == "Output with plugins"
        tool._load_plugins.assert_called_with(["example"])

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tool):
        """Test execute() with timeout error."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch(
            "app.modes.python_mode.python_tool.DockerSandbox", return_value=mock_sandbox
        ):
            result = await tool.execute(code="print('test')", timeout=10)

        assert f"Execution timed out after 10s" == result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_general_exception(self, tool):
        """Test execute() with general exception."""
        with patch("app.modes.python_mode.python_tool.DockerSandbox") as mock_sandbox:
            mock_sandbox.side_effect = Exception("Sandbox error")

            result = await tool.execute(code="print('test')")

        assert "Sandbox error" == result.error

    @pytest.mark.asyncio
    async def test_execute_with_generate_image(self, tool):
        """Test execute() with generate_image=True and matplotlib in code."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="Plot generated")
        mock_sandbox.copy_from = AsyncMock()

        with patch(
            "app.modes.python_mode.python_tool.DockerSandbox", return_value=mock_sandbox
        ), patch(
            "app.modes.python_mode.python_tool.open", create=True
        ) as mock_open, patch(
            "app.modes.python_mode.python_tool.base64.b64encode",
            return_value=b"image_data",
        ), patch.object(
            tool,
            "_generate_visualization",
            AsyncMock(return_value="data:image/png;base64,image_data"),
        ):
            result = await tool.execute(
                code="import matplotlib.pyplot as plt\nplt.plot([1,2])\nplt.savefig('plot.png')",
                generate_image=True,
            )

        assert result.base64_image == "data:image/png;base64,image_data"
        tool._generate_visualization.assert_called_once_with(mock_sandbox)

    @pytest.mark.asyncio
    async def test_execute_generate_image_no_matplotlib(self, tool):
        """Test execute() with generate_image=True but no matplotlib in code."""
        mock_sandbox = AsyncMock()
        mock_sandbox.write_file = AsyncMock()
        mock_sandbox.run_command = AsyncMock(return_value="No plot")

        with patch(
            "app.modes.python_mode.python_tool.DockerSandbox", return_value=mock_sandbox
        ):
            result = await tool.execute(code="print('no plot')", generate_image=True)

        assert result.base64_image is None

    def test_validate_code_valid(self, tool):
        """Test _validate_code with valid Python code."""
        code = "print('valid')"
        is_valid = tool._validate_code(code)

        assert is_valid is True

    def test_validate_code_invalid(self, tool):
        """Test _validate_code with invalid Python code."""
        code = "invalid syntax"
        is_valid = tool._validate_code(code)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_load_plugins_success(self, tool):
        """Test _load_plugins with valid plugin."""
        with patch("app.modes.python_mode.python_tool.__import__") as mock_import:
            mock_module = MagicMock()
            mock_module.register_actions.return_value = {"process_data": lambda x: x}
            mock_import.return_value = mock_module

            loaded = await tool._load_plugins(["example"])

        assert loaded == ["example"]
        mock_import.assert_called_with(
            "app.modes.python_mode.plugins.python_actions.example", fromlist=[""]
        )

    @pytest.mark.asyncio
    async def test_load_plugins_failure(self, tool):
        """Test _load_plugins with invalid plugin."""
        with patch(
            "app.modes.python_mode.python_tool.__import__", side_effect=ImportError
        ):
            loaded = await tool._load_plugins(["invalid"])

        assert loaded == []

    @pytest.mark.asyncio
    async def test_generate_visualization_success(self, tool):
        """Test _generate_visualization with successful image copy and encode."""
        mock_sandbox = AsyncMock()
        mock_sandbox.copy_from = AsyncMock()

        with patch(
            "app.modes.python_mode.python_tool.open", create=True
        ) as mock_open, patch(
            "app.modes.python_mode.python_tool.base64.b64encode",
            return_value=b"fake_image",
        ), patch(
            "builtins.open", mock_open
        ):
            mock_file = MagicMock()
            mock_file.read.return_value = b"file_content"
            mock_open.return_value.__enter__.return_value = mock_file

            result = await tool._generate_visualization(mock_sandbox)

        assert (
            result == "data:image/png;base64,ZmFrZV9pbWFnZQ=="
        )  # base64 of b"fake_image"
        mock_sandbox.copy_from.assert_called_with("plot.png", "/tmp/sandbox_plot.png")

    @pytest.mark.asyncio
    async def test_generate_visualization_failure(self, tool):
        """Test _generate_visualization with failure (no file)."""
        mock_sandbox = AsyncMock()
        mock_sandbox.copy_from = AsyncMock(side_effect=Exception("No plot file"))

        result = await tool._generate_visualization(mock_sandbox)

        assert result is None
