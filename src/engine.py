"""Core Tableau REST API wrapper."""

import os
from typing import Any

import requests
from dotenv import load_dotenv

from . import session

load_dotenv()

API_VERSION = "3.22"


class TableauEngine:
    """Wrapper for Tableau REST API operations."""

    def __init__(self):
        self.server_url = os.getenv("TABLEAU_SERVER_URL", "").rstrip("/")
        self.site_content_url = os.getenv("TABLEAU_SITE_ID", "")
        self.pat_name = os.getenv("TABLEAU_PAT_NAME", "")
        self.pat_secret = os.getenv("TABLEAU_PAT_SECRET", "")
        self._token = None
        self._site_id = None
        self._user_id = None

    @property
    def base_url(self) -> str:
        return f"{self.server_url}/api/{API_VERSION}"

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        require_auth: bool = True
    ) -> requests.Response:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data
            require_auth: Whether to include auth header

        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if require_auth:
            if not self._token:
                self.ensure_authenticated()
            headers["X-Tableau-Auth"] = self._token

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )

        return response

    def _parse_response(self, response: requests.Response) -> dict[str, Any]:
        """Parse API response.

        Args:
            response: Response object

        Returns:
            Parsed response data

        Raises:
            Exception: If response indicates an error
        """
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("detail", response.text)
            except Exception:
                error_msg = response.text
            raise Exception(f"API Error ({response.status_code}): {error_msg}")

        if response.text:
            return response.json()
        return {}

    # Authentication methods

    def sign_in(self) -> dict[str, Any]:
        """Sign in using Personal Access Token.

        Returns:
            Authentication response data
        """
        payload = {
            "credentials": {
                "personalAccessTokenName": self.pat_name,
                "personalAccessTokenSecret": self.pat_secret,
                "site": {"contentUrl": self.site_content_url}
            }
        }

        response = self._request(
            "POST",
            "/auth/signin",
            data=payload,
            require_auth=False
        )

        data = self._parse_response(response)

        credentials = data.get("credentials", {})
        self._token = credentials.get("token")
        self._site_id = credentials.get("site", {}).get("id")
        self._user_id = credentials.get("user", {}).get("id")

        if self._token:
            session.save_session(self._token, self._site_id, self._user_id)

        return {
            "site_id": self._site_id,
            "user_id": self._user_id,
            "site_name": credentials.get("site", {}).get("name"),
            "user_name": credentials.get("user", {}).get("name")
        }

    def sign_out(self) -> dict[str, Any]:
        """Sign out and clear session.

        Returns:
            Sign out confirmation
        """
        try:
            if self._token:
                self._request("POST", "/auth/signout")
        except Exception:
            pass  # Ignore errors on signout

        self._token = None
        self._site_id = None
        self._user_id = None
        session.clear_session()

        return {"message": "Signed out successfully"}

    def ensure_authenticated(self) -> None:
        """Ensure we have a valid session, signing in if needed."""
        stored_session = session.load_session()
        if stored_session and session.is_session_valid(stored_session):
            self._token = stored_session["token"]
            self._site_id = stored_session["site_id"]
            self._user_id = stored_session["user_id"]
        else:
            self.sign_in()

    def get_auth_status(self) -> dict[str, Any]:
        """Get current authentication status.

        Returns:
            Session status information
        """
        session_info = session.get_session_info()
        if session_info:
            return {
                "authenticated": True,
                **session_info
            }
        return {"authenticated": False}

    # Discovery methods

    def list_sites(self) -> dict[str, Any]:
        """List all sites (Tableau Server only).

        Returns:
            List of sites
        """
        response = self._request("GET", "/sites")
        data = self._parse_response(response)

        sites = data.get("sites", {}).get("site", [])
        if isinstance(sites, dict):
            sites = [sites]

        return {
            "sites": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "contentUrl": s.get("contentUrl"),
                    "state": s.get("state")
                }
                for s in sites
            ]
        }

    def list_projects(self) -> dict[str, Any]:
        """List projects in current site.

        Returns:
            List of projects
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/projects")
        data = self._parse_response(response)

        projects = data.get("projects", {}).get("project", [])
        if isinstance(projects, dict):
            projects = [projects]

        return {
            "projects": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "parentProjectId": p.get("parentProjectId")
                }
                for p in projects
            ]
        }

    def list_workbooks(self) -> dict[str, Any]:
        """List workbooks in current site.

        Returns:
            List of workbooks
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/workbooks")
        data = self._parse_response(response)

        workbooks = data.get("workbooks", {}).get("workbook", [])
        if isinstance(workbooks, dict):
            workbooks = [workbooks]

        return {
            "workbooks": [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "projectId": w.get("project", {}).get("id"),
                    "projectName": w.get("project", {}).get("name"),
                    "owner": w.get("owner", {}).get("name"),
                    "createdAt": w.get("createdAt"),
                    "updatedAt": w.get("updatedAt")
                }
                for w in workbooks
            ]
        }

    def get_workbook(self, workbook_id: str) -> dict[str, Any]:
        """Get details for a specific workbook.

        Args:
            workbook_id: Workbook LUID

        Returns:
            Workbook details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/workbooks/{workbook_id}"
        )
        data = self._parse_response(response)

        workbook = data.get("workbook", {})
        return {
            "id": workbook.get("id"),
            "name": workbook.get("name"),
            "description": workbook.get("description"),
            "projectId": workbook.get("project", {}).get("id"),
            "projectName": workbook.get("project", {}).get("name"),
            "owner": workbook.get("owner", {}).get("name"),
            "ownerId": workbook.get("owner", {}).get("id"),
            "createdAt": workbook.get("createdAt"),
            "updatedAt": workbook.get("updatedAt"),
            "webpageUrl": workbook.get("webpageUrl"),
            "showTabs": workbook.get("showTabs"),
            "size": workbook.get("size")
        }

    # Operations methods

    def list_extract_tasks(self) -> dict[str, Any]:
        """List extract refresh tasks.

        Returns:
            List of extract refresh tasks
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/tasks/extractRefreshes"
        )
        data = self._parse_response(response)

        tasks = data.get("tasks", {}).get("task", [])
        if isinstance(tasks, dict):
            tasks = [tasks]

        return {
            "tasks": [
                {
                    "id": t.get("extractRefresh", {}).get("id"),
                    "priority": t.get("extractRefresh", {}).get("priority"),
                    "type": t.get("extractRefresh", {}).get("type"),
                    "workbook": t.get("extractRefresh", {}).get("workbook", {}).get("id"),
                    "datasource": t.get("extractRefresh", {}).get("datasource", {}).get("id"),
                    "schedule": t.get("schedule", {}).get("name")
                }
                for t in tasks
            ]
        }

    def run_extract_refresh(self, task_id: str) -> dict[str, Any]:
        """Trigger an extract refresh task to run now.

        Args:
            task_id: Extract refresh task ID

        Returns:
            Job information
        """
        self.ensure_authenticated()
        response = self._request(
            "POST",
            f"/sites/{self._site_id}/tasks/extractRefreshes/{task_id}/runNow"
        )
        data = self._parse_response(response)

        job = data.get("job", {})
        return {
            "jobId": job.get("id"),
            "mode": job.get("mode"),
            "type": job.get("type"),
            "createdAt": job.get("createdAt")
        }

    # Permissions methods

    def get_workbook_permissions(self, workbook_id: str) -> dict[str, Any]:
        """Get permissions for a workbook.

        Args:
            workbook_id: Workbook LUID

        Returns:
            Workbook permissions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/permissions"
        )
        data = self._parse_response(response)

        permissions = data.get("permissions", {})
        grant_capabilities = permissions.get("granteeCapabilities", [])
        if isinstance(grant_capabilities, dict):
            grant_capabilities = [grant_capabilities]

        result = []
        for gc in grant_capabilities:
            user = gc.get("user", {})
            group = gc.get("group", {})
            capabilities = gc.get("capabilities", {}).get("capability", [])
            if isinstance(capabilities, dict):
                capabilities = [capabilities]

            result.append({
                "user": {"id": user.get("id"), "name": user.get("name")} if user else None,
                "group": {"id": group.get("id"), "name": group.get("name")} if group else None,
                "capabilities": [
                    {"name": c.get("name"), "mode": c.get("mode")}
                    for c in capabilities
                ]
            })

        return {"permissions": result}

    def add_workbook_permission(
        self,
        workbook_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Add a permission to a workbook.

        Args:
            workbook_id: Workbook LUID
            user_id: User LUID
            capability_name: Capability name (e.g., Read, Write, etc.)
            capability_mode: Allow or Deny

        Returns:
            Updated permissions
        """
        self.ensure_authenticated()

        payload = {
            "permissions": {
                "granteeCapabilities": [
                    {
                        "user": {"id": user_id},
                        "capabilities": {
                            "capability": [
                                {"name": capability_name, "mode": capability_mode}
                            ]
                        }
                    }
                ]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/permissions",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Permission added successfully", "data": data}

    def delete_workbook_permission(
        self,
        workbook_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Delete a permission from a workbook.

        Args:
            workbook_id: Workbook LUID
            user_id: User LUID
            capability_name: Capability name
            capability_mode: Allow or Deny

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()

        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/permissions/users/{user_id}/{capability_name}/{capability_mode}"
        )

        if response.status_code == 204:
            return {"message": "Permission deleted successfully"}

        return self._parse_response(response)

    # Users methods

    def list_users(self) -> dict[str, Any]:
        """List all users in the current site.

        Returns:
            List of users
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/users")
        data = self._parse_response(response)

        users = data.get("users", {}).get("user", [])
        if isinstance(users, dict):
            users = [users]

        return {
            "users": [
                {
                    "id": u.get("id"),
                    "name": u.get("name"),
                    "fullName": u.get("fullName"),
                    "email": u.get("email"),
                    "siteRole": u.get("siteRole"),
                    "lastLogin": u.get("lastLogin")
                }
                for u in users
            ]
        }

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get details for a specific user.

        Args:
            user_id: User LUID

        Returns:
            User details
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/users/{user_id}")
        data = self._parse_response(response)

        user = data.get("user", {})
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "fullName": user.get("fullName"),
            "email": user.get("email"),
            "siteRole": user.get("siteRole"),
            "lastLogin": user.get("lastLogin"),
            "externalAuthUserId": user.get("externalAuthUserId")
        }

    def add_user(self, username: str, site_role: str = "Viewer") -> dict[str, Any]:
        """Add a user to the site.

        Args:
            username: Username for the new user
            site_role: Site role (Creator, Explorer, Viewer, etc.)

        Returns:
            Created user details
        """
        self.ensure_authenticated()
        payload = {
            "user": {
                "name": username,
                "siteRole": site_role
            }
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/users",
            data=payload
        )
        data = self._parse_response(response)

        user = data.get("user", {})
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "siteRole": user.get("siteRole")
        }

    def remove_user(self, user_id: str) -> dict[str, Any]:
        """Remove a user from the site.

        Args:
            user_id: User LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/users/{user_id}"
        )

        if response.status_code == 204:
            return {"message": "User removed successfully"}

        return self._parse_response(response)

    # Groups methods

    def list_groups(self) -> dict[str, Any]:
        """List all groups in the current site.

        Returns:
            List of groups
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/groups")
        data = self._parse_response(response)

        groups = data.get("groups", {}).get("group", [])
        if isinstance(groups, dict):
            groups = [groups]

        return {
            "groups": [
                {
                    "id": g.get("id"),
                    "name": g.get("name"),
                    "domainName": g.get("domain", {}).get("name"),
                    "minimumSiteRole": g.get("minimumSiteRole")
                }
                for g in groups
            ]
        }

    def get_group_users(self, group_id: str) -> dict[str, Any]:
        """Get users in a group.

        Args:
            group_id: Group LUID

        Returns:
            List of users in the group
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/groups/{group_id}/users"
        )
        data = self._parse_response(response)

        users = data.get("users", {}).get("user", [])
        if isinstance(users, dict):
            users = [users]

        return {
            "users": [
                {
                    "id": u.get("id"),
                    "name": u.get("name"),
                    "siteRole": u.get("siteRole")
                }
                for u in users
            ]
        }

    def add_user_to_group(self, group_id: str, user_id: str) -> dict[str, Any]:
        """Add a user to a group.

        Args:
            group_id: Group LUID
            user_id: User LUID

        Returns:
            Confirmation
        """
        self.ensure_authenticated()
        payload = {
            "user": {"id": user_id}
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/groups/{group_id}/users",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "User added to group successfully", "user": data.get("user", {})}

    def remove_user_from_group(self, group_id: str, user_id: str) -> dict[str, Any]:
        """Remove a user from a group.

        Args:
            group_id: Group LUID
            user_id: User LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/groups/{group_id}/users/{user_id}"
        )

        if response.status_code == 204:
            return {"message": "User removed from group successfully"}

        return self._parse_response(response)

    # Data Sources methods

    def list_datasources(self) -> dict[str, Any]:
        """List all data sources in the current site.

        Returns:
            List of data sources
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/datasources")
        data = self._parse_response(response)

        datasources = data.get("datasources", {}).get("datasource", [])
        if isinstance(datasources, dict):
            datasources = [datasources]

        return {
            "datasources": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "type": d.get("type"),
                    "projectId": d.get("project", {}).get("id"),
                    "projectName": d.get("project", {}).get("name"),
                    "owner": d.get("owner", {}).get("name"),
                    "createdAt": d.get("createdAt"),
                    "updatedAt": d.get("updatedAt"),
                    "isCertified": d.get("isCertified")
                }
                for d in datasources
            ]
        }

    def get_datasource(self, datasource_id: str) -> dict[str, Any]:
        """Get details for a specific data source.

        Args:
            datasource_id: Data source LUID

        Returns:
            Data source details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/datasources/{datasource_id}"
        )
        data = self._parse_response(response)

        ds = data.get("datasource", {})
        return {
            "id": ds.get("id"),
            "name": ds.get("name"),
            "type": ds.get("type"),
            "description": ds.get("description"),
            "projectId": ds.get("project", {}).get("id"),
            "projectName": ds.get("project", {}).get("name"),
            "owner": ds.get("owner", {}).get("name"),
            "ownerId": ds.get("owner", {}).get("id"),
            "createdAt": ds.get("createdAt"),
            "updatedAt": ds.get("updatedAt"),
            "isCertified": ds.get("isCertified"),
            "webpageUrl": ds.get("webpageUrl")
        }

    def delete_datasource(self, datasource_id: str) -> dict[str, Any]:
        """Delete a data source.

        Args:
            datasource_id: Data source LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/datasources/{datasource_id}"
        )

        if response.status_code == 204:
            return {"message": "Data source deleted successfully"}

        return self._parse_response(response)

    def get_datasource_permissions(self, datasource_id: str) -> dict[str, Any]:
        """Get permissions for a data source.

        Args:
            datasource_id: Data source LUID

        Returns:
            Data source permissions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/datasources/{datasource_id}/permissions"
        )
        data = self._parse_response(response)

        permissions = data.get("permissions", {})
        grant_capabilities = permissions.get("granteeCapabilities", [])
        if isinstance(grant_capabilities, dict):
            grant_capabilities = [grant_capabilities]

        result = []
        for gc in grant_capabilities:
            user = gc.get("user", {})
            group = gc.get("group", {})
            capabilities = gc.get("capabilities", {}).get("capability", [])
            if isinstance(capabilities, dict):
                capabilities = [capabilities]

            result.append({
                "user": {"id": user.get("id"), "name": user.get("name")} if user else None,
                "group": {"id": group.get("id"), "name": group.get("name")} if group else None,
                "capabilities": [
                    {"name": c.get("name"), "mode": c.get("mode")}
                    for c in capabilities
                ]
            })

        return {"permissions": result}

    def add_datasource_permission(
        self,
        datasource_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Add a permission to a data source.

        Args:
            datasource_id: Data source LUID
            user_id: User LUID
            capability_name: Capability name
            capability_mode: Allow or Deny

        Returns:
            Updated permissions
        """
        self.ensure_authenticated()

        payload = {
            "permissions": {
                "granteeCapabilities": [
                    {
                        "user": {"id": user_id},
                        "capabilities": {
                            "capability": [
                                {"name": capability_name, "mode": capability_mode}
                            ]
                        }
                    }
                ]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/datasources/{datasource_id}/permissions",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Permission added successfully", "data": data}

    def delete_datasource_permission(
        self,
        datasource_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Delete a permission from a data source.

        Args:
            datasource_id: Data source LUID
            user_id: User LUID
            capability_name: Capability name
            capability_mode: Allow or Deny

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()

        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/datasources/{datasource_id}/permissions/users/{user_id}/{capability_name}/{capability_mode}"
        )

        if response.status_code == 204:
            return {"message": "Permission deleted successfully"}

        return self._parse_response(response)

    # Extended Workbook methods

    def delete_workbook(self, workbook_id: str) -> dict[str, Any]:
        """Delete a workbook.

        Args:
            workbook_id: Workbook LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/workbooks/{workbook_id}"
        )

        if response.status_code == 204:
            return {"message": "Workbook deleted successfully"}

        return self._parse_response(response)

    def list_workbook_views(self, workbook_id: str) -> dict[str, Any]:
        """List views in a workbook.

        Args:
            workbook_id: Workbook LUID

        Returns:
            List of views
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/views"
        )
        data = self._parse_response(response)

        views = data.get("views", {}).get("view", [])
        if isinstance(views, dict):
            views = [views]

        return {
            "views": [
                {
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "contentUrl": v.get("contentUrl"),
                    "viewUrlName": v.get("viewUrlName")
                }
                for v in views
            ]
        }

    def get_view(self, view_id: str) -> dict[str, Any]:
        """Get details for a specific view.

        Args:
            view_id: View LUID

        Returns:
            View details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/views/{view_id}"
        )
        data = self._parse_response(response)

        view = data.get("view", {})
        return {
            "id": view.get("id"),
            "name": view.get("name"),
            "contentUrl": view.get("contentUrl"),
            "workbookId": view.get("workbook", {}).get("id"),
            "ownerId": view.get("owner", {}).get("id"),
            "totalViewCount": view.get("usage", {}).get("totalViewCount")
        }

    # Jobs methods

    def list_jobs(self) -> dict[str, Any]:
        """List all jobs in the current site.

        Returns:
            List of jobs
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/jobs")
        data = self._parse_response(response)

        jobs = data.get("backgroundJobs", {}).get("backgroundJob", [])
        if isinstance(jobs, dict):
            jobs = [jobs]

        return {
            "jobs": [
                {
                    "id": j.get("id"),
                    "status": j.get("status"),
                    "jobType": j.get("jobType"),
                    "createdAt": j.get("createdAt"),
                    "startedAt": j.get("startedAt"),
                    "endedAt": j.get("endedAt"),
                    "progress": j.get("progress")
                }
                for j in jobs
            ]
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Get details for a specific job.

        Args:
            job_id: Job LUID

        Returns:
            Job details
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/jobs/{job_id}")
        data = self._parse_response(response)

        job = data.get("job", {})
        return {
            "id": job.get("id"),
            "status": job.get("status"),
            "jobType": job.get("type"),
            "createdAt": job.get("createdAt"),
            "startedAt": job.get("startedAt"),
            "completedAt": job.get("completedAt"),
            "progress": job.get("progress"),
            "finishCode": job.get("finishCode")
        }

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel a running job.

        Args:
            job_id: Job LUID

        Returns:
            Cancellation confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/jobs/{job_id}"
        )

        if response.status_code == 204:
            return {"message": "Job cancelled successfully"}

        return self._parse_response(response)

    # Schedules methods

    def list_schedules(self) -> dict[str, Any]:
        """List all schedules (Server only).

        Returns:
            List of schedules
        """
        self.ensure_authenticated()
        response = self._request("GET", "/schedules")
        data = self._parse_response(response)

        schedules = data.get("schedules", {}).get("schedule", [])
        if isinstance(schedules, dict):
            schedules = [schedules]

        return {
            "schedules": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "type": s.get("type"),
                    "state": s.get("state"),
                    "priority": s.get("priority"),
                    "frequency": s.get("frequency"),
                    "nextRunAt": s.get("nextRunAt")
                }
                for s in schedules
            ]
        }

    def add_workbook_to_schedule(
        self,
        schedule_id: str,
        workbook_id: str
    ) -> dict[str, Any]:
        """Add a workbook to a refresh schedule.

        Args:
            schedule_id: Schedule LUID
            workbook_id: Workbook LUID

        Returns:
            Task information
        """
        self.ensure_authenticated()
        payload = {
            "task": {
                "extractRefresh": {
                    "workbook": {"id": workbook_id}
                }
            }
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/schedules/{schedule_id}/workbooks",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Workbook added to schedule", "task": data.get("task", {})}

    def add_datasource_to_schedule(
        self,
        schedule_id: str,
        datasource_id: str
    ) -> dict[str, Any]:
        """Add a data source to a refresh schedule.

        Args:
            schedule_id: Schedule LUID
            datasource_id: Data source LUID

        Returns:
            Task information
        """
        self.ensure_authenticated()
        payload = {
            "task": {
                "extractRefresh": {
                    "datasource": {"id": datasource_id}
                }
            }
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/schedules/{schedule_id}/datasources",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Data source added to schedule", "task": data.get("task", {})}

    # Subscriptions methods

    def list_subscriptions(self) -> dict[str, Any]:
        """List all subscriptions in the current site.

        Returns:
            List of subscriptions
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/subscriptions")
        data = self._parse_response(response)

        subscriptions = data.get("subscriptions", {}).get("subscription", [])
        if isinstance(subscriptions, dict):
            subscriptions = [subscriptions]

        return {
            "subscriptions": [
                {
                    "id": s.get("id"),
                    "subject": s.get("subject"),
                    "userId": s.get("user", {}).get("id"),
                    "userName": s.get("user", {}).get("name"),
                    "viewId": s.get("content", {}).get("id") if s.get("content", {}).get("type") == "View" else None,
                    "workbookId": s.get("content", {}).get("id") if s.get("content", {}).get("type") == "Workbook" else None,
                    "scheduleId": s.get("schedule", {}).get("id"),
                    "scheduleName": s.get("schedule", {}).get("name")
                }
                for s in subscriptions
            ]
        }

    def create_subscription(
        self,
        subject: str,
        user_id: str,
        schedule_id: str,
        content_type: str,
        content_id: str
    ) -> dict[str, Any]:
        """Create a new subscription.

        Args:
            subject: Email subject line
            user_id: User LUID to receive subscription
            schedule_id: Schedule LUID
            content_type: "View" or "Workbook"
            content_id: View or Workbook LUID

        Returns:
            Created subscription
        """
        self.ensure_authenticated()
        payload = {
            "subscription": {
                "subject": subject,
                "content": {
                    "type": content_type,
                    "id": content_id
                },
                "schedule": {"id": schedule_id},
                "user": {"id": user_id}
            }
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/subscriptions",
            data=payload
        )
        data = self._parse_response(response)

        sub = data.get("subscription", {})
        return {
            "id": sub.get("id"),
            "subject": sub.get("subject"),
            "message": "Subscription created successfully"
        }

    def delete_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Delete a subscription.

        Args:
            subscription_id: Subscription LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/subscriptions/{subscription_id}"
        )

        if response.status_code == 204:
            return {"message": "Subscription deleted successfully"}

        return self._parse_response(response)

    # Favorites methods

    def list_favorites(self, user_id: str | None = None) -> dict[str, Any]:
        """List favorites for a user.

        Args:
            user_id: User LUID (defaults to current user)

        Returns:
            List of favorites
        """
        self.ensure_authenticated()
        if user_id is None:
            user_id = self._user_id

        response = self._request(
            "GET",
            f"/sites/{self._site_id}/favorites/{user_id}"
        )
        data = self._parse_response(response)

        favorites = data.get("favorites", {}).get("favorite", [])
        if isinstance(favorites, dict):
            favorites = [favorites]

        result = []
        for f in favorites:
            item = {
                "label": f.get("label")
            }
            if f.get("workbook"):
                item["type"] = "workbook"
                item["id"] = f.get("workbook", {}).get("id")
                item["name"] = f.get("workbook", {}).get("name")
            elif f.get("view"):
                item["type"] = "view"
                item["id"] = f.get("view", {}).get("id")
                item["name"] = f.get("view", {}).get("name")
            elif f.get("datasource"):
                item["type"] = "datasource"
                item["id"] = f.get("datasource", {}).get("id")
                item["name"] = f.get("datasource", {}).get("name")
            elif f.get("project"):
                item["type"] = "project"
                item["id"] = f.get("project", {}).get("id")
                item["name"] = f.get("project", {}).get("name")
            result.append(item)

        return {"favorites": result}

    def add_favorite(
        self,
        content_type: str,
        content_id: str,
        label: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Add an item to favorites.

        Args:
            content_type: Type of content (workbook, view, datasource, project)
            content_id: Content LUID
            label: Label for the favorite
            user_id: User LUID (defaults to current user)

        Returns:
            Confirmation
        """
        self.ensure_authenticated()
        if user_id is None:
            user_id = self._user_id

        payload = {
            "favorite": {
                "label": label,
                content_type: {"id": content_id}
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/favorites/{user_id}",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Added to favorites", "favorite": data.get("favorites", {})}

    def delete_favorite(
        self,
        content_type: str,
        content_id: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Remove an item from favorites.

        Args:
            content_type: Type of content (workbook, view, datasource, project)
            content_id: Content LUID
            user_id: User LUID (defaults to current user)

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        if user_id is None:
            user_id = self._user_id

        # Map content type to URL path
        type_map = {
            "workbook": "workbooks",
            "view": "views",
            "datasource": "datasources",
            "project": "projects"
        }
        url_type = type_map.get(content_type, content_type + "s")

        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/favorites/{user_id}/{url_type}/{content_id}"
        )

        if response.status_code == 204:
            return {"message": "Removed from favorites"}

        return self._parse_response(response)
