"""Basic unit tests for sql_tools using in-memory SQLite for demonstration."""

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

import json

import pytest
from sqlalchemy import text

from app.tool.base import ToolResult
from app.tool.sql_manager import create_connection, get_connection
from app.tool.sql_tools import (
    SchemaViewer,
    SQLConnect,
    SQLDelete,
    SQLInsert,
    SQLQuery,
    SQLUpdate,
)


@pytest.mark.asyncio
async def test_sql_connect():
    """Test SQLConnect tool instantiation and basic execution with SQLite."""
    tool = SQLConnect()
    assert tool.name == "sql_connect"
    assert "Create a connection" in tool.description

    result = await tool.execute(
        driver="sqlite", host="", port=0, dbname=":memory:", user="", password=""
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "connection_id" in output
    assert output["connection_id"] is not None


@pytest.mark.asyncio
async def test_sql_query_success():
    """Test SQLQuery with a successful SELECT."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup DB
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.execute(text("INSERT INTO test (name) VALUES ('test1')"))
        c.commit()

    tool = SQLQuery()

    result = await tool.execute(
        connection_id=conn_id, query="SELECT * FROM test WHERE name = 'test1'"
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "rows" in output
    assert len(output["rows"]) == 1
    assert output["rows"][0]["name"] == "test1"


@pytest.mark.asyncio
async def test_sql_query_invalid_conn():
    """Test SQLQuery with invalid connection_id."""
    tool = SQLQuery()
    result = await tool.execute(connection_id="invalid_id", query="SELECT 1")
    assert isinstance(result, ToolResult)
    assert result.error
    assert "Invalid connection_id" in result.error


@pytest.mark.asyncio
async def test_sql_insert_success():
    """Test SQLInsert with basic insert using SQLite."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup table
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.commit()

    tool = SQLInsert()

    result = await tool.execute(
        connection_id=conn_id, table="test", values=[{"name": "new_test"}]
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "inserted_rows" in output
    assert output["inserted_rows"] == 1


@pytest.mark.asyncio
async def test_sql_update_success():
    """Test SQLUpdate with WHERE clause."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup table and initial data
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.execute(text("INSERT INTO test (name) VALUES ('to_update')"))
        c.commit()

    tool = SQLUpdate()

    result = await tool.execute(
        connection_id=conn_id,
        table="test",
        set_dict={"name": "updated"},
        where_clause="name = 'to_update'",
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "updated_rows" in output
    assert output["updated_rows"] == 1


@pytest.mark.asyncio
async def test_sql_delete_success():
    """Test SQLDelete with WHERE clause."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup table and data
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.execute(text("INSERT INTO test (name) VALUES ('to_delete')"))
        c.commit()

    tool = SQLDelete()

    result = await tool.execute(
        connection_id=conn_id, table="test", where_clause="name = 'to_delete'"
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "deleted_rows" in output
    assert output["deleted_rows"] == 1


@pytest.mark.asyncio
async def test_sql_delete_no_where():
    """Test SQLDelete requires WHERE clause."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")
    tool = SQLDelete()
    result = await tool.execute(connection_id=conn_id, table="test", where_clause="")
    assert isinstance(result, ToolResult)
    assert result.error
    assert "WHERE clause is required" in result.error


@pytest.mark.asyncio
async def test_schema_viewer_tables():
    """Test SchemaViewer lists tables."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup table
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.commit()

    tool = SchemaViewer()

    result = await tool.execute(connection_id=conn_id)
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "tables" in output
    assert len(output["tables"]) == 1  # SQLite includes 'test'


@pytest.mark.asyncio
async def test_schema_viewer_specific_table():
    """Test SchemaViewer for a specific table."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")

    # Setup table
    engine = get_connection(conn_id)
    with engine.connect() as c:
        c.execute(
            text("CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        )
        c.commit()

    tool = SchemaViewer()

    result = await tool.execute(connection_id=conn_id, table_name="test")
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "columns" in output
    assert len(output["columns"]) > 0
    assert any(col["name"] == "id" for col in output["columns"])


if __name__ == "__main__":
    pytest.main([__file__])
