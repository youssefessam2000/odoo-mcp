import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from odoo_client import OdooClient

load_dotenv()

mcp = FastMCP("Odoo Tasks", host="0.0.0.0")

client = OdooClient(
    base_url=os.getenv("ODOO_BASE_URL", ""),
    db=os.getenv("ODOO_DB", ""),
    email=os.getenv("ODOO_EMAIL", ""),
    api_key=os.getenv("ODOO_API_KEY", ""),
)


# ── Project & Department Tools ─────────────────────────────────────────────


@mcp.tool()
def list_projects() -> list:
    """List all active projects with their IDs and names.
    Always call this first before filtering by project so you get the correct project ID.
    """
    return client.list_projects()


@mcp.tool()
def list_stages(project_id: int | None = None) -> list:
    """List all task stages (kanban columns) available in Odoo.
    Call this after selecting a project to show phases as buttons.

    Args:
        project_id: If provided, only return stages belonging to that project (optional).
    """
    return client.list_stages(project_id=project_id)


@mcp.tool()
def list_phases(project_id: int) -> list:
    """List all phases for a specific project. Call this to show phases as buttons.

    Args:
        project_id: The Odoo project ID (from list_projects).
    """
    return client.list_phases(project_id=project_id)


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


# ── Task Tools ─────────────────────────────────────────────────────────────


@mcp.tool()
def get_project_tasks(project_id: int, limit: int = 50, offset: int = 0,
                      stage_id: int | None = None,
                      phase_id: int | None = None,
                      deadline_from: str | None = None,
                      deadline_to: str | None = None,
                      keyword: str | None = None,
                      user_ids: list[int] | None = None) -> dict:
    """Get tasks in a project with optional filters and pagination.

    Args:
        project_id:    The Odoo project ID.
        limit:         Max tasks per page (default 50).
        offset:        Skip N tasks for pagination (default 0).
        stage_id:      Filter by kanban stage ID (from list_stages) (optional).
        phase_id:      Filter by phase/sprint ID (from list_phases) (optional).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
        keyword:       Filter tasks whose name or description contains this keyword (optional).
        user_ids:      Filter tasks assigned to any of these user IDs (optional).
    """
    return client.get_project_tasks(project_id=project_id, limit=limit, offset=offset,
                                    stage_id=stage_id, phase_id=phase_id,
                                    deadline_from=deadline_from, deadline_to=deadline_to,
                                    keyword=keyword, user_ids=user_ids)


@mcp.tool()
def get_project_summary(project_id: int) -> dict:
    """Get a compact project summary for agent analysis — works for any project size.
    Returns task counts by stage, overdue tasks, unassigned/no-estimate counts,
    and workload per developer. Use this instead of fetching raw tasks.

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_project_summary(project_id=project_id)


@mcp.tool()
def get_all_project_tasks(project_id: int) -> dict:
    """Fetch ALL tasks for a project with no filters or pagination.
    Internally loops through pages and returns everything in one response.
    Warning: slow for large projects (100+ tasks).

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_all_project_tasks(project_id=project_id)


@mcp.tool()
def get_project_task_count(project_id: int) -> dict:
    """Get the total number of tasks for a specific project.

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_project_task_count(project_id=project_id)


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


@mcp.tool()
def get_tasks_by_stage(stage_id: int, project_id: int | None = None,
                       limit: int = 20, offset: int = 0,
                       deadline_from: str | None = None,
                       deadline_to: str | None = None) -> dict:
    """Get all tasks in a specific stage (by stage ID).

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


@mcp.tool()
def get_tasks_by_phase_number(project_id: int, phase_number: int,
                              limit: int = 20, offset: int = 0,
                              deadline_from: str | None = None,
                              deadline_to: str | None = None) -> dict:
    """Get tasks in the Nth stage of a project by position (1 = first stage, 2 = second, etc.).

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
def get_user_tasks(user_id: int, limit: int = 20, offset: int = 0,
                   project_id: int | None = None, stage_id: int | None = None,
                   deadline_from: str | None = None, deadline_to: str | None = None) -> dict:
    """Get tasks assigned to a specific user with optional filters and pagination.

    Args:
        user_id:       The Odoo user ID.
        limit:         Max tasks per page (default 20).
        offset:        Skip N tasks for pagination (default 0).
        project_id:    Filter by project ID (optional).
        stage_id:      Filter by stage ID (from list_stages) (optional).
        deadline_from: Filter tasks with deadline from this date YYYY-MM-DD (optional).
        deadline_to:   Filter tasks with deadline up to this date YYYY-MM-DD (optional).
    """
    return client.get_user_tasks(user_id=user_id, limit=limit, offset=offset,
                                  project_id=project_id, stage_id=stage_id,
                                  deadline_from=deadline_from, deadline_to=deadline_to)


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

    Args:
        project_id: The Odoo project ID.
    """
    return client.get_project_progress(project_id=project_id)


@mcp.tool()
def get_user_projects(user_id: int) -> list:
    """Get all projects a user has logged time on, with total hours per project.

    Args:
        user_id: The Odoo user ID.
    """
    return client.get_user_projects(user_id=user_id)


@mcp.tool()
def get_user_by_email(email: str) -> dict:
    """Resolve a user's email to their Odoo user ID and name.

    Args:
        email: The user's Odoo login email.
    """
    return client.get_user_by_email(email=email)


@mcp.tool()
def get_user_department(user_id: int) -> dict:
    """Get the department of a user by their Odoo user ID.

    Args:
        user_id: The Odoo user ID.
    """
    return client.get_user_department(user_id=user_id)


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
