# Ideas for New Database Interaction Tools

Based on analysis of existing tools (no direct DB support, relying on indirect methods like python_execute), here are brainstormed ideas for new tools focused on SQL (relational, e.g., PostgreSQL, MySQL) and NoSQL (MongoDB). These fill gaps in querying, modifications, schema management, and utilities. Each is structured with name, description, required parameters, optional parameters, and notes on MCP feasibility/integration.

## Relational SQL Tools

### 1. SQLConnect
**Description**: Establish a secure connection to a relational database (e.g., PostgreSQL, MySQL). Returns a connection_id for subsequent operations.
**Required Parameters**:
- host: Database server hostname or IP.
- port: Port number (default 5432 for PostgreSQL, 3306 for MySQL).
- dbname: Database name.
- user: Username for authentication.
- password: Password (handle securely via env vars in implementation).
**Optional Parameters**:
- ssl_mode: SSL configuration (e.g., require, prefer).
**MCP Feasibility/Integration**: High feasibility using SQLAlchemy as a wrapper in python_execute tool initially. For production, create a dedicated MCP server for connection pooling and persistent sessions to avoid repeated auth.

### 2. SQLQuery
**Description**: Execute read-only queries (SELECT, JOIN, etc.) and return results as structured JSON.
**Required Parameters**:
- connection_id: ID from SQLConnect.
- query: SQL SELECT query string.
**Optional Parameters**:
- params: Dictionary for parameterized queries to prevent SQL injection.
- limit: Max rows to return.
**MCP Feasibility/Integration**: High; execute via connected DB engine, parse results to JSON. Integrate with existing tool_collection.py for schema enforcement.

### 3. SQLInsert
**Description**: Insert data into a table with validation.
**Required Parameters**:
- connection_id: Active connection.
- table: Target table name.
- columns: List of column names.
- values: List/dict of values to insert (JSON serializable).
**Optional Parameters**:
- on_conflict: Strategy for duplicates (e.g., do_nothing, update).
**MCP Feasibility/Integration**: High; use parameterized INSERT statements. Security: Validate input types against schema.

### 4. SQLUpdate
**Description**: Update existing records with conditions to avoid mass updates.
**Required Parameters**:
- connection_id: Active connection.
- table: Target table.
- set_dict: Dictionary of {column: value} to update.
- where_clause: Condition string (e.g., "id = %s").
**Optional Parameters**:
- params: Values for where_clause parameterization.
**MCP Feasibility/Integration**: High; enforce WHERE clause requirement to prevent accidental overwrites.

### 5. SQLDelete
**Description**: Delete records safely with conditions.
**Required Parameters**:
- connection_id: Active connection.
- table: Target table.
- where_clause: Condition for deletion.
**Optional Parameters**:
- params: Parameter values for where_clause.
**MCP Feasibility/Integration**: High; mandatory WHERE to ensure safety. Log deletions for auditing.

### 6. SchemaViewer
**Description**: Retrieve and describe table schemas (columns, types, constraints).
**Required Parameters**:
- connection_id: Active connection.
**Optional Parameters**:
- table_name: Specific table; if omitted, list all.
**MCP Feasibility/Integration**: Medium-high; query INFORMATION_SCHEMA or use DESCRIBE. Output as JSON for easy parsing.

## NoSQL MongoDB Tools

### 7. MongoConnect
**Description**: Establish connection to MongoDB instance/cluster.
**Required Parameters**:
- uri: Full connection URI (mongodb:// or mongodb+srv://).
- Or individual: host, port, dbname, user, password.
**Optional Parameters**:
- auth_source: Auth database (default: admin).
**MCP Feasibility/Integration**: High with PyMongo. Similar to SQLConnect; MCP server for replica set handling.

### 8. MongoFind
**Description**: Query documents in a collection, returning JSON array.
**Required Parameters**:
- connection_id: From MongoConnect.
- collection: Target collection name.
- filter: Query filter (JSON dict).
**Optional Parameters**:
- projection: Fields to include.
- limit: Max documents.
- sort: Sort order (JSON).
**MCP Feasibility/Integration**: High; convert BSON to JSON. Supports aggregation pipelines for complex queries.

### 9. MongoInsert
**Description**: Insert one or multiple documents into a collection.
**Required Parameters**:
- connection_id: Active connection.
- collection: Target collection.
- documents: Single dict or list of dicts (JSON).
**Optional Parameters**:
- ordered: Insert sequentially (default true).
**MCP Feasibility/Integration**: High; handle bulk inserts for efficiency.

### 10. MongoUpdate
**Description**: Update documents by filter (supports upsert).
**Required Parameters**:
- connection_id: Active connection.
- collection: Target collection.
- filter: Query filter dict.
- update_dict: Update operators (e.g., {"$set": {...}}).
**Optional Parameters**:
- upsert: Insert if no match (default false).
- multi: Update multiple docs (default false).
**MCP Feasibility/Integration**: High; atomic operations via PyMongo. Validate update syntax.

### 11. MongoDelete
**Description**: Delete documents matching filter.
**Required Parameters**:
- connection_id: Active connection.
- collection: Target collection.
- filter: Deletion filter dict.
**Optional Parameters**:
- limit: Max deletions.
- just_one: Delete only first match (default false).
**MCP Feasibility/Integration**: High; confirm deletions in logs.

## Utility Tools

### 12. DBBackup
**Description**: Export schema and/or data to file (SQL dump or JSON).
**Required Parameters**:
- connection_id: Active connection.
- format: "sql" or "json".
**Optional Parameters**:
- tables/collections: Comma-separated list to backup.
- output_path: File path for dump.
**MCP Feasibility/Integration**: Medium; use DB-specific tools (pg_dump via bash, or PyMongo export). Size limits for large DBs; integrate with file_operators.py.

### 13. TransactionManager
**Description**: Execute a batch of operations within a transaction, with commit/rollback.
**Required Parameters**:
- connection_id: Active connection.
- operations: List of CRUD tool calls (e.g., [{"type": "insert", "params": {...}}]).
**Optional Parameters**:
- isolation_level: Transaction isolation (e.g., read_committed).
**MCP Feasibility/Integration**: Medium-complex; maintain state across tool calls. Use DB context managers; dedicated MCP for long-running txns.

## Overall Feasibility and Recommendations
- **Security**: All tools must use parameterized queries, credential encryption (e.g., via config.toml), and input sanitization. Avoid raw SQL/Mongo queries where possible.
- **Integration**: Start with python_execute for prototypes (add DB libs like sqlalchemy, pymongo to requirements.txt). Evolve to MCP servers (e.g., npx for DB-specific servers) for better performance/isolation.
- **Gaps Covered**: Direct CRUD without shell scripting; schema awareness for AI planning; batch ops for complex workflows.
- **Priorities**: Implement SQL tools first (broader use), then Mongo. Test with sandbox environments.

These ideas can be prototyped in code mode.
