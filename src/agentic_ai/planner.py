"""Finite, deterministic plans. These are tool names, not prompts."""


def make_plan(task_type: str) -> list[str]:
    if task_type == "retrieval":
        return ["retrieve_documents", "verify_evidence", "answer"]
    if task_type == "metrics":
        return ["calculate_metrics", "verify_result", "answer"]
    if task_type == "analysis":
        return ["calculate_metrics", "retrieve_documents", "verify_evidence", "answer"]
    if task_type == "report":
        return ["calculate_metrics", "retrieve_documents", "request_approval", "save_report", "answer"]
    return ["clarify_or_answer_safely"]
