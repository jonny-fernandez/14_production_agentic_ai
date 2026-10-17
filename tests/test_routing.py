from agentic_ai.router import route_task
from agentic_ai.planner import make_plan
from agentic_ai.authorization import authorize

def test_policy_routes_to_retrieval():
    assert route_task("What does the policy say?") == "retrieval"

def test_metrics_route():
    assert "calculate_metrics" in make_plan(route_task("What is the average metric?"))

def test_authorization_denies_unknown_tool():
    assert not authorize("analyst", "query_database")
