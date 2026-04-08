# Odoo Timesheet MCP Server — Project Context

## What this project is
An MCP server that connects AI assistants (Claude Desktop) and Voiceflow agents to Odoo ERP.
It allows natural language querying of timesheets, projects, tasks, and developer progress.

## Tech stack
- **Python 3.14**
- **MCP** (`mcp[cli]`) — for Claude Desktop integration
- **FastAPI + uvicorn** — for Voiceflow HTTP integration
- **XML-RPC** (`xmlrpc.client` built-in) — talks to Odoo
- **python-dotenv** — loads credentials from `.env`

## Project structure
```
odoo_client.py   → Core Odoo XML-RPC client (all logic lives here)
main.py          → MCP server for Claude Desktop (STDIO or HTTP transport)
api.py           → FastAPI REST server for Voiceflow
test_auth.py     → Auth debug script
generate_pdf.py  → Generates PDF docs from markdown
requirements.txt → Python dependencies
.env             → Credentials (never commit)
CLAUDE.md        → This file
```

## Odoo instance
- URL: https://erp.envnt.co
- DB: codlab
- Version: Odoo 14.0-20231106
- Auth: email + API key via XML-RPC (`/xmlrpc/2/common` and `/xmlrpc/2/object`)

## Authentication notes
- Email login is **case-sensitive** in this instance (e.g. `Youssef.Essam@codelabsys.com`)
- Uses API key, NOT password
- XML-RPC is used (not JSON-RPC) because JSON-RPC doesn't support API key auth

## Key Odoo models used
| Model | Purpose |
|---|---|
| `account.analytic.line` | Timesheets |
| `project.project` | Projects |
| `project.task` | Tasks |
| `res.users` | Users |

## Important discoveries
- `project.task` has TWO assignee fields — always filter with both:
  `["|", ["user_id", "=", uid], ["project_user_ids", "=", uid]]`
- Domain filters must use **lists** not tuples in XML-RPC
- `effective_hours` and `remaining_hours` are computed fields on `project.task`
- `list_projects` uses `["active", "=", True]` to exclude archived projects

## All MCP tools implemented
### Timesheet tools
- `authenticate` — login, must be called first
- `list_my_timesheets(limit, offset, date_from, date_to)`
- `list_timesheets_by_date(date_from, date_to, limit, offset)`
- `list_timesheets_by_project(project_id, limit, offset, date_from, date_to)`
- `create_timesheet(name, date, hours, project_id, task_id)`
- `update_timesheet(record_id, name, date, hours, project_id, task_id)`
- `delete_timesheet(record_id)`

### Project analysis tools
- `get_project(project_id)`
- `get_project_progress(project_id)` — hours per developer
- `get_project_tasks(project_id, limit, offset, stage_id, stage, deadline_from, deadline_to, keyword, user_ids)` — keyword filters on task name + description (ilike); user_ids filters by assignee

### Task tools
- `get_task_details(task_id)`
- `get_task_hours_by_user(task_id, user_id)`

### User & project tools
- `list_projects()` — always call before filtering by project
- `get_user_by_email(email)` — resolves email → user_id
- `get_user_tasks(user_id, limit, offset, project_id, stage, deadline_from, deadline_to)`
- `get_user_projects(user_id)` — projects a user logged time on
- `get_user_department(user_id)` — returns department name and job title for a user
- `get_users_by_department(department_name)` — returns all user IDs in a department (ilike match)

## Pagination
All list tools return:
```json
{ "total": 100, "offset": 0, "limit": 20, "records": [...] }
```

## Running locally
```powershell
# Test auth
py test_auth.py

# MCP Inspector (Claude Desktop testing)
C:\Users\envnt.DESKTOP-ATC6DU9\AppData\Local\Python\pythoncore-3.14-64\Scripts\mcp.exe dev main.py

# FastAPI (Voiceflow testing)
py api.py
# → http://localhost:8000/docs

# MCP over HTTP (for Voiceflow MCP integration)
py main.py streamable-http
```

## Voiceflow architecture
5 agents planned:
1. **Project Analysis Agent** — get_project, get_project_progress, get_project_tasks
2. **Timesheet Agent** — list/create/update/delete timesheets
3. **Task Analysis Agent** — get_task_details, get_task_hours_by_user
4. **Task Search Agent** — list_projects, list_stages, get_users_by_department, get_project_tasks (keyword + department filter scenario)
5. **File Upload Workflow** — no AI, pure logic

## Deployment plan
- Deploy to **Railway** (not Netlify — needs persistent server)
- Connect GitHub repo to Railway
- Set `.env` variables in Railway dashboard
- Use Railway URL in Voiceflow MCP integration

## GitHub
- Repo: https://github.com/youssefessam2000/odoo-mcp (private)

## What's pending
- [ ] Test remaining tools: list_timesheets_by_date, list_timesheets_by_project,
      create/update/delete timesheet, get_project, get_project_progress,
      get_project_tasks, get_task_details, get_task_hours_by_user
- [ ] Add optional user_id param to timesheet listing tools (for PMO use case)
- [ ] Add search_users tool (search by name instead of email)
- [x] Deploy to Railway
- [ ] Connect Voiceflow
- [x] Write agent instructions for Task Search Agent
- [ ] Write agent instructions for remaining 4 agents
- [ ] Full documentation PDF
