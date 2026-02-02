#!/usr/bin/env python3
"""CLI entry point for Tableau API operations."""

import argparse
import json
import sys
from typing import Any

from .engine import TableauEngine


def output_response(success: bool, data: Any = None, error: str | None = None) -> None:
    """Print JSON response and exit.

    Args:
        success: Whether the operation succeeded
        data: Response data
        error: Error message if failed
    """
    response = {
        "success": success,
        "data": data,
        "error": error
    }
    print(json.dumps(response, indent=2))
    sys.exit(0 if success else 1)


def handle_auth(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle authentication commands."""
    if args.auth_command == "login":
        result = engine.sign_in()
        output_response(True, result)
    elif args.auth_command == "logout":
        result = engine.sign_out()
        output_response(True, result)
    elif args.auth_command == "status":
        result = engine.get_auth_status()
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown auth command: {args.auth_command}")


def handle_list(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle list commands."""
    list_handlers = {
        "sites": engine.list_sites,
        "projects": engine.list_projects,
        "workbooks": engine.list_workbooks,
        "refresh-tasks": engine.list_extract_tasks,
        "users": engine.list_users,
        "groups": engine.list_groups,
        "datasources": engine.list_datasources,
        "jobs": engine.list_jobs,
        "schedules": engine.list_schedules,
        "subscriptions": engine.list_subscriptions,
    }

    handler = list_handlers.get(args.list_type)
    if handler:
        result = handler()
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown list type: {args.list_type}")


def handle_get(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle get commands."""
    if args.get_type == "workbook":
        result = engine.get_workbook(args.id)
        output_response(True, result)
    elif args.get_type == "user":
        result = engine.get_user(args.id)
        output_response(True, result)
    elif args.get_type == "datasource":
        result = engine.get_datasource(args.id)
        output_response(True, result)
    elif args.get_type == "job":
        result = engine.get_job(args.id)
        output_response(True, result)
    elif args.get_type == "view":
        result = engine.get_view(args.id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown get type: {args.get_type}")


def handle_refresh(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle refresh command."""
    result = engine.run_extract_refresh(args.task_id)
    output_response(True, result)


def handle_workbook_permissions(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle workbook permissions commands."""
    if args.perm_command == "get":
        result = engine.get_workbook_permissions(args.resource_id)
        output_response(True, result)
    elif args.perm_command == "add":
        if not args.user or not args.capability or not args.mode:
            output_response(
                False,
                error="Missing required arguments: --user, --capability, --mode"
            )
        result = engine.add_workbook_permission(
            args.resource_id,
            args.user,
            args.capability,
            args.mode
        )
        output_response(True, result)
    elif args.perm_command == "delete":
        if not args.user or not args.capability or not args.mode:
            output_response(
                False,
                error="Missing required arguments: --user, --capability, --mode"
            )
        result = engine.delete_workbook_permission(
            args.resource_id,
            args.user,
            args.capability,
            args.mode
        )
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown permissions command: {args.perm_command}")


def handle_datasource_permissions(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle datasource permissions commands."""
    if args.perm_command == "get":
        result = engine.get_datasource_permissions(args.resource_id)
        output_response(True, result)
    elif args.perm_command == "add":
        if not args.user or not args.capability or not args.mode:
            output_response(
                False,
                error="Missing required arguments: --user, --capability, --mode"
            )
        result = engine.add_datasource_permission(
            args.resource_id,
            args.user,
            args.capability,
            args.mode
        )
        output_response(True, result)
    elif args.perm_command == "delete":
        if not args.user or not args.capability or not args.mode:
            output_response(
                False,
                error="Missing required arguments: --user, --capability, --mode"
            )
        result = engine.delete_datasource_permission(
            args.resource_id,
            args.user,
            args.capability,
            args.mode
        )
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown permissions command: {args.perm_command}")


def handle_users(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle user management commands."""
    if args.user_command == "add":
        result = engine.add_user(args.username, args.role or "Viewer")
        output_response(True, result)
    elif args.user_command == "remove":
        result = engine.remove_user(args.user_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown user command: {args.user_command}")


def handle_groups(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle group management commands."""
    if args.group_command == "users":
        result = engine.get_group_users(args.group_id)
        output_response(True, result)
    elif args.group_command == "add-user":
        if not args.user:
            output_response(False, error="Missing required argument: --user")
        result = engine.add_user_to_group(args.group_id, args.user)
        output_response(True, result)
    elif args.group_command == "remove-user":
        if not args.user:
            output_response(False, error="Missing required argument: --user")
        result = engine.remove_user_from_group(args.group_id, args.user)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown group command: {args.group_command}")


def handle_workbook(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle workbook management commands."""
    if args.workbook_command == "delete":
        result = engine.delete_workbook(args.workbook_id)
        output_response(True, result)
    elif args.workbook_command == "views":
        result = engine.list_workbook_views(args.workbook_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown workbook command: {args.workbook_command}")


def handle_datasource(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle datasource management commands."""
    if args.datasource_command == "delete":
        result = engine.delete_datasource(args.datasource_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown datasource command: {args.datasource_command}")


def handle_job(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle job management commands."""
    if args.job_command == "cancel":
        result = engine.cancel_job(args.job_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown job command: {args.job_command}")


def handle_schedule(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle schedule management commands."""
    if args.schedule_command == "add-workbook":
        result = engine.add_workbook_to_schedule(args.schedule_id, args.workbook)
        output_response(True, result)
    elif args.schedule_command == "add-datasource":
        result = engine.add_datasource_to_schedule(args.schedule_id, args.datasource)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown schedule command: {args.schedule_command}")


def handle_subscription(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle subscription management commands."""
    if args.sub_command == "create":
        if not all([args.subject, args.user, args.schedule, args.content_type, args.content_id]):
            output_response(
                False,
                error="Missing required arguments: --subject, --user, --schedule, --content-type, --content-id"
            )
        result = engine.create_subscription(
            args.subject,
            args.user,
            args.schedule,
            args.content_type,
            args.content_id
        )
        output_response(True, result)
    elif args.sub_command == "delete":
        result = engine.delete_subscription(args.subscription_id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown subscription command: {args.sub_command}")


def handle_favorites(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle favorites management commands."""
    if args.fav_command == "list":
        result = engine.list_favorites(args.user)
        output_response(True, result)
    elif args.fav_command == "add":
        if not all([args.content_type, args.content_id, args.label]):
            output_response(
                False,
                error="Missing required arguments: --content-type, --content-id, --label"
            )
        result = engine.add_favorite(args.content_type, args.content_id, args.label, args.user)
        output_response(True, result)
    elif args.fav_command == "delete":
        if not all([args.content_type, args.content_id]):
            output_response(
                False,
                error="Missing required arguments: --content-type, --content-id"
            )
        result = engine.delete_favorite(args.content_type, args.content_id, args.user)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown favorites command: {args.fav_command}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tableau REST API CLI for Gemini integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Auth commands
    auth_parser = subparsers.add_parser("auth", help="Authentication operations")
    auth_parser.add_argument(
        "auth_command",
        choices=["login", "logout", "status"],
        help="Auth action: login, logout, or status"
    )

    # List commands
    list_parser = subparsers.add_parser("list", help="List resources")
    list_parser.add_argument(
        "list_type",
        choices=[
            "sites", "projects", "workbooks", "refresh-tasks",
            "users", "groups", "datasources", "jobs", "schedules", "subscriptions"
        ],
        help="Resource type to list"
    )

    # Get commands
    get_parser = subparsers.add_parser("get", help="Get resource details")
    get_parser.add_argument(
        "get_type",
        choices=["workbook", "user", "datasource", "job", "view"],
        help="Resource type to get"
    )
    get_parser.add_argument("id", help="Resource ID")

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Trigger extract refresh")
    refresh_parser.add_argument("task_id", help="Extract refresh task ID")

    # Workbook permissions commands
    wb_perm_parser = subparsers.add_parser("workbook-permissions", help="Manage workbook permissions")
    wb_perm_parser.add_argument(
        "perm_command",
        choices=["get", "add", "delete"],
        help="Permission action"
    )
    wb_perm_parser.add_argument("resource_id", help="Workbook ID")
    wb_perm_parser.add_argument("--user", help="User ID for add/delete")
    wb_perm_parser.add_argument("--capability", help="Capability name (e.g., Read, Write)")
    wb_perm_parser.add_argument("--mode", choices=["Allow", "Deny"], help="Permission mode")

    # Datasource permissions commands
    ds_perm_parser = subparsers.add_parser("datasource-permissions", help="Manage datasource permissions")
    ds_perm_parser.add_argument(
        "perm_command",
        choices=["get", "add", "delete"],
        help="Permission action"
    )
    ds_perm_parser.add_argument("resource_id", help="Datasource ID")
    ds_perm_parser.add_argument("--user", help="User ID for add/delete")
    ds_perm_parser.add_argument("--capability", help="Capability name")
    ds_perm_parser.add_argument("--mode", choices=["Allow", "Deny"], help="Permission mode")

    # User management commands
    user_parser = subparsers.add_parser("user", help="User management")
    user_parser.add_argument(
        "user_command",
        choices=["add", "remove"],
        help="User action"
    )
    user_parser.add_argument("--username", help="Username for add")
    user_parser.add_argument("--user-id", dest="user_id", help="User ID for remove")
    user_parser.add_argument("--role", help="Site role (Creator, Explorer, Viewer)")

    # Group management commands
    group_parser = subparsers.add_parser("group", help="Group management")
    group_parser.add_argument(
        "group_command",
        choices=["users", "add-user", "remove-user"],
        help="Group action"
    )
    group_parser.add_argument("group_id", help="Group ID")
    group_parser.add_argument("--user", help="User ID")

    # Workbook management commands
    workbook_parser = subparsers.add_parser("workbook", help="Workbook management")
    workbook_parser.add_argument(
        "workbook_command",
        choices=["delete", "views"],
        help="Workbook action"
    )
    workbook_parser.add_argument("workbook_id", help="Workbook ID")

    # Datasource management commands
    datasource_parser = subparsers.add_parser("datasource", help="Datasource management")
    datasource_parser.add_argument(
        "datasource_command",
        choices=["delete"],
        help="Datasource action"
    )
    datasource_parser.add_argument("datasource_id", help="Datasource ID")

    # Job management commands
    job_parser = subparsers.add_parser("job", help="Job management")
    job_parser.add_argument(
        "job_command",
        choices=["cancel"],
        help="Job action"
    )
    job_parser.add_argument("job_id", help="Job ID")

    # Schedule management commands
    schedule_parser = subparsers.add_parser("schedule", help="Schedule management")
    schedule_parser.add_argument(
        "schedule_command",
        choices=["add-workbook", "add-datasource"],
        help="Schedule action"
    )
    schedule_parser.add_argument("schedule_id", help="Schedule ID")
    schedule_parser.add_argument("--workbook", help="Workbook ID")
    schedule_parser.add_argument("--datasource", help="Datasource ID")

    # Subscription management commands
    sub_parser = subparsers.add_parser("subscription", help="Subscription management")
    sub_parser.add_argument(
        "sub_command",
        choices=["create", "delete"],
        help="Subscription action"
    )
    sub_parser.add_argument("--subscription-id", dest="subscription_id", help="Subscription ID for delete")
    sub_parser.add_argument("--subject", help="Email subject for create")
    sub_parser.add_argument("--user", help="User ID to receive subscription")
    sub_parser.add_argument("--schedule", help="Schedule ID")
    sub_parser.add_argument("--content-type", dest="content_type", choices=["View", "Workbook"], help="Content type")
    sub_parser.add_argument("--content-id", dest="content_id", help="Content ID (view or workbook)")

    # Favorites management commands
    fav_parser = subparsers.add_parser("favorites", help="Favorites management")
    fav_parser.add_argument(
        "fav_command",
        choices=["list", "add", "delete"],
        help="Favorites action"
    )
    fav_parser.add_argument("--user", help="User ID (defaults to current user)")
    fav_parser.add_argument("--content-type", dest="content_type",
                           choices=["workbook", "view", "datasource", "project"],
                           help="Content type")
    fav_parser.add_argument("--content-id", dest="content_id", help="Content ID")
    fav_parser.add_argument("--label", help="Label for the favorite")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        output_response(False, error="No command provided")

    engine = TableauEngine()

    try:
        if args.command == "auth":
            handle_auth(args, engine)
        elif args.command == "list":
            handle_list(args, engine)
        elif args.command == "get":
            handle_get(args, engine)
        elif args.command == "refresh":
            handle_refresh(args, engine)
        elif args.command == "workbook-permissions":
            handle_workbook_permissions(args, engine)
        elif args.command == "datasource-permissions":
            handle_datasource_permissions(args, engine)
        elif args.command == "user":
            handle_users(args, engine)
        elif args.command == "group":
            handle_groups(args, engine)
        elif args.command == "workbook":
            handle_workbook(args, engine)
        elif args.command == "datasource":
            handle_datasource(args, engine)
        elif args.command == "job":
            handle_job(args, engine)
        elif args.command == "schedule":
            handle_schedule(args, engine)
        elif args.command == "subscription":
            handle_subscription(args, engine)
        elif args.command == "favorites":
            handle_favorites(args, engine)
        else:
            output_response(False, error=f"Unknown command: {args.command}")
    except Exception as e:
        output_response(False, error=str(e))


if __name__ == "__main__":
    main()
