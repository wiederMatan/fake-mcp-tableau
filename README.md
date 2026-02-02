# Fake MCP Tableau

A Python CLI toolkit that acts as a bridge between Gemini CLI and Tableau REST API, mimicking MCP (Model Context Protocol) capabilities through local execution.

## Features

- **Authentication Management**: Sign in with Personal Access Tokens, automatic session persistence
- **Resource Discovery**: List sites, projects, workbooks, and extract refresh tasks
- **Operations**: Trigger extract refreshes, manage workbook permissions
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
# Sign in
python -m src.cli_entry auth login

# Check session status
python -m src.cli_entry auth status

# Sign out
python -m src.cli_entry auth logout
```

### Listing Resources

```bash
# List all sites (Tableau Server only)
python -m src.cli_entry list sites

# List projects
python -m src.cli_entry list projects

# List workbooks
python -m src.cli_entry list workbooks

# List extract refresh tasks
python -m src.cli_entry list refresh-tasks
```

### Resource Details

```bash
# Get workbook details
python -m src.cli_entry get workbook <workbook_id>
```

### Operations

```bash
# Trigger extract refresh
python -m src.cli_entry refresh <task_id>
```

### Permissions

```bash
# Get workbook permissions
python -m src.cli_entry permissions get <workbook_id>

# Add permission
python -m src.cli_entry permissions add <workbook_id> --user <user_id> --capability Read --mode Allow

# Delete permission
python -m src.cli_entry permissions delete <workbook_id> --user <user_id> --capability Read --mode Allow
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
