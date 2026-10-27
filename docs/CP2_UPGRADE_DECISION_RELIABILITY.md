# Project 14 — CP2 Agent Decisions and Read-Tool Reliability Upgrade

**Scope:** Additive, offline/synthetic reliability upgrades to existing local LangGraph orchestration. This is not an LLM tool planner or production agent.

## New opt-in controls

1. **Policy-gated plan proposals:** `WorkflowEngine.start(request, proposed_plan=[...])` validates a plan against a finite trusted set before any SQLite state or tool call is created. `analysis` may swap its two independent read-only steps, but cannot omit either, move verification, introduce tools, bypass approval, or change report writes. Default plans are unchanged.
2. **Checkpoint plan integrity:** `resume` and `decide` reject unsupported persisted plan shapes, cursors and unauthorized tools before execution. This is an application policy check, **not** a cryptographic signature or defense against a fully attacker-writable database.
3. **Per-engine, in-memory read-tool circuit breaker:** opt in with `read_circuit=ReadToolCircuit(max_consecutive_failures=2)`. Consecutive read execution failures block further attempts for that tool until explicitly reset by a trusted operator. Writes are never auto-retried, and the circuit does not apply to writes. No timer, durable shared state, network requests or hard tool timeout exists.
4. **No sensitive observability:** the circuit snapshot reports only tool names, failure counts and blocked flags, not raw inputs or traces.

## Opt-in examples (synthetic only)

```python
from agentic_ai.workflow import WorkflowEngine
from agentic_ai.decision_controls import ReadToolCircuit, ALTERNATE_ANALYSIS
from pathlib import Path

engine = WorkflowEngine(Path('local-synthetic-root'), read_circuit=ReadToolCircuit(2))
state = engine.start({
    'request_id': 'safe-demo-001', 'task_type': 'analysis',
    'metrics': {'values': [10, 20, 30]},
    'retrieval': {'query': 'leave policy'}
}, proposed_plan=list(ALTERNATE_ANALYSIS))
print(state.status)
engine.store.close()
```

Report workflows retain independent reviewer approval. Never use this demonstration with confidential data or expose the local API publicly.

## Verification gates

- Previous local baseline: 81 tests passed and 23/23 frozen synthetic evaluations; commit `b0c538bc11a2dff5d3d8e05ea4500ceb37c654c2`.
- Upgrade: 32 new contract/negative tests. **Target 113 tests passed, zero failures or skips**, plus 23/23 evaluation scenarios and existing audit pass.
- Local developer-only suite (using a replacement synthetic fixture because the original snapshot excludes data): 94 passed, 1 LangGraph-dependent skip. **This does not constitute full Windows acceptance.**
- Installer copies only four allowlisted code/docs/test files and backs up the previous `workflow.py`. Original `.env`, fixtures, SQLite, outputs, git history and credentials remain untouched. No commit or push.
- Evidence is stored in `CP2_Upgrade/Evidence`; exclude that folder and patch installer from Git staging.

## Limitations and CP3 candidates

Deterministic demo routes are not general LLM planning. This upgrade does not demonstrate production load handling, enterprise authentication, signed checkpoints, distributed circuit breakers, or per-tool timeouts. CP3 should add controlled tool-fault and injection evaluations, measured failure detection/recovery and approval-resume adversarial tests.
