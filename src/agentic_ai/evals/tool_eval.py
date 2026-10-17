def tool_selection_precision(expected: set[str], actual: set[str]) -> float:
    if not actual:
        return 1.0 if not expected else 0.0
    return len(expected & actual) / len(actual)
