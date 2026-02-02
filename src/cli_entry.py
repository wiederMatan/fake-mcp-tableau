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
    if args.list_type == "sites":
        result = engine.list_sites()
        output_response(True, result)
    elif args.list_type == "projects":
        result = engine.list_projects()
        output_response(True, result)
    elif args.list_type == "workbooks":
        result = engine.list_workbooks()
        output_response(True, result)
    elif args.list_type == "refresh-tasks":
        result = engine.list_extract_tasks()
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown list type: {args.list_type}")


def handle_get(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle get commands."""
    if args.get_type == "workbook":
        result = engine.get_workbook(args.id)
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown get type: {args.get_type}")


def handle_refresh(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle refresh command."""
    result = engine.run_extract_refresh(args.task_id)
    output_response(True, result)


def handle_permissions(args: argparse.Namespace, engine: TableauEngine) -> None:
    """Handle permissions commands."""
    if args.perm_command == "get":
        result = engine.get_workbook_permissions(args.workbook_id)
        output_response(True, result)
    elif args.perm_command == "add":
        if not args.user or not args.capability or not args.mode:
            output_response(
                False,
                error="Missing required arguments: --user, --capability, --mode"
            )
        result = engine.add_workbook_permission(
            args.workbook_id,
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
            args.workbook_id,
            args.user,
            args.capability,
            args.mode
        )
        output_response(True, result)
    else:
        output_response(False, error=f"Unknown permissions command: {args.perm_command}")


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
        choices=["sites", "projects", "workbooks", "refresh-tasks"],
        help="Resource type to list"
    )

    # Get commands
    get_parser = subparsers.add_parser("get", help="Get resource details")
    get_parser.add_argument(
        "get_type",
        choices=["workbook"],
        help="Resource type to get"
    )
    get_parser.add_argument("id", help="Resource ID")

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Trigger extract refresh")
    refresh_parser.add_argument("task_id", help="Extract refresh task ID")

    # Permissions commands
    perm_parser = subparsers.add_parser("permissions", help="Manage permissions")
    perm_parser.add_argument(
        "perm_command",
        choices=["get", "add", "delete"],
        help="Permission action"
    )
    perm_parser.add_argument("workbook_id", help="Workbook ID")
    perm_parser.add_argument("--user", help="User ID for add/delete")
    perm_parser.add_argument("--capability", help="Capability name (e.g., Read, Write)")
    perm_parser.add_argument("--mode", choices=["Allow", "Deny"], help="Permission mode")

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
        elif args.command == "permissions":
            handle_permissions(args, engine)
        else:
            output_response(False, error=f"Unknown command: {args.command}")
    except Exception as e:
        output_response(False, error=str(e))


if __name__ == "__main__":
    main()
