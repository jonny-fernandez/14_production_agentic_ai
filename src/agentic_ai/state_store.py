"""SQLite checkpoint store, single-machine demo with optimistic concurrency checks."""
import sqlite3
from pathlib import Path
from agentic_ai.state import AgentState


class StateConflictError(RuntimeError):
    pass


class SQLiteStateStore:
    def __init__(self, path: str = "agent_state.db") -> None:
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path_obj), timeout=3.0)
        self.conn.execute("PRAGMA busy_timeout=3000")
        self.conn.execute("CREATE TABLE IF NOT EXISTS state (request_id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0)")
        self.conn.commit()

    def create(self, state: AgentState) -> None:
        try:
            self.conn.execute("INSERT INTO state(request_id, payload, revision) VALUES (?, ?, ?)",
                              (state.request_id, state.model_dump_json(), state.revision))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise StateConflictError("Request ID already exists; load or resume it") from None

    def save(self, state: AgentState) -> None:
        previous = state.revision
        new = state.model_copy(update={"revision": previous + 1})
        result = self.conn.execute("UPDATE state SET payload = ?, revision = ? WHERE request_id = ? AND revision = ?",
                                   (new.model_dump_json(), new.revision, state.request_id, previous))
        self.conn.commit()
        if result.rowcount != 1:
            raise StateConflictError("Stale or unknown execution state")
        state.revision = new.revision

    def load(self, request_id: str) -> AgentState | None:
        row = self.conn.execute("SELECT payload FROM state WHERE request_id = ?", (request_id,)).fetchone()
        return AgentState.model_validate_json(row[0]) if row else None

    def close(self) -> None:
        self.conn.close()
