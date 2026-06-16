"""The 7 Helios agents and their ENFORCED per-agent tool allow-lists (Bible §18.9).

The allow-list is the governance mechanism: an agent may only call tools in its set, so the
Narrator (which writes prose) structurally cannot touch BigQuery, and the Decompose agent
can only run the decomposition. The Toolbox enforces this on every call.

`model` records the intended tier (the SDK orchestration will use it); the deterministic
orchestrator here doesn't dispatch by model.
"""
from __future__ import annotations

AGENTS: dict[str, dict] = {
    # Coordinates the plan; makes the ship/suppress decision; persists the result.
    "Orchestrator": {"model": "opus",
                     "allow": {"check_suppression", "save_diagnosis", "recall_prior"}},
    # Watches metrics, pulls governed data, checks memory for repeats.
    "Monitor": {"model": "sonnet",
                "allow": {"build_query", "dry_run", "run_query", "recall_prior"}},
    # Splits the move into mix/rate/interaction — nothing else.
    "Decompose": {"model": "sonnet", "allow": {"decompose_change"}},
    # Tests significance, reconciles, grounds metric meaning.
    "Diagnose": {"model": "opus", "allow": {"significance_test", "reconcile", "get_metric"}},
    # Sizes the experiment.
    "Prescribe": {"model": "sonnet",
                  "allow": {"design_experiment", "power_analysis", "runtime_estimate"}},
    # Writes the brief. Deliberately has NO data or math tools (G2) — only render + lookup.
    "Narrator": {"model": "sonnet", "allow": {"render_brief", "get_metric"}},
    # Attacks the finding; may re-verify via reconcile / memory. Gates the ship decision.
    "Critic": {"model": "opus", "allow": {"critique", "reconcile", "recall_prior"}},
}

# The plan-execute-critique order the Orchestrator drives.
PIPELINE = ["Monitor", "Decompose", "Diagnose", "Critic", "Prescribe", "Narrator"]


def allows(agent: str, tool: str) -> bool:
    return tool in AGENTS.get(agent, {}).get("allow", set())
