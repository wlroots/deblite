"""UI-agnostic installation logic.

Nothing in this package imports GTK, Qt or any frontend. Every destructive
operation goes through :class:`installer.core.executor.Executor` so that
``--debug`` is a real, safe dry-run.
"""
