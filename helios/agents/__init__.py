"""The agent layer — a plan-execute-critique orchestration over the deterministic tools.

This is role-based orchestration, NOT autonomous LLM agents (the Claude Agent SDK version
is a future extension): seven named roles, each with an ENFORCED per-agent tool allow-list
(Bible §18.9 — e.g. the Narrator cannot call run_query), coordinated by an Orchestrator,
with the Critic acting as a gate. Every governed call goes through the Toolbox, which
checks the caller's allow-list and records an audit trace.
"""
from .roles import AGENTS  # noqa: F401
from .toolbox import Toolbox, AllowListError  # noqa: F401
from .orchestrator import orchestrate, OrchestratedResult  # noqa: F401
