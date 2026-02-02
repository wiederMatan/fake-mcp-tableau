# Fake MCP Tableau

A Python CLI toolkit that acts as a bridge between Gemini CLI and Tableau REST API, mimicking MCP (Model Context Protocol) capabilities through local execution.

## Features

- **Authentication Management**: Sign in with Personal Access Tokens, automatic session persistence
- **Resource Discovery**: List and get details for sites, projects, workbooks, views, data sources, users, groups, jobs, schedules, subscriptions, flows, webhooks, data alerts, custom views
- **User & Group Management**: Add/remove users, create/update/delete groups, manage group membership
- **Project Management**: Create/update/delete projects, manage project permissions
- **Workbook Operations**: View details, list views, update, refresh, delete, download (twbx/pdf/pptx), manage permissions and tags
- **View Operations**: Delete views, download images/pdf/data/crosstab, manage tags
- **Data Source Operations**: Update, refresh, delete, download, manage permissions and tags
- **Flow Operations**: Run flows, view run history, update, delete, manage permissions and tags
- **Webhook Management**: Create, test, and delete webhooks for event notifications
- **Data Alerts**: List alerts, add/remove users from alerts
- **Extract Refresh**: List tasks, trigger refreshes, run/delete tasks, monitor jobs
- **Schedule Management**: Create/update/delete schedules, add workbooks/datasources to schedules
- **Site Management**: Create/update/delete sites (Tableau Server only)
- **Subscriptions & Favorites**: Create/update/delete subscriptions, manage favorites
- **Custom Views**: List, get, update, delete, download images
- **Gemini-Ready Output**: All responses are JSON formatted for easy parsing

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/fake-mcp-tableau.git
   cd fake-mcp-tableau
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your Tableau credentials:
   ```
   TABLEAU_SERVER_URL=https://your-tableau-server.com
   TABLEAU_SITE_ID=your-site-content-url
   TABLEAU_PAT_NAME=your-pat-name
   TABLEAU_PAT_SECRET=your-pat-secret
   ```

   To create a Personal Access Token in Tableau:
   - Go to Account Settings > Personal Access Tokens
   - Create a new token and copy the name and secret

## Usage

All commands follow the pattern:
```bash
python -m src.cli_entry <command> [options]
```

### Authentication

```bash
python -m src.cli_entry auth login      # Sign in
python -m src.cli_entry auth status     # Check session
python -m src.cli_entry auth logout     # Sign out
```

### Listing Resources

```bash
python -m src.cli_entry list sites          # Tableau Server only
python -m src.cli_entry list projects
python -m src.cli_entry list workbooks
python -m src.cli_entry list views
python -m src.cli_entry list datasources
python -m src.cli_entry list users
python -m src.cli_entry list groups
python -m src.cli_entry list jobs
python -m src.cli_entry list schedules      # Tableau Server only
python -m src.cli_entry list subscriptions
python -m src.cli_entry list refresh-tasks
python -m src.cli_entry list flows
python -m src.cli_entry list webhooks
python -m src.cli_entry list data-alerts
python -m src.cli_entry list custom-views
```

### Getting Resource Details

```bash
python -m src.cli_entry get workbook <id>
python -m src.cli_entry get view <id>
python -m src.cli_entry get user <id>
python -m src.cli_entry get datasource <id>
python -m src.cli_entry get project <id>
python -m src.cli_entry get job <id>
python -m src.cli_entry get flow <id>
python -m src.cli_entry get webhook <id>
python -m src.cli_entry get schedule <id>
python -m src.cli_entry get task <id>
python -m src.cli_entry get data-alert <id>
python -m src.cli_entry get custom-view <id>
python -m src.cli_entry get site
python -m src.cli_entry get server-info
```

### User Management

```bash
python -m src.cli_entry user add --username <name> --role Viewer|Explorer|Creator
python -m src.cli_entry user remove --user-id <id>
```

### Group Management

```bash
python -m src.cli_entry group users <group_id>
python -m src.cli_entry group add-user <group_id> --user <user_id>
python -m src.cli_entry group remove-user <group_id> --user <user_id>
python -m src.cli_entry group create --name <group_name>
python -m src.cli_entry group update <group_id> --name <new_name>
python -m src.cli_entry group delete <group_id>
```

### Project Management

```bash
python -m src.cli_entry project create --name <name> [--description <desc>] [--parent <parent_id>]
python -m src.cli_entry project update <project_id> [--name <name>] [--description <desc>]
python -m src.cli_entry project delete <project_id>
python -m src.cli_entry project-permissions get <project_id>
python -m src.cli_entry project-permissions add <project_id> --user <user_id> --capability <name> --mode Allow|Deny
python -m src.cli_entry project-permissions delete <project_id> --user <user_id> --capability <name> --mode Allow|Deny
```

### Workbook Operations

```bash
python -m src.cli_entry workbook views <workbook_id>
python -m src.cli_entry workbook delete <workbook_id>
python -m src.cli_entry workbook update <workbook_id> [--name <name>] [--project <project_id>] [--show-tabs <true|false>]
python -m src.cli_entry workbook refresh <workbook_id>
python -m src.cli_entry workbook revisions <workbook_id>
python -m src.cli_entry workbook download <workbook_id> --filepath <path.twbx>
python -m src.cli_entry workbook download-pdf <workbook_id> --filepath <path.pdf>
python -m src.cli_entry workbook download-pptx <workbook_id> --filepath <path.pptx>
python -m src.cli_entry workbook add-tag <workbook_id> --tag <tag_name>
python -m src.cli_entry workbook delete-tag <workbook_id> --tag <tag_name>
python -m src.cli_entry workbook-permissions get <workbook_id>
python -m src.cli_entry workbook-permissions add <workbook_id> --user <user_id> --capability Read --mode Allow
python -m src.cli_entry workbook-permissions delete <workbook_id> --user <user_id> --capability Read --mode Allow
```

### View Operations

```bash
python -m src.cli_entry view delete <view_id>
python -m src.cli_entry view download-image <view_id> --filepath <path.png>
python -m src.cli_entry view download-pdf <view_id> --filepath <path.pdf>
python -m src.cli_entry view download-data <view_id> --filepath <path.csv>
python -m src.cli_entry view download-crosstab <view_id> --filepath <path.xlsx>
python -m src.cli_entry view add-tag <view_id> --tag <tag_name>
python -m src.cli_entry view delete-tag <view_id> --tag <tag_name>
python -m src.cli_entry view get-by-path --name <view_name>
python -m src.cli_entry view recommendations <view_id>
```

### Custom View Operations

```bash
python -m src.cli_entry custom-view update <custom_view_id> [--name <name>] [--owner <user_id>]
python -m src.cli_entry custom-view delete <custom_view_id>
python -m src.cli_entry custom-view download-image <custom_view_id> --filepath <path.png>
```

### Data Source Operations

```bash
python -m src.cli_entry datasource delete <datasource_id>
python -m src.cli_entry datasource update <datasource_id> [--name <name>] [--project <project_id>] [--certified <true|false>]
python -m src.cli_entry datasource refresh <datasource_id>
python -m src.cli_entry datasource download <datasource_id> --filepath <path.tdsx>
python -m src.cli_entry datasource revisions <datasource_id>
python -m src.cli_entry datasource add-tag <datasource_id> --tag <tag_name>
python -m src.cli_entry datasource delete-tag <datasource_id> --tag <tag_name>
python -m src.cli_entry datasource-permissions get <datasource_id>
python -m src.cli_entry datasource-permissions add <datasource_id> --user <user_id> --capability Connect --mode Allow
python -m src.cli_entry datasource-permissions delete <datasource_id> --user <user_id> --capability Connect --mode Allow
```

### Flow Operations

```bash
python -m src.cli_entry flow delete <flow_id>
python -m src.cli_entry flow run <flow_id>
python -m src.cli_entry flow update <flow_id> [--name <name>] [--project <project_id>]
python -m src.cli_entry flow runs <flow_id>
python -m src.cli_entry flow add-tag <flow_id> --tag <tag_name>
python -m src.cli_entry flow delete-tag <flow_id> --tag <tag_name>
python -m src.cli_entry flow-permissions get <flow_id>
python -m src.cli_entry flow-permissions add <flow_id> --user <user_id> --capability <name> --mode Allow|Deny
python -m src.cli_entry flow-permissions delete <flow_id> --user <user_id> --capability <name> --mode Allow|Deny
```

### Webhook Operations

```bash
python -m src.cli_entry webhook create --name <name> --url <destination_url> --event <event_name>
python -m src.cli_entry webhook delete <webhook_id>
python -m src.cli_entry webhook test <webhook_id>
```

### Data Alert Operations

```bash
python -m src.cli_entry data-alert delete <alert_id>
python -m src.cli_entry data-alert add-user <alert_id> --user <user_id>
python -m src.cli_entry data-alert remove-user <alert_id> --user <user_id>
```

### Extract Refresh & Jobs

```bash
python -m src.cli_entry refresh <task_id>
python -m src.cli_entry task run <task_id>
python -m src.cli_entry task delete <task_id>
python -m src.cli_entry job cancel <job_id>
```

### Schedule Management

```bash
python -m src.cli_entry schedule add-workbook <schedule_id> --workbook <workbook_id>
python -m src.cli_entry schedule add-datasource <schedule_id> --datasource <datasource_id>
python -m src.cli_entry schedule create --name <name> --frequency <Hourly|Daily|Weekly|Monthly> --start-time <HH:MM:SS>
python -m src.cli_entry schedule update <schedule_id> [--name <name>] [--frequency <freq>] [--start-time <time>] [--state Active|Suspended]
python -m src.cli_entry schedule delete <schedule_id>
```

### Site Management (Tableau Server only)

```bash
python -m src.cli_entry site create --name <name> --content-url <content_url>
python -m src.cli_entry site update [--name <name>] [--content-url <url>] [--state Active|Suspended]
python -m src.cli_entry site delete <site_id>
```

### Subscriptions

```bash
python -m src.cli_entry subscription create --subject "Report" --user <user_id> --schedule <schedule_id> --content-type View --content-id <view_id>
python -m src.cli_entry subscription update <subscription_id> [--subject <subject>] [--schedule <schedule_id>]
python -m src.cli_entry subscription delete --subscription-id <id>
```

### Favorites

```bash
python -m src.cli_entry favorites list
python -m src.cli_entry favorites add --content-type workbook --content-id <id> --label "My Workbook"
python -m src.cli_entry favorites delete --content-type workbook --content-id <id>
```

## Response Format

All commands output JSON with consistent structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

On error:
```json
{
  "success": false,
  "data": null,
  "error": "Error description"
}
```

## Gemini Integration

See `instructions.txt` for detailed instructions on integrating this tool with Gemini CLI.

## Session Management

- Sessions are stored in `.session.json` (gitignored)
- Tokens expire after 240 minutes (4 hours) per Tableau's policy
- The tool auto-authenticates when sessions expire
- Use `auth status` to check session validity

## API Version

This tool uses Tableau REST API version 3.22.

## License

MIT
