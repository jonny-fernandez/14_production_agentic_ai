from agentic_ai.approval.human_review import requires_human_approval
from agentic_ai.evals.routing_eval import routing_accuracy

def test_sensitive_action_requires_approval():
    assert requires_human_approval(True, 0.99)

def test_low_confidence_requires_approval():
    assert requires_human_approval(False, 0.50)

def test_routing_accuracy():
    assert routing_accuracy(["sql", "rag"], ["sql", "rag"]) == 1.0
