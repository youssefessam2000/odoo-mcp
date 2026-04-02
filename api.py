import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from odoo_client import OdooClient

load_dotenv()

# ── App setup ──────────────────────────────────────────────────────────────

app = FastAPI(title="Odoo Timesheet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API key protection (for Voiceflow to authenticate with your server) ────

API_KEY = os.getenv("SERVER_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str = Security(api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key

# ── Odoo client (auto-authenticates on first request) ─────────────────────

client = OdooClient(
    base_url=os.getenv("ODOO_BASE_URL", ""),
    db=os.getenv("ODOO_DB", ""),
    email=os.getenv("ODOO_EMAIL", ""),
    api_key=os.getenv("ODOO_API_KEY", ""),
)

# ── Request models ─────────────────────────────────────────────────────────

class CreateTimesheetRequest(BaseModel):
    name: str
    date: str
    hours: float
    project_id: int
    task_id: int

class UpdateTimesheetRequest(BaseModel):
    name: str | None = None
    date: str | None = None
    hours: float | None = None
    project_id: int | None = None
    task_id: int | None = None

# ── Health check ───────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "Odoo Timesheet API"}

# ── Timesheet endpoints ────────────────────────────────────────────────────

@app.get("/timesheets/my")
def list_my_timesheets(limit: int = 20, _key=Security(require_api_key)):
    """List the authenticated user's timesheet entries."""
    try:
        return client.list_my_timesheets(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/timesheets/by-date")
def list_timesheets_by_date(date_from: str, date_to: str, limit: int = 100, _key=Security(require_api_key)):
    """List timesheet entries within a date range (YYYY-MM-DD)."""
    try:
        return client.list_timesheets_by_date(date_from=date_from, date_to=date_to, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/timesheets/by-project/{project_id}")
def list_timesheets_by_project(project_id: int, limit: int = 50, _key=Security(require_api_key)):
    """List timesheet entries for a specific project."""
    try:
        return client.list_timesheets_by_project(project_id=project_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/timesheets")
def create_timesheet(body: CreateTimesheetRequest, _key=Security(require_api_key)):
    """Create a new timesheet entry."""
    try:
        record_id = client.create_timesheet(
            name=body.name,
            date=body.date,
            unit_amount=body.hours,
            project_id=body.project_id,
            task_id=body.task_id,
        )
        return {"created_id": record_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/timesheets/{record_id}")
def update_timesheet(record_id: int, body: UpdateTimesheetRequest, _key=Security(require_api_key)):
    """Update an existing timesheet entry."""
    try:
        values = {}
        if body.name is not None:
            values["name"] = body.name
        if body.date is not None:
            values["date"] = body.date
        if body.hours is not None:
            values["unit_amount"] = body.hours
        if body.project_id is not None:
            values["project_id"] = body.project_id
        if body.task_id is not None:
            values["task_id"] = body.task_id
        if not values:
            return {"updated": False, "reason": "No fields provided."}
        return {"updated": client.update_timesheet(record_id=record_id, values=values)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/timesheets/{record_id}")
def delete_timesheet(record_id: int, _key=Security(require_api_key)):
    """Delete a timesheet entry."""
    try:
        return {"deleted": client.delete_timesheet(record_id=record_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── Project & User endpoints ───────────────────────────────────────────────

@app.get("/projects")
def list_projects(_key=Security(require_api_key)):
    """List all active projects with their IDs and names."""
    try:
        return client.list_projects()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/{user_id}/tasks")
def get_user_tasks(user_id: int, _key=Security(require_api_key)):
    """Get all tasks assigned to a specific user."""
    try:
        return client.get_user_tasks(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/{user_id}/projects")
def get_user_projects(user_id: int, _key=Security(require_api_key)):
    """Get all projects a user has logged time on."""
    try:
        return client.get_user_projects(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/by-email")
def get_user_by_email(email: str, _key=Security(require_api_key)):
    """Resolve a user's email to their Odoo user ID."""
    try:
        return client.get_user_by_email(email=email)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Project analysis endpoints ─────────────────────────────────────────────

@app.get("/projects/{project_id}")
def get_project(project_id: int, _key=Security(require_api_key)):
    """Get project details by ID."""
    try:
        return client.get_project(project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}/progress")
def get_project_progress(project_id: int, _key=Security(require_api_key)):
    """Get hours logged per developer on a project."""
    try:
        return client.get_project_progress(project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}/tasks")
def get_project_tasks(project_id: int, _key=Security(require_api_key)):
    """Get all tasks in a project with estimated vs actual hours."""
    try:
        return client.get_project_tasks(project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── Task endpoints ─────────────────────────────────────────────────────────

@app.get("/tasks/{task_id}")
def get_task_details(task_id: int, _key=Security(require_api_key)):
    """Get full task details including estimate, actual hours and progress."""
    try:
        return client.get_task_details(task_id=task_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{task_id}/hours/{user_id}")
def get_task_hours_by_user(task_id: int, user_id: int, _key=Security(require_api_key)):
    """Get hours a specific user logged on a specific task."""
    try:
        return client.get_task_hours_by_user(task_id=task_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
