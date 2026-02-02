# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI toolkit that bridges Gemini CLI and Tableau REST API, mimicking MCP (Model Context Protocol) capabilities through local execution. The tool provides authentication management, resource discovery, and operations on Tableau Server/Cloud.

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Tableau credentials
```

### Running the CLI
```bash
# Run commands using module syntax
python -m src.cli_entry <command> [options]

# Examples
python -m src.cli_entry auth login
python -m src.cli_entry list workbooks
python -m src.cli_entry auth status
```

### Available Commands

**Listing:**
- `list sites|projects|workbooks|datasources|users|groups|jobs|schedules|subscriptions|refresh-tasks`

**Getting details:**
- `get workbook|user|datasource|job|view <id>`

**User management:**
- `user add --username <name> --role <role>`
- `user remove --user-id <id>`

**Group management:**
- `group users|add-user|remove-user <group_id> [--user <user_id>]`

**Workbook/Datasource:**
- `workbook views|delete <workbook_id>`
- `datasource delete <datasource_id>`

**Permissions:**
- `workbook-permissions get|add|delete <id> [--user <id> --capability <name> --mode Allow|Deny]`
- `datasource-permissions get|add|delete <id> [--user <id> --capability <name> --mode Allow|Deny]`

**Jobs & Schedules:**
- `refresh <task_id>`
- `job cancel <job_id>`
- `schedule add-workbook|add-datasource <schedule_id> [--workbook|--datasource <id>]`

**Subscriptions & Favorites:**
- `subscription create|delete [options]`
- `favorites list|add|delete [options]`

### Testing
```bash
# Verify authentication
python -m src.cli_entry auth login
python -m src.cli_entry auth status

# List resources
python -m src.cli_entry list projects
python -m src.cli_entry list workbooks
python -m src.cli_entry list users
```

## Architecture

```
src/
├── __init__.py       # Package marker
├── session.py        # Token storage and validation (240-min timeout)
├── engine.py         # TableauEngine class - core API wrapper
└── cli_entry.py      # argparse-based CLI entry point
```

### Key Components

- **session.py**: Manages `.session.json` for persisting auth tokens between CLI calls. Tokens auto-expire after 240 minutes per Tableau's session policy.

- **engine.py**: `TableauEngine` class wrapping Tableau REST API v3.22. Contains methods for:
  - Authentication: `sign_in`, `sign_out`, `ensure_authenticated`, `get_auth_status`
  - Discovery: `list_sites`, `list_projects`, `list_workbooks`, `list_datasources`, `list_users`, `list_groups`, `list_jobs`, `list_schedules`, `list_subscriptions`, `list_extract_tasks`
  - Get details: `get_workbook`, `get_user`, `get_datasource`, `get_job`, `get_view`
  - User/Group: `add_user`, `remove_user`, `get_group_users`, `add_user_to_group`, `remove_user_from_group`
  - Operations: `delete_workbook`, `delete_datasource`, `list_workbook_views`, `run_extract_refresh`, `cancel_job`
  - Permissions: `get_workbook_permissions`, `add_workbook_permission`, `delete_workbook_permission`, `get_datasource_permissions`, `add_datasource_permission`, `delete_datasource_permission`
  - Schedules: `add_workbook_to_schedule`, `add_datasource_to_schedule`
  - Subscriptions: `create_subscription`, `delete_subscription`
  - Favorites: `list_favorites`, `add_favorite`, `delete_favorite`

- **cli_entry.py**: CLI interface outputting JSON responses for Gemini parsing. All responses follow `{success, data, error}` format.

### Configuration

Environment variables in `.env`:
- `TABLEAU_SERVER_URL` - Server/Cloud URL
- `TABLEAU_SITE_ID` - Site content URL
- `TABLEAU_PAT_NAME` - Personal Access Token name
- `TABLEAU_PAT_SECRET` - Personal Access Token secret
