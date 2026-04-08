import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from odoo_client import OdooClient

load_dotenv()

mcp = FastMCP("Odoo Timesheet", host="0.0.0.0")

client = OdooClient(
    base_url=os.getenv("ODOO_BASE_URL", ""),
    db=os.getenv("ODOO_DB", ""),
    email=os.getenv("ODOO_EMAIL", ""),
    api_key=os.getenv("ODOO_API_KEY", ""),
)


@mcp.tool()
def authenticate() -> dict:
    """Authenticate with Odoo using email and API key. Must be called first."""
    return client.authenticate()


@mcp.tool()
def list_my_timesheets(limit: int = 20, offset: int = 0,
                       date_from: str | None = None, date_to: str | None = None) -> dict:
    """List the current user's timesheet entries with optional date filter and pagination.

    Args:
        limit:     Max entries per page (default 20).
        offset:    Skip N entries for pagination (default 0).
        date_from: Filter from this date — YYYY-MM-DD (optional).
        date_to:   Filter to this date — YYYY-MM-DD (optional).
    """
    return client.list_my_timesheets(limit=limit, offset=offset, date_from=date_from, date_to=date_to)


@mcp.tool()
def list_timesheets_by_date(date_from: str, date_to: str,
                             limit: int = 100, offset: int = 0) -> dict:
    """List timesheet entries within a date range.

    Args:
        date_from: Start date in YYYY-MM-DD format.
        date_to:   End date in YYYY-MM-DD format.
        limit:     Max entries per page (default 100).
        offset:    Skip N entries for pagination (default 0).
    """
    return client.list_timesheets_by_date(date_from=date_from, date_to=date_to, limit=limit, offset=offset)


@mcp.tool()
def list_timesheets_by_project(project_id: int, limit: int = 50, offset: int = 0,
                                date_from: str | None = None, date_to: str | None = None) -> dict:
    """List timesheet entries for a specific project with optional date filter and pagination.

    Args:
        project_id: The Odoo project ID.
        limit:      Max entries per page (default 50).
        offset:     Skip N entries for pagination (default 0).
        date_from:  Filter from this date — YYYY-MM-DD (optional).
        date_to:    Filter to this date — YYYY-MM-DD (optional).
    """
    return client.list_timesheets_by_project(project_id=project_id, limit=limit, offset=offset,
                                              date_from=date_from, date_to=date_to)


@mcp.tool()
def create_timesheet(
    name: str,
    date: str,
    hours: float,
    project_id: int,
    task_id: int,
) -> dict:
    """Create a new timesheet entry.

    Args:
        name:       Description / task name.
        date:       Date in YYYY-MM-DD format.
        hours:      Hours logged (e.g. 2.5).
        project_id: Odoo project ID.
        task_id:    Odoo task ID.
    """
    record_id = client.create_timesheet(
        name=name,
        date=date,
        unit_amount=hours,
        project_id=project_id,
        task_id=task_id,
    )
    return {"created_id": record_id}


@mcp.tool()
def update_timesheet(
    record_id: int,
    name: str | None = None,
    date: str | None = None,
    hours: float | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
) -> dict:
    """Update an existing timesheet entry. Only pass the fields you want to change.

    Args:
        record_id:  ID of the timesheet entry to update.
        name:       New description.
        date:       New date in YYYY-MM-DD format.
        hours:      New hours logged.
        project_id: New project ID.
        task_id:    New task ID.
    """
    values = {}
    if name is not None:
        values["name"] = name
    if date is not None:
        values["date"] = date
    if hours is not None:
        values["unit_amount"] = hours
    if project_id is not None:
        values["project_id"] = project_id
    if task_id is not None:
        values["task_id"] = task_id

    if not values:
        return {"updated": False, "reason": "No fields provided to update."}

    success = client.update_timesheet(record_id=record_id, values=values)
    return {"updated": success}


@mcp.tool()
def delete_timesheet(record_id: int) -> dict:
    """Delete a timesheet entry by its ID.

    Args:
        record_id: ID of the timesheet entry to delete.
    """
    success = client.delete_timesheet(record_id=record_id)
    return {"deleted": success}


# ── Project & User Tools ───────────────────────────────────────────────────


@mcp.tool()
def list_projects() -> list:
    """List all active projects with their IDs and names.
    Always call this first before filtering by project so you get the correct project ID.
    """
    return client.list_projects()


@mcp.tool()
def get_user_tasks(user_id: int, limit: int = 20, offset: int = 0,
                   project_id: int | None = None, stage: str | None = None,
                   deadline_from: str | None = None, deadline_to: str | None = None) -> dict:
    """Get tasks assigned to a specific user with optional filters and pagination.

    Args:
        user_id:       The Odoo user ID (get it first from get_user_by_email).
        limit:         Max tasks per page (default 20).
        offset:        Skip N tasks for pagination (default 0).
        project_id:    Filter by project ID (optional).
        stage:         Filter by stage name e.g. 'In Progress' (optional).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
    """
    return client.get_user_tasks(user_id=user_id, limit=limit, offset=offset,
                                  project_id=project_id, stage=stage,
                                  deadline_from=deadline_from, deadline_to=deadline_to)


@mcp.tool()
def get_user_projects(user_id: int) -> list:
    """Get all projects a user has logged time on, with total hours per project.

    Args:
        user_id: The Odoo user ID (get it first from get_user_by_email).
    """
    return client.get_user_projects(user_id=user_id)


@mcp.tool()
def list_departments() -> list:
    """List all departments. Call this to show departments as buttons before filtering by department."""
    return client.list_departments()


@mcp.tool()
def get_users_by_department(department_id: int) -> list:
    """Get all users (with their Odoo user IDs) belonging to a department.

    Use this after the user selects a department from buttons (list_departments).

    Args:
        department_id: The Odoo department ID (from list_departments).
    """
    return client.get_users_by_department(department_id=department_id)


@mcp.tool()
def get_user_department(user_id: int) -> dict:
    """Get the department of a user by their Odoo user ID.

    Args:
        user_id: The Odoo user ID (get it first from get_user_by_email).
    """
    return client.get_user_department(user_id=user_id)


@mcp.tool()
def get_user_by_email(email: str) -> dict:
    """Resolve a user's email to their Odoo user ID and name.
    Always call this when a user mentions a developer by email before calling any user-specific tool.

    Args:
        email: The user's Odoo login email.
    """
    return client.get_user_by_email(email=email)


# ── Project Analysis Tools ─────────────────────────────────────────────────


@mcp.tool()
def get_project(project_id: int) -> dict:
    """Get project details by project ID.

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_project(project_id=project_id)


@mcp.tool()
def get_project_progress(project_id: int) -> list:
    """Get total hours logged per developer on a project.

    Returns each developer's name and how many hours they've logged.

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_project_progress(project_id=project_id)


@mcp.tool()
def get_project_tasks(project_id: int, limit: int = 20, offset: int = 0,
                      stage_id: int | None = None, stage: str | None = None,
                      deadline_from: str | None = None,
                      deadline_to: str | None = None,
                      keyword: str | None = None,
                      user_ids: list[int] | None = None) -> dict:
    """Get tasks in a project with optional filters and pagination.

    Args:
        project_id:    The Odoo project ID.
        limit:         Max tasks per page (default 20).
        offset:        Skip N tasks for pagination (default 0).
        stage_id:      Filter by stage ID — preferred over stage name (optional).
        stage:         Filter by stage name e.g. 'Done' — used only if stage_id not provided (optional).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
        keyword:       Filter tasks whose name contains this keyword e.g. 'bug fixing' (optional).
        user_ids:      Filter tasks assigned to any of these user IDs (optional).
    """
    return client.get_project_tasks(project_id=project_id, limit=limit, offset=offset,
                                    stage_id=stage_id, stage=stage,
                                    deadline_from=deadline_from, deadline_to=deadline_to,
                                    keyword=keyword, user_ids=user_ids)


@mcp.tool()
def get_task_details(task_id: int) -> dict:
    """Get full details of a task including estimate, actual hours, remaining hours, and progress %.

    Args:
        task_id: The Odoo task ID.
    """
    return client.get_task_details(task_id=task_id)


@mcp.tool()
def get_task_progress(task_id: int) -> dict:
    """Get planned hours, total hours spent, and per-developer breakdown for a task.

    Args:
        task_id: The Odoo task ID.
    """
    return client.get_task_progress(task_id=task_id)


@mcp.tool()
def get_task_hours_by_user(task_id: int, user_id: int) -> dict:
    """Get how many hours a specific user has logged on a specific task.

    Args:
        task_id: The Odoo task ID.
        user_id: The Odoo user ID of the developer.
    """
    return client.get_task_hours_by_user(task_id=task_id, user_id=user_id)


# ── Stage Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def list_stages(project_id: int | None = None) -> list:
    """List all task stages (kanban columns) available in Odoo.
    Call this first to get stage IDs before using get_tasks_by_stage.

    Args:
        project_id: If provided, only return stages belonging to that project (optional).
    """
    return client.list_stages(project_id=project_id)


@mcp.tool()
def get_tasks_by_phase_number(project_id: int, phase_number: int,
                              limit: int = 20, offset: int = 0,
                              deadline_from: str | None = None,
                              deadline_to: str | None = None) -> dict:
    """Get tasks in the Nth stage of a project by position (1 = first stage, 2 = second, etc.).

    Call list_stages(project_id) first to see how many phases the project has.

    Args:
        project_id:    The Odoo project ID.
        phase_number:  Position of the stage (1-based).
        limit:         Max tasks per page (default 20).
        offset:        Skip N tasks for pagination (default 0).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
    """
    return client.get_tasks_by_phase_number(project_id=project_id, phase_number=phase_number,
                                            limit=limit, offset=offset,
                                            deadline_from=deadline_from, deadline_to=deadline_to)


@mcp.tool()
def get_tasks_by_stage(stage_id: int, project_id: int | None = None,
                       limit: int = 20, offset: int = 0,
                       deadline_from: str | None = None,
                       deadline_to: str | None = None) -> dict:
    """Get all tasks in a specific stage (by stage ID).

    Call list_stages first to get the correct stage ID.
    Can optionally be scoped to a single project.

    Args:
        stage_id:      The Odoo stage ID (from list_stages).
        project_id:    Scope to a specific project (optional).
        limit:         Max tasks per page (default 20).
        offset:        Skip N tasks for pagination (default 0).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
    """
    return client.get_tasks_by_stage(stage_id=stage_id, project_id=project_id,
                                     limit=limit, offset=offset,
                                     deadline_from=deadline_from, deadline_to=deadline_to)


class FixHostMiddleware:
    """Replace external Host header with localhost so FastMCP's host check passes."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope)
            scope["headers"] = [
                (b"host", b"localhost") if k == b"host" else (k, v)
                for k, v in scope.get("headers", [])
            ]
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        import uvicorn
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(FixHostMiddleware(mcp.streamable_http_app()), host="0.0.0.0", port=port)
    else:
        mcp.run(transport=transport)
