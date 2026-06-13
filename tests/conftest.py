import os
import tempfile
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("CRASHLAB_LOAD_DOTENV", "0")
os.environ.setdefault("CRASHLAB_SEED_SAMPLE_DATA", "0")
os.environ.setdefault("CRASHLAB_DB_PATH", str(Path(tempfile.gettempdir()) / f"crashlab-test-{uuid.uuid4().hex}.db"))

from fastapi.testclient import TestClient

from app.main import app, reload_registry
from app.core.models import Target
from app.core.store import conn, init_db


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    connection = conn()
    for table in ("cases", "runs", "test_plans", "target_probes", "configured_targets"):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()
    reload_registry(app)
    yield
    connection = conn()
    for table in ("cases", "runs", "test_plans", "target_probes", "configured_targets"):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()
    reload_registry(app)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

