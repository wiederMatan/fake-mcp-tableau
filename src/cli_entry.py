#!/usr/bin/env python3
"""CLI entry point for Tableau API operations."""

import argparse
import json
import sys
from typing import Any

from .engine import TableauEngine


def output_response(success: bool, data: Any = None, error: str | None = None) -> None:
    """Print JSON response and exit."""
    response = {
        "success": success,
        "data": data,
        "error": error
    }
    print(json.dumps(response, indent=2))
    sys.exit(0 if success else 1)


def handle_auth(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle authentication commands."""
    handlers = {
        "login": engine.sign_in,
        "logout": engine.sign_out,
        "status": engine.get_auth_status,
    }
    result = handlers[args.auth_command]()
    output_response(True, result)


def handle_list(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle list commands."""
    handlers = {
        "sites": engine.list_sites,
        "projects": engine.list_projects,
        "workbooks": engine.list_workbooks,
        "views": engine.list_views,
        "custom-views": engine.list_custom_views,
        "refresh-tasks": engine.list_extract_tasks,
        "tasks": engine.list_tasks,
        "users": engine.list_users,
        "groups": engine.list_groups,
        "datasources": engine.list_datasources,
        "jobs": engine.list_jobs,
        "schedules": engine.list_schedules,
        "subscriptions": engine.list_subscriptions,
        "flows": engine.list_flows,
        "flow-runs": engine.list_flow_runs,
        "webhooks": engine.list_webhooks,
        "data-alerts": engine.list_data_alerts,
    }
    handler = handlers.get(args.list_type)
    if handler:
        result = handler()
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown list type: {args.list_type}")


def handle_get(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle get commands."""
    if args.get_type == "server-info":
        result = engine.get_server_info()
        output_response(True, result)
    elif args.get_type == "view-recommendations":
        result = engine.get_recommendations_for_views()
        output_response(True, result)
    elif not args.id:
        output_response(False, error="Resource ID required")
    else:
        handlers = {
            "workbook": engine.get_workbook,
            "user": engine.get_user,
            "datasource": engine.get_datasource,
            "job": engine.get_job,
            "view": engine.get_view,
            "custom-view": engine.get_custom_view,
            "project": engine.get_project,
            "site": engine.get_site,
            "flow": engine.get_flow,
            "flow-run": engine.get_flow_run,
            "webhook": engine.get_webhook,
            "data-alert": engine.get_data_alert,
            "task": engine.get_task,
            "schedule": engine.get_schedule,
        }
        handler = handlers.get(args.get_type)
        if handler:
            result = handler(args.id)
            output_response(True, result)
        else:
            output_response(False, error=f"Unknown get type: {args.get_type}")


def handle_refresh(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle refresh command."""
    result = engine.run_extract_refresh(args.task_id)
    output_response(True, result)


def handle_permissions(args: argparse.Namespace, engine: TableauEngine, resource_type: str) -> None:
    """Handle permissions commands for any resource type."""
    get_perm = {
        "workbook": engine.get_workbook_permissions,
        "datasource": engine.get_datasource_permissions,
        "project": engine.get_project_permissions,
        "flow": engine.get_flow_permissions,
    }
    add_perm = {
        "workbook": engine.add_workbook_permission,
        "datasource": engine.add_datasource_permission,
        "project": engine.add_project_permission,
    }
    del_perm = {
        "workbook": engine.delete_workbook_permission,
        "datasource": engine.delete_datasource_permission,
        "project": engine.delete_project_permission,
    }

    if args.perm_command == "get":
        result = get_perm[resource_type](args.resource_id)
        output_response(True, result)
    elif args.perm_command in ("add", "delete"):
        if not args.user or not args.capability or not args.mode:
            output_response(False, error="Missing: --user, --capability, --mode")
        if args.perm_command == "add":
            result = add_perm[resource_type](args.resource_id, args.user, args.capability, args.mode)
        else:
            result = del_perm[resource_type](args.resource_id, args.user, args.capability, args.mode)
        output_response(True, result)


def handle_user(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle user management commands."""
    if args.user_command == "add":
        result = engine.add_user(args.username, args.role or "Viewer")
    elif args.user_command == "remove":
        result = engine.remove_user(args.user_id)
    elif args.user_command == "update":
        result = engine.update_user(
            args.user_id,
            full_name=args.full_name,
            email=args.email,
            site_role=args.role
        )
    else:
        output_response(False, error=f"Unknown user command: {args.user_command}")
        return
    output_response(True, result)


def handle_group(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle group management commands."""
    if args.group_command == "users":
        result = engine.get_group_users(args.group_id)
    elif args.group_command == "add-user":
        result = engine.add_user_to_group(args.group_id, args.user)
    elif args.group_command == "remove-user":
        result = engine.remove_user_from_group(args.group_id, args.user)
    elif args.group_command == "create":
        result = engine.create_group(args.name, minimum_site_role=args.min_role)
    elif args.group_command == "update":
        result = engine.update_group(args.group_id, name=args.name, minimum_site_role=args.min_role)
    elif args.group_command == "delete":
        result = engine.delete_group(args.group_id)
    else:
        output_response(False, error=f"Unknown group command: {args.group_command}")
        return
    output_response(True, result)


def handle_project(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle project management commands."""
    if args.project_command == "create":
        result = engine.create_project(
            args.name,
            description=args.description,
            parent_project_id=args.parent,
            content_permissions=args.permissions or "ManagedByOwner"
        )
    elif args.project_command == "update":
        result = engine.update_project(
            args.project_id,
            name=args.name,
            description=args.description,
            parent_project_id=args.parent,
            content_permissions=args.permissions
        )
    elif args.project_command == "delete":
        result = engine.delete_project(args.project_id)
    else:
        output_response(False, error=f"Unknown project command: {args.project_command}")
        return
    output_response(True, result)


def handle_workbook(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle workbook management commands."""
    cmd = args.workbook_command
    wid = args.workbook_id

    if cmd == "delete":
        result = engine.delete_workbook(wid)
    elif cmd == "views":
        result = engine.list_workbook_views(wid)
    elif cmd == "update":
        result = engine.update_workbook(wid, name=args.name, project_id=args.project,
                                        owner_id=args.owner, show_tabs=args.show_tabs)
    elif cmd == "refresh":
        result = engine.refresh_workbook(wid)
    elif cmd == "revisions":
        result = engine.get_workbook_revisions(wid)
    elif cmd == "download":
        fp = args.output or f"{wid}.twbx"
        result = engine.download_workbook(wid, fp, include_extract=not args.no_extract)
    elif cmd == "download-pdf":
        fp = args.output or f"{wid}.pdf"
        result = engine.download_workbook_pdf(wid, fp, args.page_type or "letter", args.orientation or "portrait")
    elif cmd == "download-pptx":
        fp = args.output or f"{wid}.pptx"
        result = engine.download_workbook_powerpoint(wid, fp)
    elif cmd == "add-tags":
        result = engine.add_tags_to_workbook(wid, args.tags.split(","))
    elif cmd == "delete-tag":
        result = engine.delete_tag_from_workbook(wid, args.tag)
    else:
        output_response(False, error=f"Unknown workbook command: {cmd}")
        return
    output_response(True, result)


def handle_view(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle view management commands."""
    cmd = args.view_command
    vid = args.view_id

    if cmd == "delete":
        result = engine.delete_view(vid)
    elif cmd == "download-image":
        fp = args.output or f"{vid}.png"
        result = engine.download_view_image(vid, fp, resolution=args.resolution, max_age=args.max_age)
    elif cmd == "download-pdf":
        fp = args.output or f"{vid}.pdf"
        result = engine.download_view_pdf(vid, fp, args.page_type or "letter", args.orientation or "portrait")
    elif cmd == "download-data":
        fp = args.output or f"{vid}.csv"
        result = engine.download_view_data(vid, fp, max_age=args.max_age)
    elif cmd == "download-excel":
        fp = args.output or f"{vid}.xlsx"
        result = engine.download_view_crosstab_excel(vid, fp, max_age=args.max_age)
    elif cmd == "add-tags":
        result = engine.add_tags_to_view(vid, args.tags.split(","))
    elif cmd == "delete-tag":
        result = engine.delete_tag_from_view(vid, args.tag)
    elif cmd == "by-path":
        result = engine.get_view_by_path(args.workbook_name, args.view_name)
    else:
        output_response(False, error=f"Unknown view command: {cmd}")
        return
    output_response(True, result)


def handle_datasource(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle datasource management commands."""
    cmd = args.datasource_command
    did = args.datasource_id

    if cmd == "delete":
        result = engine.delete_datasource(did)
    elif cmd == "update":
        result = engine.update_datasource(did, name=args.name, project_id=args.project,
                                          owner_id=args.owner, is_certified=args.certified)
    elif cmd == "refresh":
        result = engine.refresh_datasource(did)
    elif cmd == "revisions":
        result = engine.get_datasource_revisions(did)
    elif cmd == "download":
        fp = args.output or f"{did}.tdsx"
        result = engine.download_datasource(did, fp, include_extract=not args.no_extract)
    elif cmd == "add-tags":
        result = engine.add_tags_to_datasource(did, args.tags.split(","))
    elif cmd == "delete-tag":
        result = engine.delete_tag_from_datasource(did, args.tag)
    else:
        output_response(False, error=f"Unknown datasource command: {cmd}")
        return
    output_response(True, result)


def handle_flow(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle flow management commands."""
    cmd = args.flow_command
    fid = args.flow_id

    if cmd == "delete":
        result = engine.delete_flow(fid)
    elif cmd == "run":
        result = engine.run_flow(fid)
    elif cmd == "update":
        result = engine.update_flow(fid, name=args.name, project_id=args.project, owner_id=args.owner)
    elif cmd == "add-tags":
        result = engine.add_tags_to_flow(fid, args.tags.split(","))
    elif cmd == "delete-tag":
        result = engine.delete_tag_from_flow(fid, args.tag)
    elif cmd == "cancel-run":
        result = engine.cancel_flow_run(args.run_id)
    else:
        output_response(False, error=f"Unknown flow command: {cmd}")
        return
    output_response(True, result)


def handle_webhook(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle webhook management commands."""
    cmd = args.webhook_command

    if cmd == "create":
        result = engine.create_webhook(args.name, args.event, args.url)
    elif cmd == "delete":
        result = engine.delete_webhook(args.webhook_id)
    elif cmd == "test":
        result = engine.test_webhook(args.webhook_id)
    else:
        output_response(False, error=f"Unknown webhook command: {cmd}")
        return
    output_response(True, result)


def handle_data_alert(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle data alert management commands."""
    cmd = args.alert_command

    if cmd == "delete":
        result = engine.delete_data_alert(args.alert_id)
    elif cmd == "add-user":
        result = engine.add_user_to_data_alert(args.alert_id, args.user)
    elif cmd == "remove-user":
        result = engine.remove_user_from_data_alert(args.alert_id, args.user)
    else:
        output_response(False, error=f"Unknown data-alert command: {cmd}")
        return
    output_response(True, result)


def handle_site(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle site management commands."""
    cmd = args.site_command

    if cmd == "create":
        result = engine.create_site(args.name, args.content_url, admin_mode=args.admin_mode or "ContentAndUsers")
    elif cmd == "update":
        result = engine.update_site(args.site_id, name=args.name, content_url=args.content_url,
                                    state=args.state, admin_mode=args.admin_mode)
    elif cmd == "delete":
        result = engine.delete_site(args.site_id)
    else:
        output_response(False, error=f"Unknown site command: {cmd}")
        return
    output_response(True, result)


def handle_schedule(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle schedule management commands."""
    cmd = args.schedule_command

    if cmd == "add-workbook":
        result = engine.add_workbook_to_schedule(args.schedule_id, args.workbook)
    elif cmd == "add-datasource":
        result = engine.add_datasource_to_schedule(args.schedule_id, args.datasource)
    elif cmd == "create":
        result = engine.create_schedule(args.name, args.type, args.frequency, args.start_time,
                                        priority=args.priority or 50)
    elif cmd == "update":
        result = engine.update_schedule(args.schedule_id, name=args.name, state=args.state,
                                        priority=args.priority, frequency=args.frequency)
    elif cmd == "delete":
        result = engine.delete_schedule(args.schedule_id)
    else:
        output_response(False, error=f"Unknown schedule command: {cmd}")
        return
    output_response(True, result)


def handle_task(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle task management commands."""
    cmd = args.task_command

    if cmd == "run":
        result = engine.run_task(args.task_id)
    elif cmd == "delete":
        result = engine.delete_task(args.task_id)
    else:
        output_response(False, error=f"Unknown task command: {cmd}")
        return
    output_response(True, result)


def handle_subscription(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle subscription management commands."""
    cmd = args.sub_command

    if cmd == "create":
        if not all([args.subject, args.user, args.schedule, args.content_type, args.content_id]):
            output_response(False, error="Missing: --subject, --user, --schedule, --content-type, --content-id")
            return
        result = engine.create_subscription(args.subject, args.user, args.schedule,
                                            args.content_type, args.content_id)
    elif cmd == "update":
        result = engine.update_subscription(args.subscription_id, subject=args.subject,
                                            schedule_id=args.schedule, suspended=args.suspended)
    elif cmd == "delete":
        result = engine.delete_subscription(args.subscription_id)
    else:
        output_response(False, error=f"Unknown subscription command: {cmd}")
        return
    output_response(True, result)


def handle_favorites(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle favorites management commands."""
    cmd = args.fav_command

    if cmd == "list":
        result = engine.list_favorites(args.user)
    elif cmd == "add":
        if not all([args.content_type, args.content_id, args.label]):
            output_response(False, error="Missing: --content-type, --content-id, --label")
            return
        result = engine.add_favorite(args.content_type, args.content_id, args.label, args.user)
    elif cmd == "delete":
        if not all([args.content_type, args.content_id]):
            output_response(False, error="Missing: --content-type, --content-id")
            return
        result = engine.delete_favorite(args.content_type, args.content_id, args.user)
    else:
        output_response(False, error=f"Unknown favorites command: {cmd}")
        return
    output_response(True, result)


def handle_custom_view(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle custom view management commands."""
    cmd = args.cv_command
    cvid = args.custom_view_id

    if cmd == "delete":
        result = engine.delete_custom_view(cvid)
    elif cmd == "update":
        result = engine.update_custom_view(cvid, name=args.name, owner_id=args.owner)
    elif cmd == "download-image":
        fp = args.output or f"{cvid}.png"
        result = engine.download_custom_view_image(cvid, fp, resolution=args.resolution, max_age=args.max_age)
    elif cmd == "download-pdf":
        fp = args.output or f"{cvid}.pdf"
        result = engine.download_custom_view_pdf(cvid, fp, args.page_type or "letter", args.orientation or "portrait")
    elif cmd == "download-data":
        fp = args.output or f"{cvid}.csv"
        result = engine.download_custom_view_data(cvid, fp, max_age=args.max_age)
    else:
        output_response(False, error=f"Unknown custom-view command: {cmd}")
        return
    output_response(True, result)


def handle_recommendation(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle recommendation commands."""
    if args.rec_command == "list":
        result = engine.get_recommendations_for_views()
    elif args.rec_command == "hide":
        result = engine.hide_view_recommendation(args.recommendation_id)
    else:
        output_response(False, error=f"Unknown recommendation command: {args.rec_command}")
        return
    output_response(True, result)


def handle_job(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle job management commands."""
    if args.job_command == "cancel":
        result = engine.cancel_job(args.job_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown job command: {args.job_command}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tableau REST API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Auth
    auth_p = subparsers.add_parser("auth", help="Authentication")
    auth_p.add_argument("auth_command", choices=["login", "logout", "status"])

    # List
    list_p = subparsers.add_parser("list", help="List resources")
    list_p.add_argument("list_type", choices=[
        "sites", "projects", "workbooks", "views", "custom-views", "refresh-tasks", "tasks",
        "users", "groups", "datasources", "jobs", "schedules", "subscriptions",
        "flows", "flow-runs", "webhooks", "data-alerts"
    ])

    # Get
    get_p = subparsers.add_parser("get", help="Get resource details")
    get_p.add_argument("get_type", choices=[
        "workbook", "user", "datasource", "job", "view", "custom-view", "project", "site",
        "flow", "flow-run", "webhook", "data-alert", "task", "schedule",
        "server-info", "view-recommendations"
    ])
    get_p.add_argument("id", nargs="?", help="Resource ID")

    # Refresh
    refresh_p = subparsers.add_parser("refresh", help="Trigger extract refresh")
    refresh_p.add_argument("task_id", help="Task ID")

    # Permissions (workbook, datasource, project, flow)
    for res in ["workbook", "datasource", "project", "flow"]:
        perm_p = subparsers.add_parser(f"{res}-permissions", help=f"Manage {res} permissions")
        perm_p.add_argument("perm_command", choices=["get", "add", "delete"])
        perm_p.add_argument("resource_id", help=f"{res.capitalize()} ID")
        perm_p.add_argument("--user", help="User ID")
        perm_p.add_argument("--capability", help="Capability name")
        perm_p.add_argument("--mode", choices=["Allow", "Deny"])

    # User
    user_p = subparsers.add_parser("user", help="User management")
    user_p.add_argument("user_command", choices=["add", "remove", "update"])
    user_p.add_argument("--username", help="Username for add")
    user_p.add_argument("--user-id", dest="user_id", help="User ID")
    user_p.add_argument("--role", help="Site role")
    user_p.add_argument("--full-name", dest="full_name", help="Full name")
    user_p.add_argument("--email", help="Email")

    # Group
    group_p = subparsers.add_parser("group", help="Group management")
    group_p.add_argument("group_command", choices=["users", "add-user", "remove-user", "create", "update", "delete"])
    group_p.add_argument("group_id", nargs="?", help="Group ID")
    group_p.add_argument("--user", help="User ID")
    group_p.add_argument("--name", help="Group name")
    group_p.add_argument("--min-role", dest="min_role", help="Minimum site role")

    # Project
    project_p = subparsers.add_parser("project", help="Project management")
    project_p.add_argument("project_command", choices=["create", "update", "delete"])
    project_p.add_argument("project_id", nargs="?", help="Project ID")
    project_p.add_argument("--name", help="Project name")
    project_p.add_argument("--description", help="Description")
    project_p.add_argument("--parent", help="Parent project ID")
    project_p.add_argument("--permissions", help="Content permissions mode")

    # Workbook
    wb_p = subparsers.add_parser("workbook", help="Workbook management")
    wb_p.add_argument("workbook_command", choices=[
        "delete", "views", "update", "refresh", "revisions", "download",
        "download-pdf", "download-pptx", "add-tags", "delete-tag"
    ])
    wb_p.add_argument("workbook_id", help="Workbook ID")
    wb_p.add_argument("--name", help="New name")
    wb_p.add_argument("--project", help="Project ID")
    wb_p.add_argument("--owner", help="Owner ID")
    wb_p.add_argument("--show-tabs", dest="show_tabs", type=lambda x: x.lower() == 'true')
    wb_p.add_argument("--output", "-o", help="Output file path")
    wb_p.add_argument("--no-extract", dest="no_extract", action="store_true")
    wb_p.add_argument("--page-type", dest="page_type")
    wb_p.add_argument("--orientation")
    wb_p.add_argument("--tags", help="Comma-separated tags")
    wb_p.add_argument("--tag", help="Tag name")

    # View
    view_p = subparsers.add_parser("view", help="View management")
    view_p.add_argument("view_command", choices=[
        "delete", "download-image", "download-pdf", "download-data",
        "download-excel", "add-tags", "delete-tag", "by-path"
    ])
    view_p.add_argument("view_id", nargs="?", help="View ID")
    view_p.add_argument("--output", "-o")
    view_p.add_argument("--resolution")
    view_p.add_argument("--max-age", dest="max_age", type=int)
    view_p.add_argument("--page-type", dest="page_type")
    view_p.add_argument("--orientation")
    view_p.add_argument("--tags")
    view_p.add_argument("--tag")
    view_p.add_argument("--workbook-name", dest="workbook_name")
    view_p.add_argument("--view-name", dest="view_name")

    # Custom View
    cv_p = subparsers.add_parser("custom-view", help="Custom view management")
    cv_p.add_argument("cv_command", choices=["delete", "update", "download-image", "download-pdf", "download-data"])
    cv_p.add_argument("custom_view_id", help="Custom view ID")
    cv_p.add_argument("--name")
    cv_p.add_argument("--owner")
    cv_p.add_argument("--output", "-o")
    cv_p.add_argument("--resolution")
    cv_p.add_argument("--max-age", dest="max_age", type=int)
    cv_p.add_argument("--page-type", dest="page_type")
    cv_p.add_argument("--orientation")

    # Datasource
    ds_p = subparsers.add_parser("datasource", help="Datasource management")
    ds_p.add_argument("datasource_command", choices=[
        "delete", "update", "refresh", "revisions", "download", "add-tags", "delete-tag"
    ])
    ds_p.add_argument("datasource_id", help="Datasource ID")
    ds_p.add_argument("--name")
    ds_p.add_argument("--project")
    ds_p.add_argument("--owner")
    ds_p.add_argument("--certified", type=lambda x: x.lower() == 'true')
    ds_p.add_argument("--output", "-o")
    ds_p.add_argument("--no-extract", dest="no_extract", action="store_true")
    ds_p.add_argument("--tags")
    ds_p.add_argument("--tag")

    # Flow
    flow_p = subparsers.add_parser("flow", help="Flow management")
    flow_p.add_argument("flow_command", choices=["delete", "run", "update", "add-tags", "delete-tag", "cancel-run"])
    flow_p.add_argument("flow_id", nargs="?", help="Flow ID")
    flow_p.add_argument("--name")
    flow_p.add_argument("--project")
    flow_p.add_argument("--owner")
    flow_p.add_argument("--tags")
    flow_p.add_argument("--tag")
    flow_p.add_argument("--run-id", dest="run_id", help="Flow run ID for cancel-run")

    # Webhook
    wh_p = subparsers.add_parser("webhook", help="Webhook management")
    wh_p.add_argument("webhook_command", choices=["create", "delete", "test"])
    wh_p.add_argument("webhook_id", nargs="?", help="Webhook ID")
    wh_p.add_argument("--name")
    wh_p.add_argument("--event", help="Event type")
    wh_p.add_argument("--url", help="Destination URL")

    # Data Alert
    da_p = subparsers.add_parser("data-alert", help="Data alert management")
    da_p.add_argument("alert_command", choices=["delete", "add-user", "remove-user"])
    da_p.add_argument("alert_id", help="Data alert ID")
    da_p.add_argument("--user", help="User ID")

    # Site
    site_p = subparsers.add_parser("site", help="Site management (Server Admin)")
    site_p.add_argument("site_command", choices=["create", "update", "delete"])
    site_p.add_argument("site_id", nargs="?", help="Site ID")
    site_p.add_argument("--name")
    site_p.add_argument("--content-url", dest="content_url")
    site_p.add_argument("--admin-mode", dest="admin_mode")
    site_p.add_argument("--state")

    # Schedule
    sched_p = subparsers.add_parser("schedule", help="Schedule management")
    sched_p.add_argument("schedule_command", choices=[
        "add-workbook", "add-datasource", "create", "update", "delete"
    ])
    sched_p.add_argument("schedule_id", nargs="?", help="Schedule ID")
    sched_p.add_argument("--workbook")
    sched_p.add_argument("--datasource")
    sched_p.add_argument("--name")
    sched_p.add_argument("--type", help="Extract or Subscription")
    sched_p.add_argument("--frequency", help="Hourly, Daily, Weekly, Monthly")
    sched_p.add_argument("--start-time", dest="start_time", help="HH:MM:SS")
    sched_p.add_argument("--priority", type=int)
    sched_p.add_argument("--state")

    # Task
    task_p = subparsers.add_parser("task", help="Task management")
    task_p.add_argument("task_command", choices=["run", "delete"])
    task_p.add_argument("task_id", help="Task ID")

    # Subscription
    sub_p = subparsers.add_parser("subscription", help="Subscription management")
    sub_p.add_argument("sub_command", choices=["create", "update", "delete"])
    sub_p.add_argument("--subscription-id", dest="subscription_id")
    sub_p.add_argument("--subject")
    sub_p.add_argument("--user")
    sub_p.add_argument("--schedule")
    sub_p.add_argument("--content-type", dest="content_type", choices=["View", "Workbook"])
    sub_p.add_argument("--content-id", dest="content_id")
    sub_p.add_argument("--suspended", type=lambda x: x.lower() == 'true')

    # Favorites
    fav_p = subparsers.add_parser("favorites", help="Favorites management")
    fav_p.add_argument("fav_command", choices=["list", "add", "delete"])
    fav_p.add_argument("--user")
    fav_p.add_argument("--content-type", dest="content_type",
                       choices=["workbook", "view", "datasource", "project"])
    fav_p.add_argument("--content-id", dest="content_id")
    fav_p.add_argument("--label")

    # Recommendation
    rec_p = subparsers.add_parser("recommendation", help="View recommendations")
    rec_p.add_argument("rec_command", choices=["list", "hide"])
    rec_p.add_argument("recommendation_id", nargs="?")

    # Job
    job_p = subparsers.add_parser("job", help="Job management")
    job_p.add_argument("job_command", choices=["cancel"])
    job_p.add_argument("job_id", help="Job ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        output_response(False, error="No command provided")

    engine = TableauEngine()

    try:
        handlers = {
            "auth": lambda: handle_auth(args, engine),
            "list": lambda: handle_list(args, engine),
            "get": lambda: handle_get(args, engine),
            "refresh": lambda: handle_refresh(args, engine),
            "workbook-permissions": lambda: handle_permissions(args, engine, "workbook"),
            "datasource-permissions": lambda: handle_permissions(args, engine, "datasource"),
            "project-permissions": lambda: handle_permissions(args, engine, "project"),
            "flow-permissions": lambda: handle_permissions(args, engine, "flow"),
            "user": lambda: handle_user(args, engine),
            "group": lambda: handle_group(args, engine),
            "project": lambda: handle_project(args, engine),
            "workbook": lambda: handle_workbook(args, engine),
            "view": lambda: handle_view(args, engine),
            "custom-view": lambda: handle_custom_view(args, engine),
            "datasource": lambda: handle_datasource(args, engine),
            "flow": lambda: handle_flow(args, engine),
            "webhook": lambda: handle_webhook(args, engine),
            "data-alert": lambda: handle_data_alert(args, engine),
            "site": lambda: handle_site(args, engine),
            "schedule": lambda: handle_schedule(args, engine),
            "task": lambda: handle_task(args, engine),
            "subscription": lambda: handle_subscription(args, engine),
            "favorites": lambda: handle_favorites(args, engine),
            "recommendation": lambda: handle_recommendation(args, engine),
            "job": lambda: handle_job(args, engine),
        }

        handler = handlers.get(args.command)
        if handler:
            handler()
        else:
            output_response(False, error=f"Unknown command: {args.command}")
    except Exception as e:
        output_response(False, error=str(e))


if __name__ == "__main__":
    main()
