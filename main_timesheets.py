import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from odoo_client import OdooClient

load_dotenv()

mcp = FastMCP("Odoo Timesheets", host="0.0.0.0")

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


@mcp.tool()
def get_user_by_email(email: str) -> dict:
    """Resolve a user's email to their Odoo user ID and name.

    Args:
        email: The user's Odoo login email.
    """
    return client.get_user_by_email(email=email)


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
