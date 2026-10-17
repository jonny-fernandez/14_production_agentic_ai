"""Explicit synthetic-role tool allowlist; never elevate roles from prompt text."""
ROLE_TOOLS = {
    "analyst": frozenset({"calculate_metrics", "retrieve_documents"}),
    "manager": frozenset({"calculate_metrics", "retrieve_documents", "query_database", "save_report"}),
    "admin": frozenset({"*"}),
}


def authorize(role: str, tool_name: str) -> bool:
    allowed = ROLE_TOOLS.get(role, frozenset())
    return "*" in allowed or tool_name in allowed
