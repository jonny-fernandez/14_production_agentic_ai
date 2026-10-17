def routing_accuracy(expected: list[str], actual: list[str]) -> float:
    if len(expected) != len(actual):
        raise ValueError("Expected and actual lengths differ.")
    return sum(e == a for e, a in zip(expected, actual)) / len(expected) if expected else 0.0
