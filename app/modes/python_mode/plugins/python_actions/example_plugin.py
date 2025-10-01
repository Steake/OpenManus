"""
Example plugin for Python Mode demonstrating custom actions.

This plugin provides a simple data processing function that can be loaded
and called dynamically in PythonTool or PythonFlow. For prototype, it includes
a basic processing action. Extend with more functions as needed.
"""

from typing import Any, Dict


def process_data(data: str, **kwargs) -> str:
    """
    Example custom action: Process input data (e.g., simple transformation).

    Args:
        data: Input data string.
        **kwargs: Additional parameters (e.g., {'format': 'json'}).

    Returns:
        Processed data as string.
    """
    # Basic processing: uppercase and add prefix
    processed = data.upper()
    prefix = kwargs.get("prefix", "PROCESSED:")
    return f"{prefix} {processed}"


def register_actions() -> Dict[str, callable]:
    """
    Register available actions in this plugin.

    Returns:
        Dict of action names to functions.
    """
    return {"process_data": process_data}


# For dynamic loading, expose the module's actions
__all__ = ["process_data", "register_actions"]
