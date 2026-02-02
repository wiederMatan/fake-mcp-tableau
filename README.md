# Fake MCP Tableau

A Python CLI toolkit that acts as a bridge between Gemini CLI and Tableau REST API, mimicking MCP (Model Context Protocol) capabilities through local execution.

## Features

- **Authentication Management**: Sign in with Personal Access Tokens, automatic session persistence
- **Resource Discovery**: List sites, projects, workbooks, data sources, users, groups, jobs, schedules, subscriptions
- **User & Group Management**: Add/remove users, manage group membership
- **Workbook & Data Source Operations**: View details, list views, delete resources, manage permissions
- **Extract Refresh**: List tasks, trigger refreshes, monitor jobs
- **Subscriptions & Favorites**: Create subscriptions, manage favorites
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
python -m src.cli_entry list datasources
python -m src.cli_entry list users
python -m src.cli_entry list groups
python -m src.cli_entry list jobs
python -m src.cli_entry list schedules      # Tableau Server only
python -m src.cli_entry list subscriptions
python -m src.cli_entry list refresh-tasks
```

### Getting Resource Details

```bash
python -m src.cli_entry get workbook <id>
python -m src.cli_entry get user <id>
python -m src.cli_entry get datasource <id>
python -m src.cli_entry get job <id>
python -m src.cli_entry get view <id>
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
```

### Workbook Operations

```bash
python -m src.cli_entry workbook views <workbook_id>
python -m src.cli_entry workbook delete <workbook_id>
```

### Data Source Operations

```bash
python -m src.cli_entry datasource delete <datasource_id>
```

### Extract Refresh & Jobs

```bash
python -m src.cli_entry refresh <task_id>
python -m src.cli_entry job cancel <job_id>
```

### Schedule Management

```bash
python -m src.cli_entry schedule add-workbook <schedule_id> --workbook <workbook_id>
python -m src.cli_entry schedule add-datasource <schedule_id> --datasource <datasource_id>
```

### Permissions (Workbook)

```bash
python -m src.cli_entry workbook-permissions get <workbook_id>
python -m src.cli_entry workbook-permissions add <workbook_id> --user <user_id> --capability Read --mode Allow
python -m src.cli_entry workbook-permissions delete <workbook_id> --user <user_id> --capability Read --mode Allow
```

### Permissions (Data Source)

```bash
python -m src.cli_entry datasource-permissions get <datasource_id>
python -m src.cli_entry datasource-permissions add <datasource_id> --user <user_id> --capability Connect --mode Allow
python -m src.cli_entry datasource-permissions delete <datasource_id> --user <user_id> --capability Connect --mode Allow
```

### Subscriptions

```bash
python -m src.cli_entry subscription create --subject "Report" --user <user_id> --schedule <schedule_id> --content-type View --content-id <view_id>
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
