def route_task(user_query: str) -> str:
    q = user_query.lower()
    if "policy" in q or "document" in q:
        return "retrieval"
    if "average" in q or "mean" in q or "metric" in q:
        return "metrics"
    return "general"
