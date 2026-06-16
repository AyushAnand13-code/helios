"""Rendering of Helios findings into shippable artifacts (Markdown Decision Briefs,
later PDF/Slack). Pure formatting over the deterministic Diagnosis + Critic outputs —
no data access, no math, no LLM."""
from .brief_md import render_brief_md  # noqa: F401
