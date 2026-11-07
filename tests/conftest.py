import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import open_database  # noqa: E402
from backend.models import AlertIn, EventIn  # noqa: E402

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)  # fixed, safely in the past (models reject future timestamps)


@pytest.fixture
def db(tmp_path):
    database = open_database(tmp_path / "test.db")
    yield database
    database.close()


def syn(ip="10.0.0.5", port=80, at=NOW, dst="10.0.0.1", source="sensor-1"):
    return EventIn(type="network_connection", timestamp=at, source=source,
                   src_ip=ip, dst_ip=dst, dst_port=port)


def dns(name="example.com", ip="10.0.0.5", at=NOW):
    return EventIn(type="dns_query", timestamp=at, source="sensor-1", src_ip=ip, dns_name=name)


def auth(user="admin", ip="10.0.0.9", at=NOW):
    return EventIn(type="auth_failure", timestamp=at, source="webapp", src_ip=ip, username=user)


def http(path="/", ip="10.0.0.9", at=NOW, status=200):
    return EventIn(type="http_request", timestamp=at, source="webapp", src_ip=ip,
                   http_method="get", http_path=path, http_status=status)


def alert(rule="port_scan", ip="10.0.0.5", ids=(1, 2, 3), severity="medium"):
    return AlertIn(rule=rule, severity=severity, title=f"Possible {rule} from {ip}",
                   src_ip=ip, evidence_event_ids=list(ids),
                   explanation={"threshold": 20, "window_seconds": 30, "observed": len(ids)})


def ago(seconds=0, **kw):
    return NOW - timedelta(seconds=seconds, **kw)


# --------------------------------------------------------------------------
# Whole-application fixtures (used by the route tests)
# --------------------------------------------------------------------------
API_KEY = "test-ingest-key"
JWT_SECRET = "test-jwt-secret-that-is-at-least-32-chars"


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """Isolated settings: own database file, known keys, nothing cached from other tests."""
    from backend.config import get_settings

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("API_KEY", API_KEY)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("ALERT_COOLDOWN_SECONDS", "300")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def api(app_env):
    """A started application plus a TestClient. ``api.app.state.db`` is the live database."""
    from fastapi.testclient import TestClient

    from backend.main import create_app

    app = create_app(mount_static=False)
    with TestClient(app) as client:
        client.app_ref = app
        yield client


def ingest_headers():
    return {"X-API-Key": API_KEY}


def event_json(**over):
    """A valid event body stamped 'now' (models reject timestamps in the future)."""
    from backend.models import utcnow

    body = {
        "type": "network_connection",
        "timestamp": utcnow().isoformat(),
        "source": "sensor-1",
        "src_ip": "10.0.0.5",
        "dst_ip": "10.0.0.1",
        "dst_port": 80,
        "protocol": "tcp",
    }
    body.update(over)
    return body
