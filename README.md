# Odoo Timesheet MCP Server

A Model Context Protocol (MCP) server that connects AI assistants (like Claude) to Odoo's Timesheet module.

---

## How It Works

### Protocol: XML-RPC (not GraphQL)

This is **not GraphQL**. Here's a quick comparison:

| | GraphQL | REST | XML-RPC (what we use) |
|---|---|---|---|
| Request format | GraphQL query language | HTTP verbs + URLs | XML over HTTP POST |
| Flexible fields | Yes | No | Yes (via `fields` param) |
| Single endpoint | Yes | No | Yes |
| Built into Odoo | No | No | Yes (native) |

**XML-RPC** (Remote Procedure Call) means you call a function on a remote server by name and pass arguments — like calling a Python function over the internet. Odoo has supported it since version 6.

### Why XML-RPC over JSON-RPC?

The Postman collection used JSON-RPC with session cookies and a password. We switched to XML-RPC because:
- It supports **API key authentication** (more secure than passwords)
- No session management needed (stateless)
- Official Odoo external API standard

---

## Architecture

```
You (chat with Claude)
        │
        ▼
   Claude (AI)
        │  speaks MCP protocol
        ▼
  MCP Server (main.py)        ← this project
        │  speaks XML-RPC
        ▼
   Odoo ERP (erp.envnt.co)
        │
        ▼
  account.analytic.line       ← Timesheet model in Odoo database
```

### MCP Protocol

MCP (Model Context Protocol) is an open standard by Anthropic. It lets AI assistants discover and call external tools. The flow is:

1. Claude receives your message
2. Claude sees your available tools (authenticate, list_my_timesheets, etc.)
3. Claude decides which tool to call based on your message
4. MCP server executes the tool and returns the result
5. Claude reads the result and responds to you

---

## Authentication

Authentication uses **email + API key** via Odoo's XML-RPC endpoint.

```
POST https://erp.envnt.co/xmlrpc/2/common
Method: authenticate(db, email, api_key, {})
Returns: uid (user ID integer)
```

Once authenticated, every subsequent call uses `uid + api_key` — no session, no cookies.

**To generate an API key in Odoo:**
Settings → My Profile → Account Security → API Keys → New API Key

---

## Endpoints Used

All data calls go to a single endpoint:

```
POST https://erp.envnt.co/xmlrpc/2/object
Method: execute_kw(db, uid, api_key, model, method, args, kwargs)
```

### Odoo Model

All timesheet tools operate on:
```
Model: account.analytic.line
```

### Fields returned

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique record ID |
| `name` | String | Description / task name |
| `date` | Date | Date of work (YYYY-MM-DD) |
| `unit_amount` | Float | Hours logged |
| `project_id` | [id, name] | Project reference |
| `task_id` | [id, name] | Task reference |
| `employee_id` | [id, name] | Employee reference |

---

## MCP Tools

### `authenticate`
Logs in and stores the user session. Call this first.

**Input:** none (reads from .env)
**Output:**
```json
{ "uid": 1784, "authenticated": true }
```

---

### `list_my_timesheets`
Returns timesheet entries for the authenticated user.

**Input:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 20 | Max entries to return |

**Output:** Array of timesheet entries

---

### `list_timesheets_by_date`
Returns entries within a date range.

**Input:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date_from` | string | Yes | Start date (YYYY-MM-DD) |
| `date_to` | string | Yes | End date (YYYY-MM-DD) |
| `limit` | integer | No (100) | Max entries to return |

---

### `list_timesheets_by_project`
Returns entries for a specific project.

**Input:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | integer | Yes | Odoo project ID |
| `limit` | integer | No (50) | Max entries to return |

---

### `create_timesheet`
Creates a new timesheet entry.

**Input:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Description of work done |
| `date` | string | Yes | Date (YYYY-MM-DD) |
| `hours` | float | Yes | Hours logged (e.g. 2.5) |
| `project_id` | integer | Yes | Odoo project ID |
| `task_id` | integer | Yes | Odoo task ID |

**Output:**
```json
{ "created_id": 98765 }
```

---

### `update_timesheet`
Updates an existing entry. Only pass fields you want to change.

**Input:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `record_id` | integer | Yes | ID of the entry to update |
| `name` | string | No | New description |
| `date` | string | No | New date |
| `hours` | float | No | New hours |
| `project_id` | integer | No | New project ID |
| `task_id` | integer | No | New task ID |

**Output:**
```json
{ "updated": true }
```

---

### `delete_timesheet`
Deletes a timesheet entry permanently.

**Input:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `record_id` | integer | Yes | ID of the entry to delete |

**Output:**
```json
{ "deleted": true }
```

---

## Project Structure

```
odoo-mcp/
├── main.py          # MCP server — tool definitions
├── odoo_client.py   # XML-RPC client — talks to Odoo
├── test_auth.py     # Auth debug script
├── .env             # Credentials (never commit this)
├── .env.example     # Credentials template
└── requirements.txt # Python dependencies
```

## Dependencies

| Package | Purpose |
|---|---|
| `mcp[cli]` | MCP server framework |
| `python-dotenv` | Load .env credentials |

> `xmlrpc.client` is built into Python — no install needed.

---

## Running

### Development (with Inspector UI)
```powershell
C:\Users\envnt.DESKTOP-ATC6DU9\AppData\Local\Python\pythoncore-3.14-64\Scripts\mcp.exe dev main.py
```

### Connect to Claude Desktop
Add to `%APPDATA%/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "odoo-timesheet": {
      "command": "py",
      "args": ["D:/projects/odoo-mcp/main.py"]
    }
  }
}
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `ODOO_BASE_URL` | Odoo instance URL |
| `ODOO_DB` | Database name |
| `ODOO_EMAIL` | Login email (case-sensitive) |
| `ODOO_API_KEY` | API key from Odoo profile |
