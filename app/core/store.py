import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

DB = Path(__file__).resolve().parents[1] / "data" / "crashlab.db"
DB.parent.mkdir(parents=True, exist_ok=True)


def conn():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = conn()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs(
            run_id TEXT PRIMARY KEY,
            target_id TEXT,
            target_name TEXT,
            target_kind TEXT,
            target_profile TEXT,
            target_spec TEXT,
            status TEXT,
            run_mode TEXT,
            created_at INTEGER,
            completed_at INTEGER,
            score INTEGER,
            outcome TEXT,
            summary TEXT,
            run_meta TEXT,
            category_scores TEXT,
            logs TEXT
        );
        CREATE TABLE IF NOT EXISTS cases(
            run_id TEXT,
            case_id TEXT,
            category TEXT,
            prompt TEXT,
            variant INTEGER,
            passed INTEGER,
            result_status TEXT,
            case_score INTEGER,
            response_text TEXT,
            notes TEXT,
            meta TEXT
        );
        CREATE TABLE IF NOT EXISTS configured_targets(
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS test_plans(
            plan_id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            source TEXT NOT NULL,
            approved INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS target_probes(
            target_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    _ensure_column(connection, "runs", "completed_at", "INTEGER")
    _ensure_column(connection, "runs", "outcome", "TEXT")
    _ensure_column(connection, "runs", "summary", "TEXT")
    _ensure_column(connection, "runs", "run_meta", "TEXT")
    _ensure_column(connection, "runs", "target_kind", "TEXT")
    _ensure_column(connection, "runs", "target_profile", "TEXT")
    _ensure_column(connection, "runs", "target_spec", "TEXT")
    _ensure_column(connection, "runs", "run_mode", "TEXT")
    _ensure_column(connection, "cases", "result_status", "TEXT")
    _ensure_column(connection, "cases", "case_score", "INTEGER")
    _ensure_column(connection, "cases", "meta", "TEXT")
    connection.commit()
    connection.close()


# SQLite is used as the local system-of-record for configured targets, generated plans,
# probe summaries, and run history so the dashboard and exports share the same evidence.
def _ensure_column(connection, table, column, column_type):
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


# Runs and case rows are persisted so the dashboard, compare view, and exports all read
# the same trustworthy ground truth even after a server restart.
def save_run(run):
    connection = conn()
    connection.execute("DELETE FROM cases WHERE run_id = ?", (run["run_id"],))
    connection.execute(
        "INSERT OR REPLACE INTO runs(run_id,target_id,target_name,target_kind,target_profile,target_spec,status,run_mode,created_at,completed_at,score,outcome,summary,run_meta,category_scores,logs) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            run["run_id"],
            run["target_id"],
            run["target_name"],
            run.get("target_kind"),
            json.dumps(run.get("target_profile", {})),
            json.dumps(run.get("target_spec", {})),
            run["status"],
            run.get("run_mode", "demo"),
            run["created_at"],
            run.get("completed_at"),
            run.get("score"),
            run.get("outcome"),
            run.get("summary", ""),
            json.dumps(run.get("run_meta", {})),
            json.dumps(run.get("category_scores", {})),
            json.dumps(run.get("logs", [])),
        ),
    )
    for result in run.get("results", []):
        connection.execute(
            "INSERT INTO cases(run_id,case_id,category,prompt,variant,passed,result_status,case_score,response_text,notes,meta) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                run["run_id"],
                result["case_id"],
                result["category"],
                result["prompt"],
                1 if result.get("variant") else 0,
                None if result.get("passed") is None else (1 if result["passed"] else 0),
                result.get("result_status", "unknown"),
                result.get("case_score"),
                result.get("response_text", ""),
                result.get("notes", ""),
                json.dumps(result.get("meta", {})),
            ),
        )
    connection.commit()
    connection.close()


# Configured targets are stored separately from bootstrap JSON so the app can ship with
# known-good examples while still letting a user onboard new targets from the UI.
def save_configured_target(target_payload: Dict):
    now = int(time.time())
    connection = conn()
    existing = connection.execute("SELECT 1 FROM configured_targets WHERE id = ?", (target_payload["id"],)).fetchone()
    connection.execute(
        "INSERT OR REPLACE INTO configured_targets(id,payload,created_at,updated_at) VALUES(?,?,COALESCE((SELECT created_at FROM configured_targets WHERE id = ?), ?),?)",
        (
            target_payload["id"],
            json.dumps(target_payload),
            target_payload["id"],
            now,
            now,
        ),
    )
    connection.commit()
    connection.close()
    return bool(existing)


def list_configured_targets() -> List[Dict]:
    init_db()
    connection = conn()
    rows = connection.execute("SELECT payload FROM configured_targets ORDER BY updated_at DESC").fetchall()
    connection.close()
    return [json.loads(row["payload"]) for row in rows]


# Test plans are stored separately from family templates so users can review, regenerate,
# and approve target-specific plans without mutating the shipped defaults.
def save_test_plan(plan_payload: Dict):
    now = int(time.time())
    connection = conn()
    connection.execute(
        "INSERT OR REPLACE INTO test_plans(plan_id,target_id,mode,source,approved,created_at,updated_at,payload) VALUES(?,?,?,?,?,?,?,?)",
        (
            plan_payload["plan_id"],
            plan_payload["target_id"],
            plan_payload["mode"],
            plan_payload["source"],
            1 if plan_payload.get("approved", True) else 0,
            plan_payload.get("created_at", now),
            now,
            json.dumps(plan_payload),
        ),
    )
    connection.commit()
    connection.close()


def list_test_plans(target_id: Optional[str] = None) -> List[Dict]:
    init_db()
    connection = conn()
    if target_id:
        rows = connection.execute("SELECT payload FROM test_plans WHERE target_id = ? ORDER BY updated_at DESC", (target_id,)).fetchall()
    else:
        rows = connection.execute("SELECT payload FROM test_plans ORDER BY updated_at DESC").fetchall()
    connection.close()
    return [json.loads(row["payload"]) for row in rows]


def get_active_test_plan(target_id: str, mode: str) -> Optional[Dict]:
    init_db()
    connection = conn()
    row = connection.execute(
        "SELECT payload FROM test_plans WHERE target_id = ? AND mode = ? AND approved = 1 ORDER BY updated_at DESC LIMIT 1",
        (target_id, mode),
    ).fetchone()
    connection.close()
    return json.loads(row["payload"]) if row else None


def latest_plan_summaries() -> Dict[str, Dict]:
    summaries: Dict[str, Dict] = {}
    for plan in list_test_plans():
        key = f"{plan['target_id']}::{plan['mode']}"
        if key not in summaries:
            summaries[key] = {
                "plan_id": plan["plan_id"],
                "mode": plan["mode"],
                "source": plan["source"],
                "approved": plan.get("approved", True),
                "case_count": len(plan.get("cases", [])),
                "created_at": plan.get("created_at"),
            }
    return summaries


# Probe summaries capture lightweight target-profile evidence without overwriting the full
# run history. This keeps optional probe-assisted planning separate from benchmark results.
def save_probe_summary(target_id: str, payload: Dict):
    now = int(time.time())
    connection = conn()
    connection.execute(
        "INSERT OR REPLACE INTO target_probes(target_id,payload,created_at,updated_at) VALUES(?,?,COALESCE((SELECT created_at FROM target_probes WHERE target_id = ?), ?),?)",
        (target_id, json.dumps(payload), target_id, now, now),
    )
    connection.commit()
    connection.close()


def get_probe_summary(target_id: str) -> Optional[Dict]:
    init_db()
    connection = conn()
    row = connection.execute("SELECT payload FROM target_probes WHERE target_id = ?", (target_id,)).fetchone()
    connection.close()
    return json.loads(row["payload"]) if row else None


def latest_runs():
    init_db()
    connection = conn()
    rows = connection.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 40").fetchall()
    connection.close()
    return [_decode_run_row(row) for row in rows]


def latest_run_snapshots_by_target() -> Dict[str, Dict]:
    snapshots: Dict[str, Dict] = {}
    for run in latest_runs():
        snapshots.setdefault(run["target_id"], run)
    return snapshots


def get_run_record(run_id: str) -> Optional[Dict]:
    init_db()
    connection = conn()
    row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        connection.close()
        return None
    cases = connection.execute("SELECT * FROM cases WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
    connection.close()
    run = _decode_run_row(row)
    run["results"] = [_decode_case_row(case) for case in cases]
    return run


def _decode_run_row(row):
    data = dict(row)
    data["target_profile"] = json.loads(data.get("target_profile") or "{}")
    data["target_spec"] = json.loads(data.get("target_spec") or "{}")
    data["run_meta"] = json.loads(data.get("run_meta") or "{}")
    data["category_scores"] = json.loads(data.get("category_scores") or "{}")
    data["logs"] = json.loads(data.get("logs") or "[]")
    return data


def _decode_case_row(row):
    data = dict(row)
    data["passed"] = None if data.get("passed") is None else bool(data["passed"])
    data["variant"] = bool(data.get("variant"))
    data["meta"] = json.loads(data.get("meta") or "{}")
    return data
