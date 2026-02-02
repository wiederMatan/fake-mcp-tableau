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

    def update_workbook(
        self,
        workbook_id: str,
        name: str | None = None,
        project_id: str | None = None,
        owner_id: str | None = None,
        show_tabs: bool | None = None
    ) -> dict[str, Any]:
        """Update a workbook.

        Args:
            workbook_id: Workbook LUID
            name: New name for the workbook
            project_id: New project ID
            owner_id: New owner user ID
            show_tabs: Whether to show tabs

        Returns:
            Updated workbook details
        """
        self.ensure_authenticated()

        workbook_data: dict[str, Any] = {}
        if name is not None:
            workbook_data["name"] = name
        if project_id is not None:
            workbook_data["project"] = {"id": project_id}
        if owner_id is not None:
            workbook_data["owner"] = {"id": owner_id}
        if show_tabs is not None:
            workbook_data["showTabs"] = show_tabs

        payload = {"workbook": workbook_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/workbooks/{workbook_id}",
            data=payload
        )
        data = self._parse_response(response)

        workbook = data.get("workbook", {})
        return {
            "id": workbook.get("id"),
            "name": workbook.get("name"),
            "projectId": workbook.get("project", {}).get("id"),
            "projectName": workbook.get("project", {}).get("name"),
            "owner": workbook.get("owner", {}).get("name"),
            "showTabs": workbook.get("showTabs"),
            "message": "Workbook updated successfully"
        }

    def get_workbook_revisions(self, workbook_id: str) -> dict[str, Any]:
        """Get revision history for a workbook.

        Args:
            workbook_id: Workbook LUID

        Returns:
            List of revisions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/revisions"
        )
        data = self._parse_response(response)

        revisions = data.get("revisions", {}).get("revision", [])
        if isinstance(revisions, dict):
            revisions = [revisions]

        return {
            "revisions": [
                {
                    "revisionNumber": r.get("revisionNumber"),
                    "publishedAt": r.get("publishedAt"),
                    "deleted": r.get("deleted"),
                    "current": r.get("current"),
                    "publisherId": r.get("publisher", {}).get("id"),
                    "publisherName": r.get("publisher", {}).get("name")
                }
                for r in revisions
            ]
        }

    def download_workbook(
        self,
        workbook_id: str,
        filepath: str,
        include_extract: bool = True
    ) -> dict[str, Any]:
        """Download a workbook file (.twb or .twbx).

        Args:
            workbook_id: Workbook LUID
            filepath: Local path to save the file
            include_extract: If True, download .twbx with extract; if False, .twb only

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/workbooks/{workbook_id}/content"
        if not include_extract:
            url += "?includeExtract=false"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/octet-stream"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Workbook downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_workbook_revision(
        self,
        workbook_id: str,
        revision_number: int,
        filepath: str,
        include_extract: bool = True
    ) -> dict[str, Any]:
        """Download a specific revision of a workbook.

        Args:
            workbook_id: Workbook LUID
            revision_number: Revision number to download
            filepath: Local path to save the file
            include_extract: If True, download .twbx with extract; if False, .twb only

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/workbooks/{workbook_id}/revisions/{revision_number}/content"
        if not include_extract:
            url += "?includeExtract=false"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/octet-stream"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Workbook revision downloaded successfully",
            "filepath": filepath,
            "revisionNumber": revision_number,
            "size": len(response.content)
        }

    def download_workbook_pdf(
        self,
        workbook_id: str,
        filepath: str,
        page_type: str = "letter",
        orientation: str = "portrait"
    ) -> dict[str, Any]:
        """Download a workbook as PDF.

        Args:
            workbook_id: Workbook LUID
            filepath: Local path to save the PDF
            page_type: Page size (letter, legal, a4, a5, etc.)
            orientation: portrait or landscape

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = (
            f"{self.base_url}/sites/{self._site_id}/workbooks/{workbook_id}/pdf"
            f"?type={page_type}&orientation={orientation}"
        )

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/pdf"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Workbook PDF downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_workbook_powerpoint(
        self,
        workbook_id: str,
        filepath: str
    ) -> dict[str, Any]:
        """Download a workbook as PowerPoint.

        Args:
            workbook_id: Workbook LUID
            filepath: Local path to save the PPTX

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/workbooks/{workbook_id}/powerpoint"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Workbook PowerPoint downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def get_workbook_downgrade_info(
        self,
        workbook_id: str,
        target_version: str
    ) -> dict[str, Any]:
        """Get information about features that would be lost when downgrading.

        Args:
            workbook_id: Workbook LUID
            target_version: Target Tableau version (e.g., "2019.3")

        Returns:
            Downgrade impact information
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/downGradeInfo?productVersion={target_version}"
        )
        data = self._parse_response(response)

        downgrade_info = data.get("downgradeInfo", {})
        return {
            "affectedFeatures": downgrade_info.get("affectedFeatures", []),
            "message": downgrade_info.get("message")
        }

    def refresh_workbook(self, workbook_id: str) -> dict[str, Any]:
        """Refresh extracts in a workbook (Update Workbook Now).

        Args:
            workbook_id: Workbook LUID

        Returns:
            Job information for the refresh
        """
        self.ensure_authenticated()
        response = self._request(
            "POST",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/refresh"
        )
        data = self._parse_response(response)

        job = data.get("job", {})
        return {
            "jobId": job.get("id"),
            "mode": job.get("mode"),
            "type": job.get("type"),
            "createdAt": job.get("createdAt"),
            "message": "Workbook refresh started"
        }

    def add_tags_to_workbook(
        self,
        workbook_id: str,
        tags: list[str]
    ) -> dict[str, Any]:
        """Add tags to a workbook.

        Args:
            workbook_id: Workbook LUID
            tags: List of tag labels to add

        Returns:
            Updated tags list
        """
        self.ensure_authenticated()

        payload = {
            "tags": {
                "tag": [{"label": tag} for tag in tags]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/tags",
            data=payload
        )
        data = self._parse_response(response)

        result_tags = data.get("tags", {}).get("tag", [])
        if isinstance(result_tags, dict):
            result_tags = [result_tags]

        return {
            "tags": [t.get("label") for t in result_tags],
            "message": "Tags added successfully"
        }

    def delete_tag_from_workbook(
        self,
        workbook_id: str,
        tag_name: str
    ) -> dict[str, Any]:
        """Delete a tag from a workbook.

        Args:
            workbook_id: Workbook LUID
            tag_name: Tag label to remove

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/workbooks/{workbook_id}/tags/{tag_name}"
        )

        if response.status_code == 204:
            return {"message": "Tag deleted successfully"}

        return self._parse_response(response)

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

    def get_view_by_path(
        self,
        workbook_name: str,
        view_name: str
    ) -> dict[str, Any]:
        """Get a view using the workbook and view URL names.

        Args:
            workbook_name: Workbook URL name
            view_name: View URL name

        Returns:
            View details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/views?filter=viewUrlName:eq:{view_name}"
        )
        data = self._parse_response(response)

        views = data.get("views", {}).get("view", [])
        if isinstance(views, dict):
            views = [views]

        for view in views:
            if view.get("workbook", {}).get("name") == workbook_name:
                return {
                    "id": view.get("id"),
                    "name": view.get("name"),
                    "contentUrl": view.get("contentUrl"),
                    "workbookId": view.get("workbook", {}).get("id"),
                    "workbookName": view.get("workbook", {}).get("name")
                }

        raise Exception(f"View not found: {workbook_name}/{view_name}")

    def list_views(self) -> dict[str, Any]:
        """List all views in the current site.

        Returns:
            List of views
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/views")
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
                    "workbookId": v.get("workbook", {}).get("id"),
                    "ownerId": v.get("owner", {}).get("id"),
                    "totalViewCount": v.get("usage", {}).get("totalViewCount")
                }
                for v in views
            ]
        }

    def delete_view(self, view_id: str) -> dict[str, Any]:
        """Delete a view from a workbook.

        Args:
            view_id: View LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/views/{view_id}"
        )

        if response.status_code == 204:
            return {"message": "View deleted successfully"}

        return self._parse_response(response)

    def download_view_image(
        self,
        view_id: str,
        filepath: str,
        resolution: str | None = None,
        max_age: int | None = None
    ) -> dict[str, Any]:
        """Download a view as a PNG image.

        Args:
            view_id: View LUID
            filepath: Local path to save the image
            resolution: Image resolution (e.g., "high")
            max_age: Max age in minutes for cached image

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        params = []
        if resolution:
            params.append(f"resolution={resolution}")
        if max_age is not None:
            params.append(f"maxAge={max_age}")

        url = f"{self.base_url}/sites/{self._site_id}/views/{view_id}/image"
        if params:
            url += "?" + "&".join(params)

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "image/png"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "View image downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_view_pdf(
        self,
        view_id: str,
        filepath: str,
        page_type: str = "letter",
        orientation: str = "portrait"
    ) -> dict[str, Any]:
        """Download a view as PDF.

        Args:
            view_id: View LUID
            filepath: Local path to save the PDF
            page_type: Page size (letter, legal, a4, a5, etc.)
            orientation: portrait or landscape

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = (
            f"{self.base_url}/sites/{self._site_id}/views/{view_id}/pdf"
            f"?type={page_type}&orientation={orientation}"
        )

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/pdf"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "View PDF downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_view_data(
        self,
        view_id: str,
        filepath: str,
        max_age: int | None = None
    ) -> dict[str, Any]:
        """Download view data as CSV.

        Args:
            view_id: View LUID
            filepath: Local path to save the CSV
            max_age: Max age in minutes for cached data

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/views/{view_id}/data"
        if max_age is not None:
            url += f"?maxAge={max_age}"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "text/csv"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "View data downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_view_crosstab_excel(
        self,
        view_id: str,
        filepath: str,
        max_age: int | None = None
    ) -> dict[str, Any]:
        """Download view crosstab data as Excel.

        Args:
            view_id: View LUID
            filepath: Local path to save the Excel file
            max_age: Max age in minutes for cached data

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/views/{view_id}/crosstab/excel"
        if max_age is not None:
            url += f"?maxAge={max_age}"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "View crosstab Excel downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def add_tags_to_view(
        self,
        view_id: str,
        tags: list[str]
    ) -> dict[str, Any]:
        """Add tags to a view.

        Args:
            view_id: View LUID
            tags: List of tag labels to add

        Returns:
            Updated tags list
        """
        self.ensure_authenticated()

        payload = {
            "tags": {
                "tag": [{"label": tag} for tag in tags]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/views/{view_id}/tags",
            data=payload
        )
        data = self._parse_response(response)

        result_tags = data.get("tags", {}).get("tag", [])
        if isinstance(result_tags, dict):
            result_tags = [result_tags]

        return {
            "tags": [t.get("label") for t in result_tags],
            "message": "Tags added to view successfully"
        }

    def delete_tag_from_view(
        self,
        view_id: str,
        tag_name: str
    ) -> dict[str, Any]:
        """Delete a tag from a view.

        Args:
            view_id: View LUID
            tag_name: Tag label to remove

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/views/{view_id}/tags/{tag_name}"
        )

        if response.status_code == 204:
            return {"message": "Tag deleted from view successfully"}

        return self._parse_response(response)

    def get_recommendations_for_views(self) -> dict[str, Any]:
        """Get recommended views for the current user.

        Returns:
            List of recommended views
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/recommendations?type=view"
        )
        data = self._parse_response(response)

        recommendations = data.get("recommendations", {}).get("recommendation", [])
        if isinstance(recommendations, dict):
            recommendations = [recommendations]

        return {
            "recommendations": [
                {
                    "viewId": r.get("target", {}).get("view", {}).get("id"),
                    "viewName": r.get("target", {}).get("view", {}).get("name"),
                    "workbookId": r.get("target", {}).get("view", {}).get("workbook", {}).get("id"),
                    "workbookName": r.get("target", {}).get("view", {}).get("workbook", {}).get("name")
                }
                for r in recommendations
            ]
        }

    def hide_view_recommendation(
        self,
        recommendation_id: str
    ) -> dict[str, Any]:
        """Hide a view recommendation for the current user.

        Args:
            recommendation_id: Recommendation ID to hide

        Returns:
            Confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/recommendations/{recommendation_id}/hide"
        )

        if response.status_code == 204:
            return {"message": "Recommendation hidden successfully"}

        return self._parse_response(response)

    # Custom Views methods

    def list_custom_views(self) -> dict[str, Any]:
        """List all custom views in the current site.

        Returns:
            List of custom views
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/customviews")
        data = self._parse_response(response)

        custom_views = data.get("customViews", {}).get("customView", [])
        if isinstance(custom_views, dict):
            custom_views = [custom_views]

        return {
            "customViews": [
                {
                    "id": cv.get("id"),
                    "name": cv.get("name"),
                    "shared": cv.get("shared"),
                    "createdAt": cv.get("createdAt"),
                    "updatedAt": cv.get("updatedAt"),
                    "viewId": cv.get("view", {}).get("id"),
                    "viewName": cv.get("view", {}).get("name"),
                    "workbookId": cv.get("workbook", {}).get("id"),
                    "workbookName": cv.get("workbook", {}).get("name"),
                    "ownerId": cv.get("owner", {}).get("id"),
                    "ownerName": cv.get("owner", {}).get("name")
                }
                for cv in custom_views
            ]
        }

    def get_custom_view(self, custom_view_id: str) -> dict[str, Any]:
        """Get details for a specific custom view.

        Args:
            custom_view_id: Custom view LUID

        Returns:
            Custom view details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/customviews/{custom_view_id}"
        )
        data = self._parse_response(response)

        cv = data.get("customView", {})
        return {
            "id": cv.get("id"),
            "name": cv.get("name"),
            "shared": cv.get("shared"),
            "createdAt": cv.get("createdAt"),
            "updatedAt": cv.get("updatedAt"),
            "viewId": cv.get("view", {}).get("id"),
            "viewName": cv.get("view", {}).get("name"),
            "workbookId": cv.get("workbook", {}).get("id"),
            "workbookName": cv.get("workbook", {}).get("name"),
            "ownerId": cv.get("owner", {}).get("id"),
            "ownerName": cv.get("owner", {}).get("name")
        }

    def update_custom_view(
        self,
        custom_view_id: str,
        name: str | None = None,
        owner_id: str | None = None
    ) -> dict[str, Any]:
        """Update a custom view.

        Args:
            custom_view_id: Custom view LUID
            name: New name for the custom view
            owner_id: New owner user ID

        Returns:
            Updated custom view details
        """
        self.ensure_authenticated()

        cv_data: dict[str, Any] = {}
        if name is not None:
            cv_data["name"] = name
        if owner_id is not None:
            cv_data["owner"] = {"id": owner_id}

        payload = {"customView": cv_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/customviews/{custom_view_id}",
            data=payload
        )
        data = self._parse_response(response)

        cv = data.get("customView", {})
        return {
            "id": cv.get("id"),
            "name": cv.get("name"),
            "shared": cv.get("shared"),
            "ownerId": cv.get("owner", {}).get("id"),
            "message": "Custom view updated successfully"
        }

    def delete_custom_view(self, custom_view_id: str) -> dict[str, Any]:
        """Delete a custom view.

        Args:
            custom_view_id: Custom view LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/customviews/{custom_view_id}"
        )

        if response.status_code == 204:
            return {"message": "Custom view deleted successfully"}

        return self._parse_response(response)

    def download_custom_view_image(
        self,
        custom_view_id: str,
        filepath: str,
        resolution: str | None = None,
        max_age: int | None = None
    ) -> dict[str, Any]:
        """Download a custom view as a PNG image.

        Args:
            custom_view_id: Custom view LUID
            filepath: Local path to save the image
            resolution: Image resolution (e.g., "high")
            max_age: Max age in minutes for cached image

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        params = []
        if resolution:
            params.append(f"resolution={resolution}")
        if max_age is not None:
            params.append(f"maxAge={max_age}")

        url = f"{self.base_url}/sites/{self._site_id}/customviews/{custom_view_id}/image"
        if params:
            url += "?" + "&".join(params)

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "image/png"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Custom view image downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_custom_view_pdf(
        self,
        custom_view_id: str,
        filepath: str,
        page_type: str = "letter",
        orientation: str = "portrait"
    ) -> dict[str, Any]:
        """Download a custom view as PDF.

        Args:
            custom_view_id: Custom view LUID
            filepath: Local path to save the PDF
            page_type: Page size (letter, legal, a4, a5, etc.)
            orientation: portrait or landscape

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = (
            f"{self.base_url}/sites/{self._site_id}/customviews/{custom_view_id}/pdf"
            f"?type={page_type}&orientation={orientation}"
        )

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/pdf"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Custom view PDF downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    def download_custom_view_data(
        self,
        custom_view_id: str,
        filepath: str,
        max_age: int | None = None
    ) -> dict[str, Any]:
        """Download custom view data as CSV.

        Args:
            custom_view_id: Custom view LUID
            filepath: Local path to save the CSV
            max_age: Max age in minutes for cached data

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/customviews/{custom_view_id}/data"
        if max_age is not None:
            url += f"?maxAge={max_age}"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "text/csv"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Custom view data downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
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

    # Project methods

    def get_project(self, project_id: str) -> dict[str, Any]:
        """Get details for a specific project.

        Args:
            project_id: Project LUID

        Returns:
            Project details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/projects/{project_id}"
        )
        data = self._parse_response(response)

        project = data.get("project", {})
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "parentProjectId": project.get("parentProjectId"),
            "contentPermissions": project.get("contentPermissions"),
            "createdAt": project.get("createdAt"),
            "updatedAt": project.get("updatedAt")
        }

    def create_project(
        self,
        name: str,
        description: str | None = None,
        parent_project_id: str | None = None,
        content_permissions: str = "ManagedByOwner"
    ) -> dict[str, Any]:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            parent_project_id: Parent project LUID for nested projects
            content_permissions: Permission mode (ManagedByOwner, LockedToProject, etc.)

        Returns:
            Created project details
        """
        self.ensure_authenticated()

        project_data: dict[str, Any] = {
            "name": name,
            "contentPermissions": content_permissions
        }
        if description:
            project_data["description"] = description
        if parent_project_id:
            project_data["parentProjectId"] = parent_project_id

        payload = {"project": project_data}

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/projects",
            data=payload
        )
        data = self._parse_response(response)

        project = data.get("project", {})
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "parentProjectId": project.get("parentProjectId"),
            "contentPermissions": project.get("contentPermissions"),
            "message": "Project created successfully"
        }

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        parent_project_id: str | None = None,
        content_permissions: str | None = None
    ) -> dict[str, Any]:
        """Update a project.

        Args:
            project_id: Project LUID
            name: New project name
            description: New description
            parent_project_id: New parent project ID
            content_permissions: New permission mode

        Returns:
            Updated project details
        """
        self.ensure_authenticated()

        project_data: dict[str, Any] = {}
        if name is not None:
            project_data["name"] = name
        if description is not None:
            project_data["description"] = description
        if parent_project_id is not None:
            project_data["parentProjectId"] = parent_project_id
        if content_permissions is not None:
            project_data["contentPermissions"] = content_permissions

        payload = {"project": project_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/projects/{project_id}",
            data=payload
        )
        data = self._parse_response(response)

        project = data.get("project", {})
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "contentPermissions": project.get("contentPermissions"),
            "message": "Project updated successfully"
        }

    def delete_project(self, project_id: str) -> dict[str, Any]:
        """Delete a project.

        Args:
            project_id: Project LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/projects/{project_id}"
        )

        if response.status_code == 204:
            return {"message": "Project deleted successfully"}

        return self._parse_response(response)

    def get_project_permissions(self, project_id: str) -> dict[str, Any]:
        """Get permissions for a project.

        Args:
            project_id: Project LUID

        Returns:
            Project permissions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/projects/{project_id}/permissions"
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

    def add_project_permission(
        self,
        project_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Add a permission to a project.

        Args:
            project_id: Project LUID
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
            f"/sites/{self._site_id}/projects/{project_id}/permissions",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "Permission added successfully", "data": data}

    def delete_project_permission(
        self,
        project_id: str,
        user_id: str,
        capability_name: str,
        capability_mode: str
    ) -> dict[str, Any]:
        """Delete a permission from a project.

        Args:
            project_id: Project LUID
            user_id: User LUID
            capability_name: Capability name
            capability_mode: Allow or Deny

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()

        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/projects/{project_id}/permissions/users/{user_id}/{capability_name}/{capability_mode}"
        )

        if response.status_code == 204:
            return {"message": "Permission deleted successfully"}

        return self._parse_response(response)

    # Flow methods

    def list_flows(self) -> dict[str, Any]:
        """List all flows in the current site.

        Returns:
            List of flows
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/flows")
        data = self._parse_response(response)

        flows = data.get("flows", {}).get("flow", [])
        if isinstance(flows, dict):
            flows = [flows]

        return {
            "flows": [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "description": f.get("description"),
                    "projectId": f.get("project", {}).get("id"),
                    "projectName": f.get("project", {}).get("name"),
                    "owner": f.get("owner", {}).get("name"),
                    "createdAt": f.get("createdAt"),
                    "updatedAt": f.get("updatedAt")
                }
                for f in flows
            ]
        }

    def get_flow(self, flow_id: str) -> dict[str, Any]:
        """Get details for a specific flow.

        Args:
            flow_id: Flow LUID

        Returns:
            Flow details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/flows/{flow_id}"
        )
        data = self._parse_response(response)

        flow = data.get("flow", {})
        return {
            "id": flow.get("id"),
            "name": flow.get("name"),
            "description": flow.get("description"),
            "projectId": flow.get("project", {}).get("id"),
            "projectName": flow.get("project", {}).get("name"),
            "owner": flow.get("owner", {}).get("name"),
            "ownerId": flow.get("owner", {}).get("id"),
            "createdAt": flow.get("createdAt"),
            "updatedAt": flow.get("updatedAt"),
            "webpageUrl": flow.get("webpageUrl")
        }

    def delete_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete a flow.

        Args:
            flow_id: Flow LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/flows/{flow_id}"
        )

        if response.status_code == 204:
            return {"message": "Flow deleted successfully"}

        return self._parse_response(response)

    def run_flow(self, flow_id: str) -> dict[str, Any]:
        """Run a flow now.

        Args:
            flow_id: Flow LUID

        Returns:
            Job information for the flow run
        """
        self.ensure_authenticated()
        response = self._request(
            "POST",
            f"/sites/{self._site_id}/flows/{flow_id}/run"
        )
        data = self._parse_response(response)

        job = data.get("job", {})
        return {
            "jobId": job.get("id"),
            "mode": job.get("mode"),
            "type": job.get("type"),
            "createdAt": job.get("createdAt"),
            "message": "Flow run started"
        }

    def update_flow(
        self,
        flow_id: str,
        name: str | None = None,
        project_id: str | None = None,
        owner_id: str | None = None
    ) -> dict[str, Any]:
        """Update a flow.

        Args:
            flow_id: Flow LUID
            name: New name for the flow
            project_id: New project ID
            owner_id: New owner user ID

        Returns:
            Updated flow details
        """
        self.ensure_authenticated()

        flow_data: dict[str, Any] = {}
        if name is not None:
            flow_data["name"] = name
        if project_id is not None:
            flow_data["project"] = {"id": project_id}
        if owner_id is not None:
            flow_data["owner"] = {"id": owner_id}

        payload = {"flow": flow_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/flows/{flow_id}",
            data=payload
        )
        data = self._parse_response(response)

        flow = data.get("flow", {})
        return {
            "id": flow.get("id"),
            "name": flow.get("name"),
            "projectId": flow.get("project", {}).get("id"),
            "owner": flow.get("owner", {}).get("name"),
            "message": "Flow updated successfully"
        }

    def get_flow_permissions(self, flow_id: str) -> dict[str, Any]:
        """Get permissions for a flow.

        Args:
            flow_id: Flow LUID

        Returns:
            Flow permissions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/flows/{flow_id}/permissions"
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

    def list_flow_runs(self) -> dict[str, Any]:
        """List all flow runs in the current site.

        Returns:
            List of flow runs
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/flows/runs")
        data = self._parse_response(response)

        runs = data.get("flowRuns", {}).get("flowRun", [])
        if isinstance(runs, dict):
            runs = [runs]

        return {
            "flowRuns": [
                {
                    "id": r.get("id"),
                    "flowId": r.get("flow", {}).get("id"),
                    "flowName": r.get("flow", {}).get("name"),
                    "status": r.get("status"),
                    "startedAt": r.get("startedAt"),
                    "completedAt": r.get("completedAt"),
                    "progress": r.get("progress")
                }
                for r in runs
            ]
        }

    def get_flow_run(self, flow_run_id: str) -> dict[str, Any]:
        """Get details for a specific flow run.

        Args:
            flow_run_id: Flow run LUID

        Returns:
            Flow run details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/flows/runs/{flow_run_id}"
        )
        data = self._parse_response(response)

        run = data.get("flowRun", {})
        return {
            "id": run.get("id"),
            "flowId": run.get("flow", {}).get("id"),
            "flowName": run.get("flow", {}).get("name"),
            "status": run.get("status"),
            "startedAt": run.get("startedAt"),
            "completedAt": run.get("completedAt"),
            "progress": run.get("progress"),
            "backgroundJobId": run.get("backgroundJob", {}).get("id")
        }

    def cancel_flow_run(self, flow_run_id: str) -> dict[str, Any]:
        """Cancel a running flow.

        Args:
            flow_run_id: Flow run LUID

        Returns:
            Cancellation confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/flows/runs/{flow_run_id}"
        )

        if response.status_code == 204:
            return {"message": "Flow run cancelled successfully"}

        return self._parse_response(response)

    def add_tags_to_flow(
        self,
        flow_id: str,
        tags: list[str]
    ) -> dict[str, Any]:
        """Add tags to a flow.

        Args:
            flow_id: Flow LUID
            tags: List of tag labels to add

        Returns:
            Updated tags list
        """
        self.ensure_authenticated()

        payload = {
            "tags": {
                "tag": [{"label": tag} for tag in tags]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/flows/{flow_id}/tags",
            data=payload
        )
        data = self._parse_response(response)

        result_tags = data.get("tags", {}).get("tag", [])
        if isinstance(result_tags, dict):
            result_tags = [result_tags]

        return {
            "tags": [t.get("label") for t in result_tags],
            "message": "Tags added to flow successfully"
        }

    def delete_tag_from_flow(
        self,
        flow_id: str,
        tag_name: str
    ) -> dict[str, Any]:
        """Delete a tag from a flow.

        Args:
            flow_id: Flow LUID
            tag_name: Tag label to remove

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/flows/{flow_id}/tags/{tag_name}"
        )

        if response.status_code == 204:
            return {"message": "Tag deleted from flow successfully"}

        return self._parse_response(response)

    # Webhook methods

    def list_webhooks(self) -> dict[str, Any]:
        """List all webhooks in the current site.

        Returns:
            List of webhooks
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/webhooks")
        data = self._parse_response(response)

        webhooks = data.get("webhooks", {}).get("webhook", [])
        if isinstance(webhooks, dict):
            webhooks = [webhooks]

        return {
            "webhooks": [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "event": w.get("webhook-source-api-event-name"),
                    "url": w.get("webhook-destination-http", {}).get("url"),
                    "isEnabled": w.get("isEnabled"),
                    "createdAt": w.get("createdAt"),
                    "updatedAt": w.get("updatedAt")
                }
                for w in webhooks
            ]
        }

    def get_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Get details for a specific webhook.

        Args:
            webhook_id: Webhook LUID

        Returns:
            Webhook details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/webhooks/{webhook_id}"
        )
        data = self._parse_response(response)

        webhook = data.get("webhook", {})
        return {
            "id": webhook.get("id"),
            "name": webhook.get("name"),
            "event": webhook.get("webhook-source-api-event-name"),
            "url": webhook.get("webhook-destination-http", {}).get("url"),
            "isEnabled": webhook.get("isEnabled"),
            "createdAt": webhook.get("createdAt"),
            "updatedAt": webhook.get("updatedAt"),
            "ownerId": webhook.get("owner", {}).get("id")
        }

    def create_webhook(
        self,
        name: str,
        event: str,
        url: str
    ) -> dict[str, Any]:
        """Create a new webhook.

        Args:
            name: Webhook name
            event: Event type (e.g., webhook-source-event-datasource-refresh-succeeded)
            url: Destination URL

        Returns:
            Created webhook details
        """
        self.ensure_authenticated()

        payload = {
            "webhook": {
                "webhook-source": {
                    "webhook-source-api-event-name": event
                },
                "webhook-destination": {
                    "webhook-destination-http": {
                        "method": "POST",
                        "url": url
                    }
                },
                "name": name
            }
        }

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/webhooks",
            data=payload
        )
        data = self._parse_response(response)

        webhook = data.get("webhook", {})
        return {
            "id": webhook.get("id"),
            "name": webhook.get("name"),
            "event": webhook.get("webhook-source-api-event-name"),
            "url": webhook.get("webhook-destination-http", {}).get("url"),
            "message": "Webhook created successfully"
        }

    def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook.

        Args:
            webhook_id: Webhook LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/webhooks/{webhook_id}"
        )

        if response.status_code == 204:
            return {"message": "Webhook deleted successfully"}

        return self._parse_response(response)

    def test_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Test a webhook by sending a test payload.

        Args:
            webhook_id: Webhook LUID

        Returns:
            Test result
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/webhooks/{webhook_id}/test"
        )
        data = self._parse_response(response)

        return {
            "status": data.get("webhookTestResult", {}).get("status"),
            "body": data.get("webhookTestResult", {}).get("body")
        }

    # Data Alert methods

    def list_data_alerts(self) -> dict[str, Any]:
        """List all data-driven alerts in the current site.

        Returns:
            List of data alerts
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/sites/{self._site_id}/dataAlerts")
        data = self._parse_response(response)

        alerts = data.get("dataAlerts", {}).get("dataAlert", [])
        if isinstance(alerts, dict):
            alerts = [alerts]

        return {
            "dataAlerts": [
                {
                    "id": a.get("id"),
                    "subject": a.get("subject"),
                    "frequency": a.get("frequency"),
                    "public": a.get("public"),
                    "ownerId": a.get("owner", {}).get("id"),
                    "ownerName": a.get("owner", {}).get("name"),
                    "viewId": a.get("view", {}).get("id"),
                    "viewName": a.get("view", {}).get("name"),
                    "createdAt": a.get("createdAt"),
                    "updatedAt": a.get("updatedAt")
                }
                for a in alerts
            ]
        }

    def get_data_alert(self, data_alert_id: str) -> dict[str, Any]:
        """Get details for a specific data alert.

        Args:
            data_alert_id: Data alert LUID

        Returns:
            Data alert details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/dataAlerts/{data_alert_id}"
        )
        data = self._parse_response(response)

        alert = data.get("dataAlert", {})
        return {
            "id": alert.get("id"),
            "subject": alert.get("subject"),
            "frequency": alert.get("frequency"),
            "public": alert.get("public"),
            "ownerId": alert.get("owner", {}).get("id"),
            "ownerName": alert.get("owner", {}).get("name"),
            "viewId": alert.get("view", {}).get("id"),
            "viewName": alert.get("view", {}).get("name"),
            "createdAt": alert.get("createdAt"),
            "updatedAt": alert.get("updatedAt")
        }

    def delete_data_alert(self, data_alert_id: str) -> dict[str, Any]:
        """Delete a data alert.

        Args:
            data_alert_id: Data alert LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/dataAlerts/{data_alert_id}"
        )

        if response.status_code == 204:
            return {"message": "Data alert deleted successfully"}

        return self._parse_response(response)

    def add_user_to_data_alert(
        self,
        data_alert_id: str,
        user_id: str
    ) -> dict[str, Any]:
        """Add a user to a data alert.

        Args:
            data_alert_id: Data alert LUID
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
            f"/sites/{self._site_id}/dataAlerts/{data_alert_id}/users",
            data=payload
        )
        data = self._parse_response(response)

        return {"message": "User added to data alert", "user": data.get("user", {})}

    def remove_user_from_data_alert(
        self,
        data_alert_id: str,
        user_id: str
    ) -> dict[str, Any]:
        """Remove a user from a data alert.

        Args:
            data_alert_id: Data alert LUID
            user_id: User LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/dataAlerts/{data_alert_id}/users/{user_id}"
        )

        if response.status_code == 204:
            return {"message": "User removed from data alert"}

        return self._parse_response(response)

    # Site methods (Server Admin only)

    def get_site(self, site_id: str | None = None) -> dict[str, Any]:
        """Get details for a specific site.

        Args:
            site_id: Site LUID (defaults to current site)

        Returns:
            Site details
        """
        self.ensure_authenticated()
        if site_id is None:
            site_id = self._site_id

        response = self._request("GET", f"/sites/{site_id}")
        data = self._parse_response(response)

        site = data.get("site", {})
        return {
            "id": site.get("id"),
            "name": site.get("name"),
            "contentUrl": site.get("contentUrl"),
            "state": site.get("state"),
            "adminMode": site.get("adminMode"),
            "userQuota": site.get("userQuota"),
            "storageQuota": site.get("storageQuota"),
            "disableSubscriptions": site.get("disableSubscriptions")
        }

    def create_site(
        self,
        name: str,
        content_url: str,
        admin_mode: str = "ContentAndUsers",
        user_quota: int | None = None,
        storage_quota: int | None = None
    ) -> dict[str, Any]:
        """Create a new site (Server Admin only).

        Args:
            name: Site name
            content_url: Site content URL
            admin_mode: ContentAndUsers or ContentOnly
            user_quota: Maximum users allowed
            storage_quota: Maximum storage in MB

        Returns:
            Created site details
        """
        self.ensure_authenticated()

        site_data: dict[str, Any] = {
            "name": name,
            "contentUrl": content_url,
            "adminMode": admin_mode
        }
        if user_quota is not None:
            site_data["userQuota"] = user_quota
        if storage_quota is not None:
            site_data["storageQuota"] = storage_quota

        payload = {"site": site_data}

        response = self._request(
            "POST",
            "/sites",
            data=payload
        )
        data = self._parse_response(response)

        site = data.get("site", {})
        return {
            "id": site.get("id"),
            "name": site.get("name"),
            "contentUrl": site.get("contentUrl"),
            "state": site.get("state"),
            "message": "Site created successfully"
        }

    def update_site(
        self,
        site_id: str,
        name: str | None = None,
        content_url: str | None = None,
        admin_mode: str | None = None,
        state: str | None = None,
        user_quota: int | None = None,
        storage_quota: int | None = None
    ) -> dict[str, Any]:
        """Update a site (Server Admin only).

        Args:
            site_id: Site LUID
            name: New site name
            content_url: New content URL
            admin_mode: ContentAndUsers or ContentOnly
            state: Active or Suspended
            user_quota: Maximum users allowed
            storage_quota: Maximum storage in MB

        Returns:
            Updated site details
        """
        self.ensure_authenticated()

        site_data: dict[str, Any] = {}
        if name is not None:
            site_data["name"] = name
        if content_url is not None:
            site_data["contentUrl"] = content_url
        if admin_mode is not None:
            site_data["adminMode"] = admin_mode
        if state is not None:
            site_data["state"] = state
        if user_quota is not None:
            site_data["userQuota"] = user_quota
        if storage_quota is not None:
            site_data["storageQuota"] = storage_quota

        payload = {"site": site_data}

        response = self._request(
            "PUT",
            f"/sites/{site_id}",
            data=payload
        )
        data = self._parse_response(response)

        site = data.get("site", {})
        return {
            "id": site.get("id"),
            "name": site.get("name"),
            "contentUrl": site.get("contentUrl"),
            "state": site.get("state"),
            "message": "Site updated successfully"
        }

    def delete_site(self, site_id: str) -> dict[str, Any]:
        """Delete a site (Server Admin only).

        Args:
            site_id: Site LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{site_id}"
        )

        if response.status_code == 204:
            return {"message": "Site deleted successfully"}

        return self._parse_response(response)

    # User update method

    def update_user(
        self,
        user_id: str,
        full_name: str | None = None,
        email: str | None = None,
        site_role: str | None = None,
        auth_setting: str | None = None
    ) -> dict[str, Any]:
        """Update a user.

        Args:
            user_id: User LUID
            full_name: New full name
            email: New email
            site_role: New site role
            auth_setting: Authentication setting

        Returns:
            Updated user details
        """
        self.ensure_authenticated()

        user_data: dict[str, Any] = {}
        if full_name is not None:
            user_data["fullName"] = full_name
        if email is not None:
            user_data["email"] = email
        if site_role is not None:
            user_data["siteRole"] = site_role
        if auth_setting is not None:
            user_data["authSetting"] = auth_setting

        payload = {"user": user_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/users/{user_id}",
            data=payload
        )
        data = self._parse_response(response)

        user = data.get("user", {})
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "fullName": user.get("fullName"),
            "email": user.get("email"),
            "siteRole": user.get("siteRole"),
            "message": "User updated successfully"
        }

    # Group CRUD methods

    def create_group(
        self,
        name: str,
        minimum_site_role: str | None = None
    ) -> dict[str, Any]:
        """Create a new local group.

        Args:
            name: Group name
            minimum_site_role: Minimum site role for group members

        Returns:
            Created group details
        """
        self.ensure_authenticated()

        group_data: dict[str, Any] = {"name": name}
        if minimum_site_role:
            group_data["minimumSiteRole"] = minimum_site_role

        payload = {"group": group_data}

        response = self._request(
            "POST",
            f"/sites/{self._site_id}/groups",
            data=payload
        )
        data = self._parse_response(response)

        group = data.get("group", {})
        return {
            "id": group.get("id"),
            "name": group.get("name"),
            "minimumSiteRole": group.get("minimumSiteRole"),
            "message": "Group created successfully"
        }

    def update_group(
        self,
        group_id: str,
        name: str | None = None,
        minimum_site_role: str | None = None
    ) -> dict[str, Any]:
        """Update a group.

        Args:
            group_id: Group LUID
            name: New group name
            minimum_site_role: New minimum site role

        Returns:
            Updated group details
        """
        self.ensure_authenticated()

        group_data: dict[str, Any] = {}
        if name is not None:
            group_data["name"] = name
        if minimum_site_role is not None:
            group_data["minimumSiteRole"] = minimum_site_role

        payload = {"group": group_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/groups/{group_id}",
            data=payload
        )
        data = self._parse_response(response)

        group = data.get("group", {})
        return {
            "id": group.get("id"),
            "name": group.get("name"),
            "minimumSiteRole": group.get("minimumSiteRole"),
            "message": "Group updated successfully"
        }

    def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group.

        Args:
            group_id: Group LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/groups/{group_id}"
        )

        if response.status_code == 204:
            return {"message": "Group deleted successfully"}

        return self._parse_response(response)

    # Data source extended methods

    def update_datasource(
        self,
        datasource_id: str,
        name: str | None = None,
        project_id: str | None = None,
        owner_id: str | None = None,
        is_certified: bool | None = None,
        certification_note: str | None = None
    ) -> dict[str, Any]:
        """Update a data source.

        Args:
            datasource_id: Data source LUID
            name: New name
            project_id: New project ID
            owner_id: New owner user ID
            is_certified: Certification status
            certification_note: Certification note

        Returns:
            Updated data source details
        """
        self.ensure_authenticated()

        ds_data: dict[str, Any] = {}
        if name is not None:
            ds_data["name"] = name
        if project_id is not None:
            ds_data["project"] = {"id": project_id}
        if owner_id is not None:
            ds_data["owner"] = {"id": owner_id}
        if is_certified is not None:
            ds_data["isCertified"] = is_certified
        if certification_note is not None:
            ds_data["certificationNote"] = certification_note

        payload = {"datasource": ds_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/datasources/{datasource_id}",
            data=payload
        )
        data = self._parse_response(response)

        ds = data.get("datasource", {})
        return {
            "id": ds.get("id"),
            "name": ds.get("name"),
            "projectId": ds.get("project", {}).get("id"),
            "owner": ds.get("owner", {}).get("name"),
            "isCertified": ds.get("isCertified"),
            "message": "Data source updated successfully"
        }

    def refresh_datasource(self, datasource_id: str) -> dict[str, Any]:
        """Refresh a data source extract now.

        Args:
            datasource_id: Data source LUID

        Returns:
            Job information for the refresh
        """
        self.ensure_authenticated()
        response = self._request(
            "POST",
            f"/sites/{self._site_id}/datasources/{datasource_id}/refresh"
        )
        data = self._parse_response(response)

        job = data.get("job", {})
        return {
            "jobId": job.get("id"),
            "mode": job.get("mode"),
            "type": job.get("type"),
            "createdAt": job.get("createdAt"),
            "message": "Data source refresh started"
        }

    def add_tags_to_datasource(
        self,
        datasource_id: str,
        tags: list[str]
    ) -> dict[str, Any]:
        """Add tags to a data source.

        Args:
            datasource_id: Data source LUID
            tags: List of tag labels to add

        Returns:
            Updated tags list
        """
        self.ensure_authenticated()

        payload = {
            "tags": {
                "tag": [{"label": tag} for tag in tags]
            }
        }

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/datasources/{datasource_id}/tags",
            data=payload
        )
        data = self._parse_response(response)

        result_tags = data.get("tags", {}).get("tag", [])
        if isinstance(result_tags, dict):
            result_tags = [result_tags]

        return {
            "tags": [t.get("label") for t in result_tags],
            "message": "Tags added to data source successfully"
        }

    def delete_tag_from_datasource(
        self,
        datasource_id: str,
        tag_name: str
    ) -> dict[str, Any]:
        """Delete a tag from a data source.

        Args:
            datasource_id: Data source LUID
            tag_name: Tag label to remove

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/datasources/{datasource_id}/tags/{tag_name}"
        )

        if response.status_code == 204:
            return {"message": "Tag deleted from data source successfully"}

        return self._parse_response(response)

    def get_datasource_revisions(self, datasource_id: str) -> dict[str, Any]:
        """Get revision history for a data source.

        Args:
            datasource_id: Data source LUID

        Returns:
            List of revisions
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/datasources/{datasource_id}/revisions"
        )
        data = self._parse_response(response)

        revisions = data.get("revisions", {}).get("revision", [])
        if isinstance(revisions, dict):
            revisions = [revisions]

        return {
            "revisions": [
                {
                    "revisionNumber": r.get("revisionNumber"),
                    "publishedAt": r.get("publishedAt"),
                    "deleted": r.get("deleted"),
                    "current": r.get("current"),
                    "publisherId": r.get("publisher", {}).get("id"),
                    "publisherName": r.get("publisher", {}).get("name")
                }
                for r in revisions
            ]
        }

    def download_datasource(
        self,
        datasource_id: str,
        filepath: str,
        include_extract: bool = True
    ) -> dict[str, Any]:
        """Download a data source file (.tds or .tdsx).

        Args:
            datasource_id: Data source LUID
            filepath: Local path to save the file
            include_extract: If True, download .tdsx with extract; if False, .tds only

        Returns:
            Download confirmation with file path
        """
        self.ensure_authenticated()

        url = f"{self.base_url}/sites/{self._site_id}/datasources/{datasource_id}/content"
        if not include_extract:
            url += "?includeExtract=false"

        headers = {
            "X-Tableau-Auth": self._token,
            "Accept": "application/octet-stream"
        }

        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        with open(filepath, "wb") as f:
            f.write(response.content)

        return {
            "message": "Data source downloaded successfully",
            "filepath": filepath,
            "size": len(response.content)
        }

    # Server Info

    def get_server_info(self) -> dict[str, Any]:
        """Get server information (version, build, etc.).

        Returns:
            Server information
        """
        response = self._request(
            "GET",
            "/serverinfo",
            require_auth=False
        )
        data = self._parse_response(response)

        server_info = data.get("serverInfo", {})
        return {
            "productVersion": server_info.get("productVersion", {}).get("value"),
            "buildNumber": server_info.get("productVersion", {}).get("build"),
            "restApiVersion": server_info.get("restApiVersion")
        }

    # Tasks methods

    def list_tasks(self) -> dict[str, Any]:
        """List all extract refresh tasks.

        Returns:
            List of tasks
        """
        return self.list_extract_tasks()

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get details for a specific extract refresh task.

        Args:
            task_id: Task LUID

        Returns:
            Task details
        """
        self.ensure_authenticated()
        response = self._request(
            "GET",
            f"/sites/{self._site_id}/tasks/extractRefreshes/{task_id}"
        )
        data = self._parse_response(response)

        task = data.get("task", {}).get("extractRefresh", {})
        return {
            "id": task.get("id"),
            "priority": task.get("priority"),
            "type": task.get("type"),
            "consecutiveFailedCount": task.get("consecutiveFailedCount"),
            "workbookId": task.get("workbook", {}).get("id"),
            "datasourceId": task.get("datasource", {}).get("id")
        }

    def run_task(self, task_id: str) -> dict[str, Any]:
        """Run an extract refresh task now.

        Args:
            task_id: Task LUID

        Returns:
            Job information
        """
        return self.run_extract_refresh(task_id)

    def delete_task(self, task_id: str) -> dict[str, Any]:
        """Delete an extract refresh task.

        Args:
            task_id: Task LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/sites/{self._site_id}/tasks/extractRefreshes/{task_id}"
        )

        if response.status_code == 204:
            return {"message": "Task deleted successfully"}

        return self._parse_response(response)

    # Schedule CRUD methods

    def get_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Get details for a specific schedule.

        Args:
            schedule_id: Schedule LUID

        Returns:
            Schedule details
        """
        self.ensure_authenticated()
        response = self._request("GET", f"/schedules/{schedule_id}")
        data = self._parse_response(response)

        schedule = data.get("schedule", {})
        return {
            "id": schedule.get("id"),
            "name": schedule.get("name"),
            "type": schedule.get("type"),
            "state": schedule.get("state"),
            "priority": schedule.get("priority"),
            "frequency": schedule.get("frequency"),
            "nextRunAt": schedule.get("nextRunAt"),
            "createdAt": schedule.get("createdAt"),
            "updatedAt": schedule.get("updatedAt")
        }

    def create_schedule(
        self,
        name: str,
        schedule_type: str,
        frequency: str,
        start_time: str,
        priority: int = 50,
        execution_order: str = "Parallel"
    ) -> dict[str, Any]:
        """Create a new schedule (Server only).

        Args:
            name: Schedule name
            schedule_type: Extract or Subscription
            frequency: Hourly, Daily, Weekly, Monthly
            start_time: Start time in HH:MM:SS format
            priority: Priority (1-100, default 50)
            execution_order: Parallel or Serial

        Returns:
            Created schedule details
        """
        self.ensure_authenticated()

        payload = {
            "schedule": {
                "name": name,
                "type": schedule_type,
                "frequency": frequency,
                "frequencyDetails": {
                    "start": start_time
                },
                "priority": priority,
                "executionOrder": execution_order
            }
        }

        response = self._request(
            "POST",
            "/schedules",
            data=payload
        )
        data = self._parse_response(response)

        schedule = data.get("schedule", {})
        return {
            "id": schedule.get("id"),
            "name": schedule.get("name"),
            "type": schedule.get("type"),
            "frequency": schedule.get("frequency"),
            "message": "Schedule created successfully"
        }

    def update_schedule(
        self,
        schedule_id: str,
        name: str | None = None,
        state: str | None = None,
        priority: int | None = None,
        frequency: str | None = None
    ) -> dict[str, Any]:
        """Update a schedule (Server only).

        Args:
            schedule_id: Schedule LUID
            name: New schedule name
            state: Active or Suspended
            priority: New priority (1-100)
            frequency: New frequency

        Returns:
            Updated schedule details
        """
        self.ensure_authenticated()

        schedule_data: dict[str, Any] = {}
        if name is not None:
            schedule_data["name"] = name
        if state is not None:
            schedule_data["state"] = state
        if priority is not None:
            schedule_data["priority"] = priority
        if frequency is not None:
            schedule_data["frequency"] = frequency

        payload = {"schedule": schedule_data}

        response = self._request(
            "PUT",
            f"/schedules/{schedule_id}",
            data=payload
        )
        data = self._parse_response(response)

        schedule = data.get("schedule", {})
        return {
            "id": schedule.get("id"),
            "name": schedule.get("name"),
            "state": schedule.get("state"),
            "priority": schedule.get("priority"),
            "message": "Schedule updated successfully"
        }

    def delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Delete a schedule (Server only).

        Args:
            schedule_id: Schedule LUID

        Returns:
            Deletion confirmation
        """
        self.ensure_authenticated()
        response = self._request(
            "DELETE",
            f"/schedules/{schedule_id}"
        )

        if response.status_code == 204:
            return {"message": "Schedule deleted successfully"}

        return self._parse_response(response)

    # Subscription update

    def update_subscription(
        self,
        subscription_id: str,
        subject: str | None = None,
        schedule_id: str | None = None,
        suspended: bool | None = None
    ) -> dict[str, Any]:
        """Update a subscription.

        Args:
            subscription_id: Subscription LUID
            subject: New email subject
            schedule_id: New schedule ID
            suspended: Whether subscription is suspended

        Returns:
            Updated subscription details
        """
        self.ensure_authenticated()

        sub_data: dict[str, Any] = {}
        if subject is not None:
            sub_data["subject"] = subject
        if schedule_id is not None:
            sub_data["schedule"] = {"id": schedule_id}
        if suspended is not None:
            sub_data["suspended"] = suspended

        payload = {"subscription": sub_data}

        response = self._request(
            "PUT",
            f"/sites/{self._site_id}/subscriptions/{subscription_id}",
            data=payload
        )
        data = self._parse_response(response)

        sub = data.get("subscription", {})
        return {
            "id": sub.get("id"),
            "subject": sub.get("subject"),
            "suspended": sub.get("suspended"),
            "message": "Subscription updated successfully"
        }
