import xmlrpc.client


class OdooClient:
    def __init__(self, base_url: str, db: str, email: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.db = db
        self.email = email
        self.api_key = api_key
        self.uid: int | None = None

        self._common = None
        self._models = None

    def _get_common(self):
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(f"{self.base_url}/xmlrpc/2/common")
        return self._common

    def _get_models(self):
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(f"{self.base_url}/xmlrpc/2/object")
        return self._models

    def authenticate(self) -> dict:
        uid = self._get_common().authenticate(self.db, self.email, self.api_key, {})
        if not uid:
            raise ValueError("Authentication failed — check your email and API key.")
        self.uid = uid
        return {"uid": self.uid, "authenticated": True}

    def _ensure_auth(self):
        if not self.uid:
            self.authenticate()

    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None) -> any:
        self._ensure_auth()
        return self._get_models().execute_kw(
            self.db, self.uid, self.api_key,
            model, method, args, kwargs or {}
        )

    # ── Timesheet helpers ──────────────────────────────────────────────────

    TIMESHEET_FIELDS = ["id", "name", "date", "unit_amount", "project_id", "task_id", "employee_id"]

    def list_my_timesheets(self, limit: int = 20, offset: int = 0,
                           date_from: str | None = None, date_to: str | None = None) -> dict:
        self._ensure_auth()
        domain = [["user_id", "=", self.uid]]
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        records = self._execute(
            model="account.analytic.line",
            method="search_read",
            args=[domain],
            kwargs={"fields": self.TIMESHEET_FIELDS, "limit": limit, "offset": offset},
        )
        total = self._execute("account.analytic.line", "search_count", [domain])
        return {"total": total, "offset": offset, "limit": limit, "records": records}

    def list_timesheets_by_date(self, date_from: str, date_to: str,
                                limit: int = 100, offset: int = 0) -> dict:
        self._ensure_auth()
        domain = [
            ["user_id", "=", self.uid],
            ["date", ">=", date_from],
            ["date", "<=", date_to],
        ]
        records = self._execute(
            model="account.analytic.line",
            method="search_read",
            args=[domain],
            kwargs={"fields": self.TIMESHEET_FIELDS, "limit": limit, "offset": offset},
        )
        total = self._execute("account.analytic.line", "search_count", [domain])
        return {"total": total, "offset": offset, "limit": limit, "records": records}

    def list_timesheets_by_project(self, project_id: int, limit: int = 50, offset: int = 0,
                                   date_from: str | None = None, date_to: str | None = None) -> dict:
        self._ensure_auth()
        domain = [
            ["user_id", "=", self.uid],
            ["project_id", "=", project_id],
        ]
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        records = self._execute(
            model="account.analytic.line",
            method="search_read",
            args=[domain],
            kwargs={"fields": self.TIMESHEET_FIELDS, "limit": limit, "offset": offset},
        )
        total = self._execute("account.analytic.line", "search_count", [domain])
        return {"total": total, "offset": offset, "limit": limit, "records": records}

    def create_timesheet(self, name: str, date: str, unit_amount: float, project_id: int, task_id: int) -> int:
        return self._execute(
            model="account.analytic.line",
            method="create",
            args=[{
                "name": name,
                "date": date,
                "unit_amount": unit_amount,
                "project_id": project_id,
                "task_id": task_id,
            }],
        )

    def update_timesheet(self, record_id: int, values: dict) -> bool:
        return self._execute(
            model="account.analytic.line",
            method="write",
            args=[[record_id], values],
        )

    def delete_timesheet(self, record_id: int) -> bool:
        return self._execute(
            model="account.analytic.line",
            method="unlink",
            args=[[record_id]],
        )

    # ── Project helpers ────────────────────────────────────────────────────

    def get_project(self, project_id: int) -> dict:
        results = self._execute(
            model="project.project",
            method="search_read",
            args=[[["id", "=", project_id]]],
            kwargs={
                "fields": ["id", "name", "description", "user_id", "partner_id",
                           "date_start", "date", "task_count"],
                "limit": 1,
            },
        )
        if not results:
            raise ValueError(f"Project {project_id} not found.")
        return results[0]

    def get_project_progress(self, project_id: int) -> list:
        """Return total hours logged per developer on a project."""
        rows = self._execute(
            model="account.analytic.line",
            method="read_group",
            args=[[["project_id", "=", project_id]]],
            kwargs={
                "fields": ["user_id", "unit_amount"],
                "groupby": ["user_id"],
            },
        )
        result = []
        for row in rows:
            user = row.get("user_id")
            result.append({
                "user_id": user[0] if user else None,
                "user_name": user[1] if user else "Unknown",
                "hours_logged": round(row.get("unit_amount", 0), 2),
                "entry_count": row.get("user_id_count", 0),
            })
        return result

    def list_phases(self, project_id: int) -> list:
        """Return all phases for a specific project."""
        return self._execute(
            model="project.phase",
            method="search_read",
            args=[[["project_id", "=", project_id]]],
            kwargs={"fields": ["id", "name"], "order": "id asc"},
        )

    def list_departments(self) -> list:
        """Return all departments."""
        return self._execute(
            model="hr.department",
            method="search_read",
            args=[[]],
            kwargs={"fields": ["id", "name"], "order": "name asc"},
        )

    def get_users_by_department(self, department_id: int) -> list:
        """Return all Odoo user IDs belonging to a department (by ID)."""
        employees = self._execute(
            model="hr.employee",
            method="search_read",
            args=[[["department_id", "=", department_id]]],
            kwargs={"fields": ["id", "name", "user_id", "department_id"]},
        )
        result = []
        for emp in employees:
            if emp.get("user_id"):
                result.append({
                    "user_id": emp["user_id"][0],
                    "user_name": emp["user_id"][1],
                    "employee_name": emp["name"],
                    "department": emp["department_id"][1] if emp.get("department_id") else None,
                })
        return result

    def get_project_tasks(self, project_id: int, limit: int = 20, offset: int = 0,
                          stage_id: int | None = None,
                          phase_id: int | None = None,
                          deadline_from: str | None = None,
                          deadline_to: str | None = None,
                          keyword: str | None = None,
                          user_ids: list[int] | None = None) -> dict:
        """Return tasks in a project with optional filters and pagination."""
        domain = [["project_id", "=", project_id]]
        if stage_id:
            domain.append(["stage_id", "=", stage_id])
        if phase_id:
            domain.append(["phase_id", "=", phase_id])
        if keyword:
            domain += ["|", ["name", "ilike", keyword], ["description", "ilike", keyword]]
        if user_ids:
            domain += ["|", ["user_id", "in", user_ids], ["project_user_ids", "in", user_ids]]
        if deadline_from:
            domain.append(["date_deadline", ">=", deadline_from])
        if deadline_to:
            domain.append(["date_deadline", "<=", deadline_to])
        tasks = self._execute(
            model="project.task",
            method="search_read",
            args=[domain],
            kwargs={
                "fields": ["id", "name", "description", "user_id", "project_user_ids",
                           "stage_id", "phase_id", "priority",
                           "planned_hours", "effective_hours", "remaining_hours", "date_deadline"],
                "limit": limit,
                "offset": offset,
            },
        )
        total = self._execute("project.task", "search_count", [domain])

        # Collect all unique user IDs to fetch emails in one query
        user_id_set = set()
        for task in tasks:
            if task.get("user_id"):
                user_id_set.add(task["user_id"][0])
            for uid in (task.get("project_user_ids") or []):
                user_id_set.add(uid)

        user_email_map = {}
        if user_id_set:
            users = self._execute(
                model="res.users",
                method="search_read",
                args=[[["id", "in", list(user_id_set)]]],
                kwargs={"fields": ["id", "name", "login"]},
            )
            user_email_map = {u["id"]: {"name": u["name"], "email": u["login"]} for u in users}

        # Fetch timesheet hours per user per task in one batch query
        task_ids = [t["id"] for t in tasks]
        timesheets = self._execute(
            model="account.analytic.line",
            method="search_read",
            args=[[["task_id", "in", task_ids]]],
            kwargs={"fields": ["task_id", "user_id", "unit_amount"]},
        )
        # Build map: task_id -> { user_id -> hours }
        task_hours_map: dict[int, dict[int, float]] = {}
        ts_user_ids = set()
        for ts in timesheets:
            if not ts.get("task_id") or not ts.get("user_id"):
                continue
            tid = ts["task_id"][0]
            uid = ts["user_id"][0]
            ts_user_ids.add(uid)
            task_hours_map.setdefault(tid, {})
            task_hours_map[tid][uid] = task_hours_map[tid].get(uid, 0) + ts["unit_amount"]

        # Fetch emails for any timesheet users not already in user_email_map
        missing_ids = ts_user_ids - set(user_email_map.keys())
        if missing_ids:
            extra_users = self._execute(
                model="res.users",
                method="search_read",
                args=[[["id", "in", list(missing_ids)]]],
                kwargs={"fields": ["id", "name", "login"]},
            )
            for u in extra_users:
                user_email_map[u["id"]] = {"name": u["name"], "email": u["login"]}

        result = []
        for task in tasks:
            planned = task.get("planned_hours") or 0
            actual = task.get("effective_hours") or 0

            # Primary assignee
            assignee = None
            if task.get("user_id"):
                uid = task["user_id"][0]
                assignee = {
                    "user_id": uid,
                    "name": user_email_map.get(uid, {}).get("name", task["user_id"][1]),
                    "email": user_email_map.get(uid, {}).get("email"),
                }

            # All assignees (multi-assign)
            all_assignees = []
            for uid in (task.get("project_user_ids") or []):
                all_assignees.append({
                    "user_id": uid,
                    "name": user_email_map.get(uid, {}).get("name"),
                    "email": user_email_map.get(uid, {}).get("email"),
                })

            # Hours breakdown per developer from timesheets
            hours_by_developer = []
            for uid, hours in sorted(
                task_hours_map.get(task["id"], {}).items(),
                key=lambda x: x[1], reverse=True
            ):
                hours_by_developer.append({
                    "user_id": uid,
                    "name": user_email_map.get(uid, {}).get("name"),
                    "email": user_email_map.get(uid, {}).get("email"),
                    "hours_logged": round(hours, 2),
                })

            result.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "priority": "high" if task.get("priority") == "1" else "normal",
                "assignee": assignee,
                "all_assignees": all_assignees,
                "stage": task["stage_id"][1] if task.get("stage_id") else "Unknown",
                "phase": task["phase_id"][1] if task.get("phase_id") else None,
                "deadline": task.get("date_deadline"),
                "estimated_hours": round(planned, 2),
                "actual_hours": round(actual, 2),
                "remaining_hours": round(task.get("remaining_hours") or (planned - actual), 2),
                "progress_pct": round((actual / planned * 100), 1) if planned > 0 else None,
                "hours_by_developer": hours_by_developer,
            })
        return {"total": total, "offset": offset, "limit": limit, "records": result}

    def get_task_details(self, task_id: int) -> dict:
        """Return full details of a task including estimate and actual hours."""
        results = self._execute(
            model="project.task",
            method="search_read",
            args=[[["id", "=", task_id]]],
            kwargs={
                "fields": ["id", "name", "description", "user_id", "project_id",
                           "stage_id", "planned_hours", "effective_hours",
                           "remaining_hours", "date_deadline", "priority"],
                "limit": 1,
            },
        )
        if not results:
            raise ValueError(f"Task {task_id} not found.")
        task = results[0]
        planned = task.get("planned_hours") or 0
        actual = task.get("effective_hours") or 0
        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "project": task["project_id"][1] if task.get("project_id") else None,
            "assignee": task["user_id"][1] if task.get("user_id") else "Unassigned",
            "stage": task["stage_id"][1] if task.get("stage_id") else "Unknown",
            "priority": "High" if task.get("priority") == "1" else "Normal",
            "deadline": task.get("date_deadline"),
            "estimated_hours": round(planned, 2),
            "actual_hours": round(actual, 2),
            "remaining_hours": round(task.get("remaining_hours") or (planned - actual), 2),
            "progress_pct": round((actual / planned * 100), 1) if planned > 0 else None,
        }

    def get_task_progress(self, task_id: int) -> dict:
        """Return planned hours, total spent, and hours breakdown per developer for a task."""
        task = self.get_task_details(task_id)
        rows = self._execute(
            model="account.analytic.line",
            method="read_group",
            args=[[["task_id", "=", task_id]]],
            kwargs={
                "fields": ["user_id", "unit_amount"],
                "groupby": ["user_id"],
            },
        )
        breakdown = []
        for row in rows:
            user = row.get("user_id")
            breakdown.append({
                "user_id": user[0] if user else None,
                "user_name": user[1] if user else "Unknown",
                "hours_logged": round(row.get("unit_amount", 0), 2),
            })
        return {
            "task_id": task_id,
            "task_name": task["task_name"],
            "stage": task["stage"],
            "estimated_hours": task["estimated_hours"],
            "actual_hours": task["actual_hours"],
            "remaining_hours": task["remaining_hours"],
            "progress_pct": task["progress_pct"],
            "developers": breakdown,
        }

    def get_task_hours_by_user(self, task_id: int, user_id: int) -> dict:
        """Return total hours a specific user logged on a specific task."""
        entries = self._execute(
            model="account.analytic.line",
            method="search_read",
            args=[[["task_id", "=", task_id], ["user_id", "=", user_id]]],
            kwargs={
                "fields": ["id", "name", "date", "unit_amount"],
                "limit": 500,
            },
        )
        total = sum(e.get("unit_amount", 0) for e in entries)
        return {
            "task_id": task_id,
            "user_id": user_id,
            "total_hours": round(total, 2),
            "entry_count": len(entries),
            "entries": entries,
        }

    # ── Stage helpers ──────────────────────────────────────────────────────

    def list_stages(self, project_id: int | None = None) -> list:
        """Return all task stages, optionally filtered to a specific project."""
        domain = []
        if project_id:
            domain.append(["project_ids", "in", [project_id]])
        return self._execute(
            model="project.task.type",
            method="search_read",
            args=[domain],
            kwargs={
                "fields": ["id", "name", "sequence"],
                "order": "sequence asc",
            },
        )

    def get_tasks_by_stage(self, stage_id: int, project_id: int | None = None,
                           limit: int = 20, offset: int = 0,
                           deadline_from: str | None = None,
                           deadline_to: str | None = None) -> dict:
        """Return tasks in a specific stage, with optional project and deadline filters."""
        domain = [["stage_id", "=", stage_id]]
        if project_id:
            domain.append(["project_id", "=", project_id])
        if deadline_from:
            domain.append(["date_deadline", ">=", deadline_from])
        if deadline_to:
            domain.append(["date_deadline", "<=", deadline_to])
        tasks = self._execute(
            model="project.task",
            method="search_read",
            args=[domain],
            kwargs={
                "fields": ["id", "name", "user_id", "project_id", "stage_id",
                           "planned_hours", "effective_hours", "remaining_hours", "date_deadline"],
                "order": "project_id asc",
                "limit": limit,
                "offset": offset,
            },
        )
        total = self._execute("project.task", "search_count", [domain])
        result = []
        for task in tasks:
            planned = task.get("planned_hours") or 0
            actual = task.get("effective_hours") or 0
            result.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "assignee": task["user_id"][1] if task.get("user_id") else "Unassigned",
                "project": task["project_id"][1] if task.get("project_id") else "No Project",
                "project_id": task["project_id"][0] if task.get("project_id") else None,
                "stage": task["stage_id"][1] if task.get("stage_id") else "Unknown",
                "deadline": task.get("date_deadline"),
                "estimated_hours": round(planned, 2),
                "actual_hours": round(actual, 2),
                "remaining_hours": round(task.get("remaining_hours") or (planned - actual), 2),
                "progress_pct": round((actual / planned * 100), 1) if planned > 0 else None,
            })
        return {"total": total, "offset": offset, "limit": limit, "records": result}

    def get_tasks_by_phase_number(self, project_id: int, phase_number: int,
                                  limit: int = 20, offset: int = 0,
                                  deadline_from: str | None = None,
                                  deadline_to: str | None = None) -> dict:
        """Return tasks in the Nth stage of a project (1 = first stage, 2 = second, etc.)."""
        stages = self.list_stages(project_id=project_id)
        if not stages:
            raise ValueError(f"No stages found for project {project_id}.")
        if phase_number < 1 or phase_number > len(stages):
            raise ValueError(f"Phase number {phase_number} is out of range — project has {len(stages)} stages.")
        stage = stages[phase_number - 1]
        result = self.get_tasks_by_stage(
            stage_id=stage["id"],
            project_id=project_id,
            limit=limit,
            offset=offset,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
        )
        result["phase_number"] = phase_number
        result["phase_name"] = stage["name"]
        return result

    # ── User helpers ───────────────────────────────────────────────────────

    def list_projects(self) -> list:
        """Return all active projects with their IDs and names."""
        return self._execute(
            model="project.project",
            method="search_read",
            args=[[["active", "=", True]]],
            kwargs={
                "fields": ["id", "name", "user_id", "task_count"],
                "order": "name asc",
                "limit": 200,
            },
        )

    def get_user_tasks(self, user_id: int, limit: int = 20, offset: int = 0,
                       project_id: int | None = None, stage_id: int | None = None,
                       deadline_from: str | None = None, deadline_to: str | None = None) -> dict:
        """Return tasks assigned to a user with optional filters and pagination."""
        domain = ["|", ["user_id", "=", user_id], ["project_user_ids", "=", user_id]]
        if project_id:
            domain = [["project_id", "=", project_id]] + domain
        if stage_id:
            domain.append(["stage_id", "=", stage_id])
        if deadline_from:
            domain.append(["date_deadline", ">=", deadline_from])
        if deadline_to:
            domain.append(["date_deadline", "<=", deadline_to])
        tasks = self._execute(
            model="project.task",
            method="search_read",
            args=[domain],
            kwargs={
                "fields": ["id", "name", "project_id", "stage_id", "planned_hours",
                           "effective_hours", "remaining_hours", "date_deadline"],
                "order": "project_id asc",
                "limit": limit,
                "offset": offset,
            },
        )
        total = self._execute("project.task", "search_count", [domain])
        result = []
        for task in tasks:
            planned = task.get("planned_hours") or 0
            actual = task.get("effective_hours") or 0
            result.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "project": task["project_id"][1] if task.get("project_id") else "No Project",
                "project_id": task["project_id"][0] if task.get("project_id") else None,
                "stage": task["stage_id"][1] if task.get("stage_id") else "Unknown",
                "deadline": task.get("date_deadline"),
                "estimated_hours": round(planned, 2),
                "actual_hours": round(actual, 2),
                "remaining_hours": round(task.get("remaining_hours") or (planned - actual), 2),
                "progress_pct": round((actual / planned * 100), 1) if planned > 0 else None,
            })
        return {"total": total, "offset": offset, "limit": limit, "records": result}

    def get_user_projects(self, user_id: int) -> list:
        """Return all projects a user has logged time on."""
        rows = self._execute(
            model="account.analytic.line",
            method="read_group",
            args=[[["user_id", "=", user_id], ["project_id", "!=", False]]],
            kwargs={
                "fields": ["project_id", "unit_amount"],
                "groupby": ["project_id"],
            },
        )
        result = []
        for row in rows:
            project = row.get("project_id")
            result.append({
                "project_id": project[0] if project else None,
                "project_name": project[1] if project else "Unknown",
                "total_hours_logged": round(row.get("unit_amount", 0), 2),
            })
        return result

    def get_user_department(self, user_id: int) -> dict:
        """Return the department of a user via hr.employee."""
        results = self._execute(
            model="hr.employee",
            method="search_read",
            args=[[["user_id", "=", user_id]]],
            kwargs={
                "fields": ["id", "name", "department_id", "job_title"],
                "limit": 1,
            },
        )
        if not results:
            raise ValueError(f"No employee record found for user_id: {user_id}")
        emp = results[0]
        return {
            "user_id": user_id,
            "employee_name": emp["name"],
            "department_id": emp["department_id"][0] if emp.get("department_id") else None,
            "department": emp["department_id"][1] if emp.get("department_id") else None,
            "job_title": emp.get("job_title"),
        }

    def get_user_by_email(self, email: str) -> dict:
        """Resolve an email address to an Odoo user ID and name."""
        results = self._execute(
            model="res.users",
            method="search_read",
            args=[[["login", "=", email]]],
            kwargs={
                "fields": ["id", "name", "login", "email"],
                "limit": 1,
            },
        )
        if not results:
            raise ValueError(f"No user found with email: {email}")
        user = results[0]
        return {
            "user_id": user["id"],
            "name": user["name"],
            "email": user.get("email") or user["login"],
        }
