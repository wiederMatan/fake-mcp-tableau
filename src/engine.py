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
