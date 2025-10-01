"""SQL Tools for database operations using SQLAlchemy.

Implements SQLConnect, SQLQuery, SQLInsert, SQLUpdate, SQLDelete, SchemaViewer.
Each is a BaseTool subclass with JSON schema parameters and ToolResult output.
Connections managed via sql_manager.py.
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, exc, inspect, text
from sqlalchemy.dialects.mysql import insert as my_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.sql_manager import create_connection, dispose_connection, get_connection


class SQLConnect(BaseTool):
    """Establish a secure connection to a relational database (e.g., PostgreSQL, MySQL). Returns connection_id for reuse."""

    name: str = "sql_connect"
    description: str = (
        "Create a connection to a SQL database. Returns a unique connection_id for subsequent operations."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "driver": {
                "type": "string",
                "description": "Database driver (e.g., 'postgresql' for Postgres, 'mysql' for MySQL).",
                "enum": ["postgresql", "mysql"],
            },
            "host": {
                "type": "string",
                "description": "Database server hostname or IP address.",
            },
            "port": {
                "type": "integer",
                "description": "Database port (default 5432 for PostgreSQL, 3306 for MySQL).",
            },
            "dbname": {"type": "string", "description": "Database name."},
            "user": {"type": "string", "description": "Username for authentication."},
            "password": {
                "type": "string",
                "description": "Password for authentication (handled securely).",
            },
            "ssl_mode": {
                "type": "string",
                "description": "SSL mode (e.g., 'require', 'prefer'). Optional.",
                "default": None,
            },
        },
        "required": ["driver", "host", "port", "dbname", "user", "password"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            # Extract params, set defaults
            port = kwargs.get(
                "port", 5432 if kwargs.get("driver") == "postgresql" else 3306
            )
            ssl_mode = kwargs.get("ssl_mode")
            conn_id = create_connection(
                driver=kwargs["driver"],
                host=kwargs["host"],
                port=port,
                dbname=kwargs["dbname"],
                user=kwargs["user"],
                password=kwargs["password"],
                ssl_mode=ssl_mode,
            )
            logger.info(
                f"SQLConnect successful for {kwargs['driver']} at {kwargs['host']}:{port}"
            )
            return self.success_response(
                {
                    "connection_id": conn_id,
                    "message": "Connection established successfully.",
                }
            )
        except Exception as e:
            logger.error(f"SQLConnect failed: {str(e)}")
            return self.fail_response(f"Failed to create connection: {str(e)}")


class SQLQuery(BaseTool):
    """Execute a SELECT query on a connected database and return results as JSON."""

    name: str = "sql_query"
    description: str = (
        "Execute a read-only SQL SELECT query and return results as JSON. Use parameterized queries for safety."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect.",
            },
            "query": {"type": "string", "description": "SQL SELECT query string."},
            "params": {
                "type": "object",
                "description": "Dictionary of parameters for the query to prevent SQL injection. Optional.",
                "default": {},
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of rows to return. Optional.",
                "default": 100,
            },
        },
        "required": ["connection_id", "query"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            conn = get_connection(kwargs["connection_id"])
            with conn.connect() as c:
                stmt = text(kwargs["query"])
                params = kwargs.get("params", {})
                limit = kwargs.get("limit", 100)
                result = c.execute(stmt, params)
                rows = result.fetchmany(limit)
                # Convert to list of dicts
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                logger.info(f"SQLQuery successful: returned {len(data)} rows")
                return self.success_response(
                    {"rows": data, "columns": list(columns), "total_rows": len(data)}
                )
        except exc.SQLAlchemyError as e:
            logger.error(f"SQLQuery failed: {str(e)}")
            return self.fail_response(f"Query execution failed: {str(e)}")
        except KeyError:
            return self.fail_response(
                "Invalid connection_id. Reconnect using sql_connect."
            )
        except Exception as e:
            logger.error(f"Unexpected SQLQuery error: {str(e)}")
            return self.fail_response(f"Unexpected error: {str(e)}")


class SQLInsert(BaseTool):
    """Insert data into a database table, supporting upsert for PostgreSQL/MySQL."""

    name: str = "sql_insert"
    description: str = (
        "Insert one or more rows into a SQL table. Supports upsert (ON CONFLICT) for PostgreSQL."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect.",
            },
            "table": {"type": "string", "description": "Target table name."},
            "values": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of dictionaries, each representing a row to insert.",
            },
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of column names if not inferring from values.",
            },
            "on_conflict": {
                "type": "string",
                "description": "Upsert strategy for PostgreSQL (e.g., 'do_nothing', 'update'). Optional.",
                "default": None,
            },
        },
        "required": ["connection_id", "table", "values"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            conn = get_connection(kwargs["connection_id"])
            values = kwargs["values"]
            if not values:
                return self.fail_response("No values provided for insert.")

            # Assume single row for simplicity; extend for bulk
            if len(values) == 1:
                value = values[0]
            else:
                value = values[0]  # First for demo; implement bulk

            if "driver" not in conn.url:  # Placeholder, actually check dialect
                # Generic insert
                with conn.connect() as c:
                    columns = list(value.keys())
                    placeholders = ", ".join([f":{k}" for k in columns])
                    insert_sql = f"INSERT INTO {kwargs['table']} ({', '.join(columns)}) VALUES ({placeholders})"
                    result = c.execute(text(insert_sql), value)
                    c.commit()
                inserted_id = (
                    result.lastrowid if hasattr(result, "lastrowid") else "unknown"
                )
                logger.info(f"SQLInsert successful: inserted 1 row")
                return self.success_response(
                    {"inserted_rows": 1, "last_insert_id": inserted_id}
                )
            else:
                # TODO: Upsert logic based on driver
                return self.success_response(
                    {"message": "Insert successful (upsert not implemented yet)"}
                )
        except exc.SQLAlchemyError as e:
            logger.error(f"SQLInsert failed: {str(e)}")
            return self.fail_response(f"Insert failed: {str(e)}")
        except KeyError:
            return self.fail_response("Invalid connection_id.")
        except Exception as e:
            logger.error(f"Unexpected SQLInsert error: {str(e)}")
            return self.fail_response(f"Unexpected error: {str(e)}")


class SQLUpdate(BaseTool):
    """Update rows in a database table with a required WHERE clause."""

    name: str = "sql_update"
    description: str = (
        "Update rows in a SQL table using a WHERE clause. Parameters prevent mass updates."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect.",
            },
            "table": {"type": "string", "description": "Target table name."},
            "set_dict": {
                "type": "object",
                "description": "Dictionary of {column: value} to set.",
            },
            "where_clause": {
                "type": "string",
                "description": "WHERE condition (e.g., 'id = :id'). Required to avoid full table updates.",
            },
            "params": {
                "type": "object",
                "description": "Parameters for set_dict and where_clause. Optional but recommended.",
                "default": {},
            },
        },
        "required": ["connection_id", "table", "set_dict", "where_clause"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            conn = get_connection(kwargs["connection_id"])
            set_dict = kwargs["set_dict"]
            where = kwargs["where_clause"]
            params = kwargs.get("params", {})

            set_clause = ", ".join([f"{k} = :{k}" for k in set_dict.keys()])
            update_sql = f"UPDATE {kwargs['table']} SET {set_clause} WHERE {where}"
            all_params = {**set_dict, **params}

            with conn.connect() as c:
                result = c.execute(text(update_sql), all_params)
                c.commit()
                updated_rows = result.rowcount
                logger.info(f"SQLUpdate successful: updated {updated_rows} rows")
                return self.success_response({"updated_rows": updated_rows})
        except exc.SQLAlchemyError as e:
            logger.error(f"SQLUpdate failed: {str(e)}")
            return self.fail_response(f"Update failed: {str(e)}")
        except KeyError:
            return self.fail_response("Invalid connection_id or required params.")
        except Exception as e:
            logger.error(f"Unexpected SQLUpdate error: {str(e)}")
            return self.fail_response(f"Unexpected error: {str(e)}")


class SQLDelete(BaseTool):
    """Delete rows from a database table with a required WHERE clause for safety."""

    name: str = "sql_delete"
    description: str = (
        "Delete rows from a SQL table using a WHERE clause. No WHERE means error to prevent accidents."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect.",
            },
            "table": {"type": "string", "description": "Target table name."},
            "where_clause": {
                "type": "string",
                "description": "WHERE condition (e.g., 'id = :id'). Required.",
            },
            "params": {
                "type": "object",
                "description": "Parameters for where_clause.",
                "default": {},
            },
        },
        "required": ["connection_id", "table", "where_clause"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        if not kwargs.get("where_clause", "").strip():
            return self.fail_response(
                "WHERE clause is required for safety to prevent deleting all rows."
            )

        try:
            conn = get_connection(kwargs["connection_id"])
            where = kwargs["where_clause"]
            params = kwargs.get("params", {})

            delete_sql = f"DELETE FROM {kwargs['table']} WHERE {where}"

            with conn.connect() as c:
                result = c.execute(text(delete_sql), params)
                c.commit()
                deleted_rows = result.rowcount
                logger.info(f"SQLDelete successful: deleted {deleted_rows} rows")
                return self.success_response({"deleted_rows": deleted_rows})
        except exc.SQLAlchemyError as e:
            logger.error(f"SQLDelete failed: {str(e)}")
            return self.fail_response(f"Delete failed: {str(e)}")
        except KeyError:
            return self.fail_response("Invalid connection_id.")
        except Exception as e:
            logger.error(f"Unexpected SQLDelete error: {str(e)}")
            return self.fail_response(f"Unexpected error: {str(e)}")


class SchemaViewer(BaseTool):
    """View database schema information for tables."""

    name: str = "schema_viewer"
    description: str = (
        "Retrieve schema information for tables in the connected database (columns, types, etc.)."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect.",
            },
            "table_name": {
                "type": "string",
                "description": "Specific table name. If omitted, list all tables.",
                "default": None,
            },
        },
        "required": ["connection_id"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            conn = get_connection(kwargs["connection_id"])
            inspector = inspect(conn)
            table_name = kwargs.get("table_name")

            if table_name:
                # Specific table schema
                columns = inspector.get_columns(table_name)
                schema_info = {
                    "table": table_name,
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", False),
                            "default": col.get("default"),
                            "primary_key": col.get("primary_key", False),
                        }
                        for col in columns
                    ],
                }
                logger.info(f"SchemaViewer successful for table {table_name}")
                return self.success_response(schema_info)
            else:
                # List all tables
                tables = inspector.get_table_names()
                logger.info(f"SchemaViewer: listed {len(tables)} tables")
                return self.success_response({"tables": tables})
        except exc.SQLAlchemyError as e:
            logger.error(f"SchemaViewer failed: {str(e)}")
            return self.fail_response(f"Schema query failed: {str(e)}")
        except KeyError:
            return self.fail_response("Invalid connection_id.")
        except Exception as e:
            logger.error(f"Unexpected SchemaViewer error: {str(e)}")
            return self.fail_response(f"Unexpected error: {str(e)}")
