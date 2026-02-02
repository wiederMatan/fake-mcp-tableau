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

### Testing
```bash
# Verify authentication
python -m src.cli_entry auth login
python -m src.cli_entry auth status

# List resources
python -m src.cli_entry list projects
python -m src.cli_entry list workbooks
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

- **engine.py**: `TableauEngine` class wrapping Tableau REST API v3.22. Methods for auth, discovery (sites, projects, workbooks), and operations (extract refresh, permissions).

- **cli_entry.py**: CLI interface outputting JSON responses for Gemini parsing. All responses follow `{success, data, error}` format.

### Configuration

Environment variables in `.env`:
- `TABLEAU_SERVER_URL` - Server/Cloud URL
- `TABLEAU_SITE_ID` - Site content URL
- `TABLEAU_PAT_NAME` - Personal Access Token name
- `TABLEAU_PAT_SECRET` - Personal Access Token secret
