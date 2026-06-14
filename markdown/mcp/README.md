# mcp/

The Helios MCP servers - the governed tool layer.

- Build it: `docs/architecture/MCP_ARCHITECTURE.md` (milestones M6 / M6b).
- Servers: `warehouse-mcp`, `semantic-mcp`, `stats-mcp`, `experiment-mcp`, `report-mcp`.
- `semantic-mcp` reads `models/semantic/semantic_layer.yaml` and is the only path to SQL (0 hallucinated columns).

_Lean v1 builds one server. Empty until M6._
