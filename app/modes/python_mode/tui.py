"""
Textual-based TUI for Python Mode prototype.

Provides an interactive interface for selecting and running Python Agent, Tool, or Flow;
inputting scripts, plugins, and parameters; viewing real-time outputs; and keyboard navigation.

Standalone and runnable via `python -m app.modes.python_mode.tui`.
"""

import asyncio
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Optional

# Debug logging for import path
print("Current working directory:", os.getcwd())
print("sys.path:", sys.path)
root_path = Path(__file__).parent.parent.parent.parent
print("Inferred root path:", root_path)
sys.path.insert(0, str(root_path))

from textual.app import App, ComposeResult, on
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

# Local imports
from app.config import Config
from app.logger import logger
from app.modes.python_mode.python_agent import PythonAgent
from app.modes.python_mode.python_flow import PythonFlow
from app.modes.python_mode.python_tool import PythonTool
from app.tool.base import ToolResult


class OutputUpdate(Message):
    """Message to update the output display."""

    def __init__(self, content: str, is_error: bool = False):
        super().__init__()
        self.content = content
        self.is_error = is_error


class PluginList(ListView):
    """ListView for selecting plugins."""

    def compose(self) -> ComposeResult:
        yield ListItem(Label("No plugins loaded"), id="plugins")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.app.set_active_plugin(event.item.id)


class PythonTUI(App):
    """Main Textual App for Python Mode TUI."""

    # CSS_PATH = "tui.css"  # Optional, but not created here
    BINDINGS = [
        Binding("ctrl+e", "execute", "Execute"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("tab", "next_focus", "Next Focus"),
        Binding("shift+tab", "previous_focus", "Previous Focus"),
    ]

    # Reactive state
    current_mode: reactive[str] = reactive("tool")  # tool, agent, flow
    active_plugins: reactive[List[str]] = reactive([])
    timeout: reactive[int] = reactive(30)
    output_content: reactive[str] = reactive("")
    script_code: reactive[str] = reactive(
        "# Enter your Python script here\nprint('Hello, Python Mode!')"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("🚀 Initializing PythonTUI application")

        logger.info("📋 Loading configuration...")
        self.config = Config()

        logger.info("🤖 Initializing PythonAgent...")
        self.agent = PythonAgent(name="tui_agent")

        logger.info("🔧 Initializing PythonTool...")
        self.tool = PythonTool()

        logger.info("🌊 Initializing PythonFlow...")
        self.flow = PythonFlow(agents={"python": self.agent})

        logger.info("📁 Setting up plugins directory...")
        self.plugins_dir = Path(__file__).parent / "plugins" / "python_actions"
        logger.info(f"🔌 Plugins directory: {self.plugins_dir}")

        logger.info("🔄 Loading plugins...")
        self.load_plugins()

        logger.info("✅ PythonTUI initialization complete")

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="main-container"):
            # Navigation Tabs
            with TabbedContent(initial="tool"):
                with TabPane("Tool", id="tool"):
                    yield from self._tool_pane()
                with TabPane("Agent", id="agent"):
                    yield from self._agent_pane()
                with TabPane("Flow", id="flow"):
                    yield from self._flow_pane()
                with TabPane("Plugins", id="plugins"):
                    yield from self._plugins_pane()

            # Output Area
            yield RichLog(id="output", markup=True)

        # Global Controls
        with Horizontal(id="controls"):
            yield Button("Execute", id="execute-btn", variant="primary")
            yield Input(
                value="30", id="timeout-input", placeholder="Timeout (s)", type="number"
            )
            yield Button("Clear Output", id="clear-output")

    def _tool_pane(self) -> ComposeResult:
        """Tool-specific pane."""
        yield Label("Script Code:")
        yield TextArea(self.script_code, id="script-input", language="python")
        yield Label("Plugins:")
        yield PluginList(id="plugin-list")
        yield Label(f"Timeout: {self.timeout}s", id="timeout-label")

    def _agent_pane(self) -> ComposeResult:
        """Agent-specific pane."""
        yield Label("Agent Input (Script):")
        yield TextArea(self.script_code, id="agent-input", language="python")
        yield Label("Plugins:")
        yield PluginList(id="agent-plugins")
        yield Label(f"Timeout: {self.timeout}s", id="agent-timeout")

    def _flow_pane(self) -> ComposeResult:
        """Flow-specific pane."""
        yield Label("Flow Input (Task):")
        yield Input(placeholder="Describe the task...", id="flow-input")
        yield Label("Plugins:")
        yield PluginList(id="flow-plugins")
        yield Label("Max Steps: 5", id="max-steps")  # Fixed for prototype

    def _plugins_pane(self) -> ComposeResult:
        """Plugins pane for viewing/managing plugins."""
        yield Label("Available Plugins:")
        yield OptionList(id="plugin-options")
        yield Button("Reload Plugins", id="reload-plugins")

    def load_plugins(self) -> None:
        """Dynamically load plugins from plugins/python_actions/ with verbose logging."""
        logger.info(f"🔌 Starting plugin loading from: {self.plugins_dir}")
        self.active_plugins = []

        if not self.plugins_dir.exists():
            logger.warning(f"❌ Plugins directory not found: {self.plugins_dir}")
            return

        plugin_files = list(self.plugins_dir.glob("*.py"))
        logger.info(f"📁 Found {len(plugin_files)} Python files in plugins directory")

        for py_file in plugin_files:
            if py_file.name == "__init__.py":
                logger.debug(f"⏭️ Skipping __init__.py file")
                continue

            plugin_name = py_file.stem
            logger.info(f"🔄 Loading plugin: {plugin_name} from {py_file.name}")

            try:
                spec = importlib.util.spec_from_file_location(plugin_name, py_file)
                if spec is None:
                    logger.error(f"❌ Failed to create spec for plugin {plugin_name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                logger.debug(f"📦 Created module for plugin {plugin_name}")

                spec.loader.exec_module(module)
                logger.debug(f"⚙️ Executed module for plugin {plugin_name}")

                # Check for register_actions function
                if hasattr(module, "register_actions"):
                    actions = module.register_actions()
                    action_names = (
                        list(actions.keys())
                        if isinstance(actions, dict)
                        else str(actions)
                    )
                    logger.info(
                        f"✅ Successfully loaded plugin {plugin_name}: {action_names}"
                    )
                    self.active_plugins.append(plugin_name)
                else:
                    logger.warning(
                        f"⚠️ Plugin {plugin_name} has no register_actions() function"
                    )

            except Exception as e:
                import traceback

                logger.error(f"❌ Failed to load plugin {plugin_name}: {str(e)}")
                logger.debug(
                    f"📋 Plugin {plugin_name} traceback:\n{traceback.format_exc()}"
                )

        logger.info(
            f"🎯 Plugin loading complete. Loaded {len(self.active_plugins)} plugins: {self.active_plugins}"
        )

    @on(Button.Pressed, "#execute-btn")
    async def execute_action(self) -> None:
        """Execute based on current mode with verbose logging."""
        mode = self.query_one(TabbedContent).active
        output_widget = self.query_one("#output", RichLog)

        # Start execution logging
        await self._log_verbose(f"🚀 Starting execution in mode: {mode}")

        try:
            if mode == "tool":
                await self._execute_tool_mode()
            elif mode == "agent":
                await self._execute_agent_mode()
            elif mode == "flow":
                await self._execute_flow_mode()
            else:
                content = f"❌ Invalid mode selected: {mode}"
                await self._log_verbose(content)
                self.post_message(OutputUpdate(content, is_error=True))
                await self._update_output(content)

        except Exception as e:
            import traceback

            error_content = f"💥 Execution Error in {mode} mode: {str(e)}"
            traceback_content = f"📋 Full traceback:\n{traceback.format_exc()}"

            # Log both to logger and TUI
            logger.error(f"{error_content}\n{traceback_content}")
            await self._log_verbose(error_content)
            await self._log_verbose(traceback_content)

            self.post_message(OutputUpdate(error_content, is_error=True))
            await self._update_output(f"{error_content}\n{traceback_content}")

    async def _execute_tool_mode(self) -> None:
        """Execute tool mode with verbose logging."""
        await self._log_verbose("🔧 Executing in Tool Mode")

        code = self.query_one("#script-input", TextArea).text
        plugins = self.active_plugins
        timeout = self.timeout

        await self._log_verbose(f"📝 Script code length: {len(code)} characters")
        await self._log_verbose(f"🔌 Active plugins: {plugins}")
        await self._log_verbose(f"⏱️ Timeout: {timeout}s")

        if not code.strip():
            await self._log_verbose("⚠️ No script code provided")
            content = "⚠️ Please enter Python code to execute"
            self.post_message(OutputUpdate(content, is_error=True))
            await self._update_output(content)
            return

        await self._log_verbose("🏃 Calling PythonTool.execute()...")
        result = await self.tool.execute(code=code, plugins=plugins, timeout=timeout)

        await self._log_verbose(
            f"✅ Tool execution completed. Has error: {bool(result.error)}"
        )
        content = self._format_result(result)
        self.post_message(OutputUpdate(content))
        await self._update_output(content)

    async def _execute_agent_mode(self) -> None:
        """Execute agent mode with verbose logging."""
        await self._log_verbose("🤖 Executing in Agent Mode")

        code = self.query_one("#agent-input", TextArea).text
        await self._log_verbose(f"📝 Agent input length: {len(code)} characters")

        if not code.strip():
            await self._log_verbose("⚠️ No agent input provided")
            content = "⚠️ Please enter input for the agent"
            self.post_message(OutputUpdate(content, is_error=True))
            await self._update_output(content)
            return

        await self._log_verbose("💾 Updating agent memory with user input...")
        self.agent.update_memory("user", code)

        await self._log_verbose("🧠 Calling PythonAgent.step()...")
        result = await self.agent.step()

        await self._log_verbose(f"✅ Agent step completed. Result type: {type(result)}")
        content = f"🤖 Agent Step Result:\n{result}"
        self.post_message(OutputUpdate(content))
        await self._update_output(content)

    async def _execute_flow_mode(self) -> None:
        """Execute flow mode with verbose logging."""
        await self._log_verbose("🌊 Executing in Flow Mode")

        task = self.query_one("#flow-input", Input).value
        await self._log_verbose(f"📝 Task description: '{task}'")

        if not task.strip():
            await self._log_verbose("⚠️ No task description provided")
            content = "⚠️ Please describe the task to execute"
            self.post_message(OutputUpdate(content, is_error=True))
            await self._update_output(content)
            return

        await self._log_verbose("⚙️ Initializing flow execution...")
        await self._log_verbose(f"🔗 Flow agents: {list(self.flow.agents.keys())}")

        await self._log_verbose("🏃 Calling PythonFlow.execute()...")
        try:
            result = await self.flow.execute(task)
            # Determine success/failure from result content
            failed = self._flow_failed(result)
            status_emoji = "❌" if failed else "✅"
            await self._log_verbose(
                f"{status_emoji} Flow execution finished. Result type: {type(result)}"
            )

            # Format flow result more verbosely
            if hasattr(result, "steps") and result.steps:
                content = f"🌊 Flow Execution Results:\n"
                content += f"📋 Task: {task}\n"
                content += f"📊 Total Steps: {len(result.steps)}\n\n"
                for i, step in enumerate(result.steps, 1):
                    content += f"Step {i}:\n{step}\n---\n"
                content += f"\n🎯 Final Result: {result.final_result if hasattr(result, 'final_result') else 'No final result'}"
            else:
                if failed:
                    content = f"[red]🌊 Flow Result (FAILED):[/red]\n{result}"
                else:
                    content = f"🌊 Flow Result:\n{result}"

        except Exception as e:
            await self._log_verbose(f"❌ Flow execution failed: {str(e)}")
            raise  # Re-raise to be caught by main exception handler

        self.post_message(OutputUpdate(content))
        await self._update_output(content)

    async def _log_verbose(self, message: str) -> None:
        """Log verbose message to both logger and TUI output."""
        # Log to application logger
        logger.info(f"[TUI] {message}")

        # Also display in TUI with timestamp
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        tui_message = f"[{timestamp}] {message}"

        # Update TUI output
        output = self.query_one("#output", RichLog)
        output.write(f"[dim]{tui_message}[/dim]")

    def _flow_failed(self, result: object) -> bool:
        """Heuristics to detect failed flow results from returned payload."""
        try:
            # Prefer explicit indicators if present
            if hasattr(result, "success"):
                return not bool(getattr(result, "success"))
            if hasattr(result, "error") and getattr(result, "error"):
                return True
        except Exception:
            pass

        # String-based heuristics
        if isinstance(result, str):
            low = result.lower()
            failure_markers = [
                "error",
                "exception",
                "traceback",
                "invalid",
                "timed out",
                "timeout",
                "failed",
                "non-zero exit",
            ]
            return any(k in low for k in failure_markers)

        return False

    def action_execute(self) -> None:
        """Execute action triggered by Ctrl+E key binding."""
        # Run the async execute_action method
        self.run_worker(self.execute_action(), exclusive=True)

    async def _update_output(self, content: str) -> None:
        """Update the output display asynchronously."""
        output = self.query_one(RichLog)
        if "error" in content.lower():
            output.write(f"[red]{content}[/red]")
        else:
            output.write(content)
        output.scroll_end(animate=False)

    def _format_result(self, result: ToolResult) -> str:
        """Format ToolResult for display with verbose information."""
        formatted = "🔧 Tool Execution Results:\n"
        formatted += "=" * 40 + "\n"

        # Show execution status
        if result.error:
            formatted += f"❌ Status: FAILED\n"
            formatted += f"🚨 Error: {result.error}\n"

            # Add error details if available
            if hasattr(result, "error_type"):
                formatted += f"📋 Error Type: {result.error_type}\n"
            if hasattr(result, "traceback"):
                formatted += f"📋 Traceback:\n{result.traceback}\n"
        else:
            formatted += f"✅ Status: SUCCESS\n"

        # Show output
        if result.output:
            formatted += f"📤 Output ({len(result.output)} chars):\n"
            formatted += f"```\n{result.output}\n```\n"
        else:
            formatted += f"📭 Output: No output generated\n"

        # Show additional data
        if result.base64_image:
            preview = (
                result.base64_image[:100] + "..."
                if len(result.base64_image) > 100
                else result.base64_image
            )
            formatted += f"🖼️ Image Data: Generated ({len(result.base64_image)} chars)\n"
            formatted += f"📋 Preview: {preview}\n"

        if hasattr(result, "execution_time"):
            formatted += f"⏱️ Execution Time: {result.execution_time}s\n"

        if hasattr(result, "memory_usage"):
            formatted += f"💾 Memory Usage: {result.memory_usage}MB\n"

        formatted += "=" * 40
        return formatted

    def watch_output_content(self, content: str) -> None:
        """Reactive watcher for output (not directly used, via messages)."""
        pass

    @on(Input.Changed, "#timeout-input")
    def update_timeout(self, event: Input.Changed) -> None:
        """Update timeout from input."""
        try:
            self.timeout = int(event.value)
        except ValueError:
            # Invalid input, keep previous value
            pass

    @on(Button.Pressed, "#clear-output")
    def clear_output(self) -> None:
        """Clear the output log."""
        self.query_one(RichLog).clear()

    @on(Button.Pressed, "#reload-plugins")
    def reload_plugins(self) -> None:
        """Reload plugins."""
        self.load_plugins()
        # Update plugin lists
        for list_view in self.query(PluginList):
            list_view.clear()
            for plugin in self.active_plugins:
                list_view.append(ListItem(Label(plugin)))
        self.notify("Plugins reloaded", title="Success", severity="information")

    def on_output_update(self, message: OutputUpdate) -> None:
        """Handle output update message."""
        self.output_content = message.content
        if message.is_error:
            self.bell()

    def on_mount(self) -> None:
        """Initialize on mount."""
        # Set initial plugins in lists
        for list_view in self.query(PluginList):
            for plugin in self.active_plugins:
                list_view.append(ListItem(Label(plugin)))
        # Focus timeout input specifically
        timeout_input = self.query_one("#timeout-input", Input)
        timeout_input.focus()

    def on_key(self, event: Key) -> None:
        """Handle global key events."""
        if event.key == "ctrl+c":
            self.exit()

    def action_quit(self) -> None:
        """Binding action for quit."""
        self.exit()


if __name__ == "__main__":
    app = PythonTUI()
    app.run()
