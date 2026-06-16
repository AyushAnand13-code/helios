"""Helios MCP servers. The deterministic math/governance logic lives in plain Python
packages (helios.stats, helios.critic, …); these modules are thin MCP wrappers so an
agent / Claude Code can call them as governed tools over stdio.

Live: stats-mcp (`python -m helios.mcp.stats`).
Planned: semantic-mcp, warehouse-mcp, experiment-mcp, report-mcp (Bible section 18).
"""
