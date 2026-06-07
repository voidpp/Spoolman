# Spoolman MCP Server

<!-- FORK: multi-tenancy -->

An MCP (Model Context Protocol) server that lets AI agents manage your Spoolman filament inventory.

## Prerequisites

1. Spoolman running with auth enabled (`auth_providers.yaml` configured)
2. A long-lived API token — log in → **Settings → Account → Create Token**

## Installation

The MCP server is included in Spoolman's virtualenv:

```bash
# Already installed if you set up the dev environment
.venv/bin/pip install fastmcp~=2.0
```

## Usage

### stdio (Claude Desktop / Cursor / local agents)

Run as a stdio subprocess — the agent client starts it automatically.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "spoolman": {
      "command": "/path/to/Spoolman/.venv/bin/python",
      "args": ["-m", "spoolman.mcp.server"],
      "env": {
        "SPOOLMAN_API_URL": "http://localhost:7912/api/v1",
        "SPOOLMAN_API_TOKEN": "your-bearer-token-here"
      }
    }
  }
}
```

Or using the installed script (after `pip install -e .`):

```json
{
  "mcpServers": {
    "spoolman": {
      "command": "/path/to/Spoolman/.venv/bin/spoolman-mcp",
      "args": ["--url", "http://localhost:7912/api/v1", "--token", "your-token"]
    }
  }
}
```

### HTTP (web agents, n8n, OpenWebUI, etc.)

```bash
SPOOLMAN_API_TOKEN=<spoolman-token> \
MCP_AUTH_TOKEN=<secret-for-mcp-clients> \
  .venv/bin/python -m spoolman.mcp.server \
    --transport http \
    --host 0.0.0.0 \
    --port 8001 \
    --url http://localhost:7912/api/v1
```

Web agents connect to `http://your-host:8001/mcp` with `Authorization: Bearer <MCP_AUTH_TOKEN>`.

## Available Tools

| Tool | Description |
|------|-------------|
| `get_current_user` | Confirm connection + which account is active |
| `inventory_summary` | Overview: counts, total weight by material, low-stock alerts |
| `list_spools` | Search/filter active spools by material, location, color, vendor |
| `get_spool` | Full detail of a single spool |
| `find_spools_for_print` | Given material + grams needed, find suitable spools |
| `list_filaments` | Browse filament library |
| `list_vendors` | List all vendors |
| `list_locations` | All distinct storage locations |
| `record_usage` | Log filament consumption (by weight or length) |
| `measure_spool` | Update remaining from a gross scale measurement |
| `create_spool` | Add a new spool |
| `update_spool` | Update location, comment, lot number |
| `archive_spool` | Mark a spool as finished/archived |

## Example Prompts

- *"What PLA do I have and how much is left?"*
- *"I'm printing with PETG and need about 80g. Which spool should I use?"*
- *"Log that I used 45g from spool 3"*
- *"I just weighed spool 7 and it's 234g total. Update it."*
- *"Move all spools in Drawer 1 to Shelf B"* (use `update_spool` per spool)
- *"Which spools are running low?"* (use `inventory_summary`)
