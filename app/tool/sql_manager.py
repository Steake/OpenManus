"""SQL Connection Manager for SQL Tools.

Manages stateful connections using SQLAlchemy engines.
Connections are stored by connection_id (UUID) for reuse across tool calls.
"""

import uuid
from typing import Dict, Optional

from sqlalchemy import create_engine, engine
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.logger import logger

# Global store for connections (stateful across tool executions)
_connections: Dict[str, engine.Engine] = {}
_connection_configs: Dict[str, Dict] = {}  # Store config for reference


def create_connection(
    driver: str,
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    ssl_mode: Optional[str] = None,
) -> str:
    """
    Create a new SQLAlchemy engine and store it with a unique connection_id.

    Args:
        driver: Database driver, e.g., 'postgresql', 'mysql', 'sqlite'.
        host: Database host (ignored for SQLite).
        port: Database port (ignored for SQLite).
        dbname: Database name or :memory: for SQLite.
        user: Username (ignored for SQLite).
        password: Password (ignored for SQLite).
        ssl_mode: Optional SSL mode (e.g., 'require').

    Returns:
        str: Unique connection_id.

    Raises:
        ValueError: If connection creation fails.
    """
    # Build connection URL
    if driver == "sqlite":
        if dbname == ":memory:":
            url = "sqlite:///:memory:"
        else:
            url = f"sqlite:///{dbname}"
        # SQLite ignores host, port, user, password
        info = url
    else:
        url = f"{driver}://{user}:{password}@{host}:{port}/{dbname}"
        info = f"{driver}://{host}:{port}/{dbname}"
        if ssl_mode:
            url += f"?sslmode={ssl_mode}"

    try:
        engine_obj = create_engine(url, echo=False)  # No echo for security
        connection_id = str(uuid.uuid4())
        _connections[connection_id] = engine_obj
        masked_url = (
            url.replace(f":{password}@", ":***@")
            if driver != "sqlite" and password
            else url
        )
        _connection_configs[connection_id] = {
            "url": masked_url,  # Masked password
            "driver": driver,
        }
        masked_info = (
            info.replace(f":{password}@", ":***@")
            if driver != "sqlite" and password
            else info
        )
        logger.info(f"Created connection {connection_id} for {driver}:{masked_info}")
        return connection_id
    except OperationalError as e:
        logger.error(f"Failed to create connection: {e}")
        raise ValueError(f"Connection failed: {str(e)}")


def get_connection(connection_id: str) -> engine.Engine:
    """
    Retrieve a stored engine by connection_id.

    Args:
        connection_id: The ID from create_connection.

    Returns:
        engine.Engine: The SQLAlchemy engine.

    Raises:
        KeyError: If connection_id not found.
    """
    if connection_id not in _connections:
        raise KeyError(f"Connection {connection_id} not found. Create it first.")
    return _connections[connection_id]


def dispose_connection(connection_id: str) -> None:
    """
    Close and remove a connection.

    Args:
        connection_id: The ID to dispose.
    """
    if connection_id in _connections:
        _connections[connection_id].dispose()
        del _connections[connection_id]
        if connection_id in _connection_configs:
            del _connection_configs[connection_id]
        logger.info(f"Disposed connection {connection_id}")


def list_connections() -> list:
    """List all active connection_ids."""
    return list(_connections.keys())


def clear_all_connections() -> None:
    """Clear all connections (for cleanup or reset)."""
    for conn_id in list(_connections.keys()):
        dispose_connection(conn_id)


# Optional: Graceful shutdown hook (can be called at app end)
def shutdown():
    clear_all_connections()
