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
odoo_client.py          → Core Odoo XML-RPC client (all logic lives here)
main.py                 → Original MCP server (all tools combined)
main_tasks.py           → MCP server #1 — Tasks, projects, stages, departments (16 tools)
main_timesheets.py      → MCP server #2 — Timesheets + auth (8 tools)
api.py                  → FastAPI REST server for Voiceflow
test_auth.py            → Auth debug script
generate_pdf.py         → Generates PDF docs from markdown
requirements.txt        → Python dependencies
department_75_users.json → Cached users for Web Development Department (167 users)
.env                    → Credentials (never commit)
CLAUDE.md               → This file
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
| `project.phase` | Phases/sprints per project |
| `res.users` | Users |
| `hr.employee` | Employees (used to resolve department) |
| `hr.department` | Departments |

## Important discoveries
- `project.task` has TWO assignee fields — always filter with both:
  `["|", ["user_id", "=", uid], ["project_user_ids", "=", uid]]`
- Domain filters must use **lists** not tuples in XML-RPC
- OR operator (`|`) must be at top level — use `domain += ["|", [...], [...]]` NOT `.append(["|", [...], [...]])`
- `effective_hours` and `remaining_hours` are computed fields on `project.task`
- `list_projects` uses `["active", "=", True]` to exclude archived projects
- Tasks have no `department_id` field — department filtering must go through `hr.employee` → `user_id`
- All filters use IDs not names (stage_id, department_id, project_id) — name params removed to avoid fuzzy matching issues
- keyword filter uses OR on name + description: `["|", ["name", "ilike", kw], ["description", "ilike", kw]]`
- `project.phase` has no `sequence` field — order by `id asc` instead
- `res.users.login` is the email field

## Department filtering — important note
- `get_users_by_department(department_id)` returns all employees in a department
- Web Development Department (id=75) has **167 users** — passing all as `user_ids` to `get_project_tasks` may be slow
- **Recommended approach:** filter by project + phase + keyword first, then filter results client-side in Voiceflow by checking if assignee is in the department user list

## get_project_tasks — enriched response
Each task record now returns full data for analysis:
```json
{
  "task_id": 101,
  "task_name": "Fix login bug",
  "priority": "high",
  "assignee": { "user_id": 42, "name": "Ahmed Ali", "email": "ahmed@company.com" },
  "all_assignees": [{ "user_id": 42, "name": "Ahmed Ali", "email": "ahmed@company.com" }],
  "stage": "In Progress",
  "phase": "Sprint 3",
  "deadline": "2026-04-15",
  "estimated_hours": 8.0,
  "actual_hours": 5.5,
  "remaining_hours": 2.5,
  "progress_pct": 68.8,
  "hours_by_developer": [
    { "user_id": 42, "name": "Ahmed Ali", "email": "ahmed@company.com", "hours_logged": 5.5 }
  ]
}
```
- `hours_by_developer` is fetched from `account.analytic.line` in one batch query — sorted descending by hours
- `all_assignees` uses `project_user_ids` (multi-assign support)
- User emails resolved from `res.users` in one batch query, reused across assignees + timesheet users

## All MCP tools implemented

### main_tasks.py (16 tools)
- `list_projects()` — all active projects
- `list_stages(project_id)` — kanban stages, optionally filtered by project
- `list_phases(project_id)` — sprints/phases for a project (ordered by id asc)
- `list_departments()` — all departments, use for buttons
- `get_users_by_department(department_id)` — users in a department by ID (exact match, not fuzzy)
- `get_user_department(user_id)` — department of a specific user
- `get_user_by_email(email)` — resolves email → user_id
- `get_project(project_id)` — project details
- `get_project_progress(project_id)` — hours per developer on a project
- `get_project_tasks(project_id, limit, offset, stage_id, phase_id, deadline_from, deadline_to, keyword, user_ids)` — enriched task list with hours_by_developer
- `get_task_details(task_id)` — full task info
- `get_task_progress(task_id)` — hours breakdown per developer
- `get_task_hours_by_user(task_id, user_id)` — hours a user logged on a task
- `get_tasks_by_stage(stage_id, project_id, limit, offset, deadline_from, deadline_to)`
- `get_tasks_by_phase_number(project_id, phase_number, limit, offset, deadline_from, deadline_to)`
- `get_user_tasks(user_id, limit, offset, project_id, stage_id, deadline_from, deadline_to)`
- `get_user_projects(user_id)` — projects a user logged time on

### main_timesheets.py (8 tools)
- `authenticate` — login, must be called first
- `list_my_timesheets(limit, offset, date_from, date_to)`
- `list_timesheets_by_date(date_from, date_to, limit, offset)`
- `list_timesheets_by_project(project_id, limit, offset, date_from, date_to)`
- `create_timesheet(name, date, hours, project_id, task_id)`
- `update_timesheet(record_id, name, date, hours, project_id, task_id)`
- `delete_timesheet(record_id)`
- `get_user_by_email(email)` — resolves email → user_id

## Pagination
All list tools return:
```json
{ "total": 100, "offset": 0, "limit": 20, "records": [...] }
```
- Default limit is 20, use 50 for broader queries
- Never use unlimited — Odoo always requires a limit value
- For "show more" UX: increment offset by limit on each request

## Running locally
```powershell
# Test auth
py test_auth.py

# MCP Inspector (Claude Desktop testing)
C:\Users\envnt.DESKTOP-ATC6DU9\AppData\Local\Python\pythoncore-3.14-64\Scripts\mcp.exe dev main_tasks.py

# Tasks MCP over HTTP
py main_tasks.py streamable-http

# Timesheets MCP over HTTP
py main_timesheets.py streamable-http
```

## Deployment — Railway
- **odoo-tasks-mcp** service → start command: `python main_tasks.py streamable-http`
- **odoo-timesheets-mcp** service → start command: `python main_timesheets.py streamable-http`
- Both services connected to same GitHub repo: `youssefessam2000/odoo-mcp`
- Auto-deploys on every push to main
- Live URL: `https://odoo-mcp-production-fc43.up.railway.app` (tasks service)
- Set `.env` variables in Railway dashboard for each service

## Voiceflow architecture

### Task Search + Analysis Flow
**5-step flow:** project → phase → stage → department → fetch + analyze tasks

**Tool call sequence:**
1. `list_projects()` → user picks project → save `project_id`
2. `list_phases(project_id)` → render as buttons → save `phase_id`
3. `list_stages(project_id)` → render as buttons → save `stage_id`
4. `list_departments()` → render as buttons → save `department_id`
5. `get_users_by_department(department_id)` → extract `user_ids`
6. `get_project_tasks(project_id, phase_id, stage_id, keyword, user_ids, limit=50)` → pass to analysis agent

**Important Voiceflow lesson:**
- Agent internal memory ≠ Voiceflow `{variable}` state
- MCP tool `defaultValue` in tool config overrides the variable — **never set a defaultValue of "0" or any fallback on required fields**
- To pass variables between agents: use a **Set Variable** step before calling the next agent/tool
- `captureInputVariables` captures the tool's input back into a variable after the call (may coerce int → string, this is fine)

**Note:** If department has many users (e.g. 167 in dept 75), consider filtering client-side in Voiceflow instead of passing all user_ids to the tool.

### Task Analysis Agent prompt
> You are a project task analysis assistant. You receive a list of tasks from a software project and your job is to analyze them and give the project manager a clear, actionable summary.
>
> **What to analyze:**
> - **Overdue tasks** — tasks where the deadline has passed and progress is below 100%
> - **At-risk tasks** — tasks where actual hours exceeded estimated hours, or remaining hours are high relative to deadline
> - **No estimate** — tasks with 0 estimated hours (can't track progress)
> - **Unassigned tasks** — tasks with no assignee
> - **Workload distribution** — which developers have the most tasks or most remaining hours
> - **Top contributors per task** — use `hours_by_developer` to identify who is carrying the task
> - **High priority tasks** — any tasks marked high priority and their current status
>
> **Output format:**
> 1. **Summary** — total tasks, completed, in-progress, overdue
> 2. **Overdue / At-risk** — task name, assignee, deadline, progress %
> 3. **Workload per developer** — name, email, number of tasks, total hours logged
> 4. **Recommendations** — 2-3 actionable points for the project manager
>
> Be concise. Use bullet points. Always mention developer name and email when flagging issues.

## GitHub
- Repo: https://github.com/youssefessam2000/odoo-mcp (private)

## What's pending
- [ ] Test remaining tools end-to-end
- [ ] Add optional user_id param to timesheet listing tools (for PMO use case)
- [ ] Add search_users tool (search by name instead of email)
- [x] Deploy to Railway
- [x] Write agent instructions for Task Search Agent
- [x] Fix Voiceflow variable passing (defaultValue bug)
- [x] Enrich get_project_tasks with assignee emails + hours_by_developer
- [ ] Connect full Voiceflow 5-step flow end-to-end and test
- [ ] Decide on department filtering approach (server-side vs client-side) for large departments
- [ ] Full documentation PDF
