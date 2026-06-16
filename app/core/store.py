import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import httpx

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "crashlab.db"
DB = Path(os.getenv("CRASHLAB_DB_PATH", str(DEFAULT_DB))).expanduser().resolve()
DB.parent.mkdir(parents=True, exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")
SUPABASE_RUNS_TABLE = os.getenv("CRASHLAB_SUPABASE_RUNS_TABLE", "crashlab_runs")
SUPABASE_CASES_TABLE = os.getenv("CRASHLAB_SUPABASE_CASES_TABLE", "crashlab_cases")
SUPABASE_TARGETS_TABLE = os.getenv("CRASHLAB_SUPABASE_TARGETS_TABLE", "crashlab_configured_targets")
SUPABASE_PLANS_TABLE = os.getenv("CRASHLAB_SUPABASE_PLANS_TABLE", "crashlab_test_plans")
SUPABASE_PROBES_TABLE = os.getenv("CRASHLAB_SUPABASE_PROBES_TABLE", "crashlab_target_probes")


# SQLite remains the zero-config local fallback. Render or any hosted deployment can switch
# to Supabase by setting SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
def conn():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _supabase_headers(prefer: Optional[str] = None, object_mode: bool = False) -> Dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept-Profile": SUPABASE_SCHEMA,
        "Content-Profile": SUPABASE_SCHEMA,
    }
    if prefer:
        headers["Prefer"] = prefer
    if object_mode:
        headers["Accept"] = "application/vnd.pgrst.object+json"
    return headers


def _supabase_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def _supabase_request(method: str, table: str, *, params: Optional[Dict] = None, json_body=None, prefer: Optional[str] = None, object_mode: bool = False):
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.request(
            method,
            _supabase_url(table),
            headers=_supabase_headers(prefer=prefer, object_mode=object_mode),
            params=params,
            json=json_body,
        )
    response.raise_for_status()
    if not response.text.strip():
        return None
    return response.json()


def _warn_supabase_failure(action: str, exc: Exception):
    print(f"[CrashLab] Supabase {action} failed; falling back to SQLite: {exc}")


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


# SQLite is used as the local fallback system-of-record so local development and tests work
# without cloud infrastructure. Hosted deployments can transparently swap to Supabase.
def _ensure_column(connection, table, column, column_type):
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def has_any_runs() -> bool:
    init_db()
    if supabase_enabled():
        try:
            rows = _supabase_request("GET", SUPABASE_RUNS_TABLE, params={"select": "run_id", "limit": 1}) or []
            return bool(rows)
        except Exception as exc:
            _warn_supabase_failure("has_any_runs", exc)
    connection = conn()
    row = connection.execute("SELECT 1 FROM runs LIMIT 1").fetchone()
    connection.close()
    return bool(row)


def _sqlite_save_run(run):
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


# Runs and case rows are persisted so the dashboard, compare view, and exports all read
# the same ground truth even after a server restart. Supabase enables shared persistence.
def save_run(run):
    if supabase_enabled():
        try:
            _supabase_request(
                "POST",
                SUPABASE_RUNS_TABLE,
                json_body={
                    "run_id": run["run_id"],
                    "target_id": run["target_id"],
                    "target_name": run["target_name"],
                    "target_kind": run.get("target_kind"),
                    "target_profile": run.get("target_profile", {}),
                    "target_spec": run.get("target_spec", {}),
                    "status": run["status"],
                    "run_mode": run.get("run_mode", "demo"),
                    "created_at": run["created_at"],
                    "completed_at": run.get("completed_at"),
                    "score": run.get("score"),
                    "outcome": run.get("outcome"),
                    "summary": run.get("summary", ""),
                    "run_meta": run.get("run_meta", {}),
                    "category_scores": run.get("category_scores", {}),
                    "logs": run.get("logs", []),
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            _supabase_request("DELETE", SUPABASE_CASES_TABLE, params={"run_id": f"eq.{run['run_id']}"})
            cases = []
            for result in run.get("results", []):
                cases.append(
                    {
                        "run_id": run["run_id"],
                        "case_id": result["case_id"],
                        "category": result["category"],
                        "prompt": result["prompt"],
                        "variant": bool(result.get("variant")),
                        "passed": result.get("passed"),
                        "result_status": result.get("result_status", "unknown"),
                        "case_score": result.get("case_score"),
                        "response_text": result.get("response_text", ""),
                        "notes": result.get("notes", ""),
                        "meta": result.get("meta", {}),
                    }
                )
            if cases:
                _supabase_request("POST", SUPABASE_CASES_TABLE, json_body=cases, prefer="return=minimal")
            return
        except Exception as exc:
            _warn_supabase_failure("save_run", exc)
    _sqlite_save_run(run)


def _sqlite_save_configured_target(target_payload: Dict):
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


# Configured targets are stored separately from bootstrap JSON so the app can ship with
# known-good examples while still letting a user onboard new targets from the UI.
def save_configured_target(target_payload: Dict):
    if supabase_enabled():
        try:
            existing = _supabase_request("GET", SUPABASE_TARGETS_TABLE, params={"select": "id", "id": f"eq.{target_payload['id']}", "limit": 1}) or []
            now = int(time.time())
            _supabase_request(
                "POST",
                SUPABASE_TARGETS_TABLE,
                json_body={
                    "id": target_payload["id"],
                    "payload": target_payload,
                    "created_at": now,
                    "updated_at": now,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            return bool(existing)
        except Exception as exc:
            _warn_supabase_failure("save_configured_target", exc)
    return _sqlite_save_configured_target(target_payload)


def list_configured_targets() -> List[Dict]:
    init_db()
    if supabase_enabled():
        try:
            rows = _supabase_request("GET", SUPABASE_TARGETS_TABLE, params={"select": "payload", "order": "updated_at.desc"}) or []
            return [row["payload"] for row in rows]
        except Exception as exc:
            _warn_supabase_failure("list_configured_targets", exc)
    connection = conn()
    rows = connection.execute("SELECT payload FROM configured_targets ORDER BY updated_at DESC").fetchall()
    connection.close()
    return [json.loads(row["payload"]) for row in rows]


def _sqlite_save_test_plan(plan_payload: Dict):
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


# Test plans are stored separately from family templates so users can review, regenerate,
# and approve target-specific plans without mutating the shipped defaults.
def save_test_plan(plan_payload: Dict):
    if supabase_enabled():
        try:
            now = int(time.time())
            _supabase_request(
                "POST",
                SUPABASE_PLANS_TABLE,
                json_body={
                    "plan_id": plan_payload["plan_id"],
                    "target_id": plan_payload["target_id"],
                    "mode": plan_payload["mode"],
                    "source": plan_payload["source"],
                    "approved": bool(plan_payload.get("approved", True)),
                    "created_at": plan_payload.get("created_at", now),
                    "updated_at": now,
                    "payload": plan_payload,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            return
        except Exception as exc:
            _warn_supabase_failure("save_test_plan", exc)
    _sqlite_save_test_plan(plan_payload)


def list_test_plans(target_id: Optional[str] = None) -> List[Dict]:
    init_db()
    if supabase_enabled():
        try:
            params = {"select": "payload", "order": "updated_at.desc"}
            if target_id:
                params["target_id"] = f"eq.{target_id}"
            rows = _supabase_request("GET", SUPABASE_PLANS_TABLE, params=params) or []
            return [row["payload"] for row in rows]
        except Exception as exc:
            _warn_supabase_failure("list_test_plans", exc)
    connection = conn()
    if target_id:
        rows = connection.execute("SELECT payload FROM test_plans WHERE target_id = ? ORDER BY updated_at DESC", (target_id,)).fetchall()
    else:
        rows = connection.execute("SELECT payload FROM test_plans ORDER BY updated_at DESC").fetchall()
    connection.close()
    return [json.loads(row["payload"]) for row in rows]


def get_active_test_plan(target_id: str, mode: str) -> Optional[Dict]:
    init_db()
    if supabase_enabled():
        try:
            rows = _supabase_request(
                "GET",
                SUPABASE_PLANS_TABLE,
                params={
                    "select": "payload",
                    "target_id": f"eq.{target_id}",
                    "mode": f"eq.{mode}",
                    "approved": "eq.true",
                    "order": "updated_at.desc",
                    "limit": 1,
                },
            ) or []
            return rows[0]["payload"] if rows else None
        except Exception as exc:
            _warn_supabase_failure("get_active_test_plan", exc)
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


def _sqlite_save_probe_summary(target_id: str, payload: Dict):
    now = int(time.time())
    connection = conn()
    connection.execute(
        "INSERT OR REPLACE INTO target_probes(target_id,payload,created_at,updated_at) VALUES(?,?,COALESCE((SELECT created_at FROM target_probes WHERE target_id = ?), ?),?)",
        (target_id, json.dumps(payload), target_id, now, now),
    )
    connection.commit()
    connection.close()


# Probe summaries capture lightweight target-profile evidence without overwriting the full
# run history. This keeps optional probe-assisted planning separate from benchmark results.
def save_probe_summary(target_id: str, payload: Dict):
    if supabase_enabled():
        try:
            now = int(time.time())
            _supabase_request(
                "POST",
                SUPABASE_PROBES_TABLE,
                json_body={
                    "target_id": target_id,
                    "payload": payload,
                    "created_at": now,
                    "updated_at": now,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            return
        except Exception as exc:
            _warn_supabase_failure("save_probe_summary", exc)
    _sqlite_save_probe_summary(target_id, payload)


def get_probe_summary(target_id: str) -> Optional[Dict]:
    init_db()
    if supabase_enabled():
        try:
            rows = _supabase_request("GET", SUPABASE_PROBES_TABLE, params={"select": "payload", "target_id": f"eq.{target_id}", "limit": 1}) or []
            return rows[0]["payload"] if rows else None
        except Exception as exc:
            _warn_supabase_failure("get_probe_summary", exc)
    connection = conn()
    row = connection.execute("SELECT payload FROM target_probes WHERE target_id = ?", (target_id,)).fetchone()
    connection.close()
    return json.loads(row["payload"]) if row else None


def latest_runs():
    init_db()
    if supabase_enabled():
        try:
            rows = _supabase_request("GET", SUPABASE_RUNS_TABLE, params={"select": "*", "order": "created_at.desc", "limit": 40}) or []
            return [_decode_run_row(row) for row in rows]
        except Exception as exc:
            _warn_supabase_failure("latest_runs", exc)
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
    if supabase_enabled():
        try:
            rows = _supabase_request("GET", SUPABASE_RUNS_TABLE, params={"select": "*", "run_id": f"eq.{run_id}", "limit": 1}) or []
            if not rows:
                return None
            case_rows = _supabase_request("GET", SUPABASE_CASES_TABLE, params={"select": "*", "run_id": f"eq.{run_id}", "order": "created_at.asc"}) if False else _supabase_request("GET", SUPABASE_CASES_TABLE, params={"select": "*", "run_id": f"eq.{run_id}"}) or []
            run = _decode_run_row(rows[0])
            run["results"] = [_decode_case_row(case) for case in case_rows]
            return run
        except Exception as exc:
            _warn_supabase_failure("get_run_record", exc)
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


def _decode_json_field(value, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _decode_run_row(row):
    data = dict(row)
    data["target_profile"] = _decode_json_field(data.get("target_profile"), {})
    data["target_spec"] = _decode_json_field(data.get("target_spec"), {})
    data["run_meta"] = _decode_json_field(data.get("run_meta"), {})
    data["category_scores"] = _decode_json_field(data.get("category_scores"), {})
    data["logs"] = _decode_json_field(data.get("logs"), [])
    return data


def _decode_case_row(row):
    data = dict(row)
    passed = data.get("passed")
    if passed is None:
        data["passed"] = None
    elif isinstance(passed, bool):
        data["passed"] = passed
    else:
        data["passed"] = bool(passed)
    data["variant"] = bool(data.get("variant"))
    data["meta"] = _decode_json_field(data.get("meta"), {})
    return data
