"""LLM layer for the grounded Decision Brief.

The model NEVER writes SQL and NEVER computes a statistic — it calls the governed
tools in this package (which wrap the deterministic engine + the metric registry).
Provider-swappable: brief.py uses Gemini today; swap the client to use another model.
"""
