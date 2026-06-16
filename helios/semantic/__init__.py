"""The governed semantic layer — the ONLY path to SQL (grounding rule G1).

Loads semantic/semantic_layer.yaml and composes governed SQL from registered
metric/dimension definitions. Nothing here hand-authors SQL: a query is assembled from
each metric's `sql_definition` and each dimension's column expression, and any unknown
or unsupported name is a hard error (G5), never a fallback to free SQL.
"""
from .layer import SemanticLayer, SemanticError, DEFAULT_REGISTRY  # noqa: F401
