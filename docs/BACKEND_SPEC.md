# CYBER-MI6 — Backend Specification

## API endpoints

Authentication: sensors send the ingestion API key; people log in at `/api/token` and send `Authorization: Bearer <token>`. Every route except `/api/token` and `POST /api/events` needs a login; the `/api/users*` routes also need the admin role. Errors always look like `{"error": ..., "detail": ...}`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/token` | Dashboard login. Body `{"username", "password"}`; returns `{access_token, token_type, user}`. Rate limited per IP |
| POST | `/api/events` | Ingest and validate one event, or a batch as `{"events": [...]}`. Requires the ingestion API key (`X-API-Key`), not a login |
| GET | `/api/events` | Recent events with filters: `type`, `src_ip`, `from`, `to`, `limit`, `offset`. Requires login |
| GET | `/api/alerts` | Alerts with filters: `severity`, `status`, `rule`, `limit` |
| GET | `/api/alerts/{id}` | Alert detail with evidence events |
| PATCH | `/api/alerts/{id}` | Change status (`new`, `investigating`, `resolved`, `false_positive`) |
| GET | `/api/stats` | Counts for the dashboard (events, alerts by severity, top source IPs) |
| GET | `/api/users` | List dashboard accounts. **Admin only** |
| POST | `/api/users` | Create an account (`username`, `password`, `role`, `status`). **Admin only** |
| PATCH | `/api/users/{id}` | Edit username, password, role or status. **Admin only** |
| PATCH | `/api/users/{id}/status` | Enable or disable an account. **Admin only** |
| WS | `/ws` | Live stream of new events and alerts. The client's first message must be `{"type": "auth", "token": "<JWT>"}`; refused sockets are closed with code 4401 |
| GET | `/docs` | Auto-generated OpenAPI documentation (the API contract) |

### Example ingestion request

```http
POST /api/events
X-API-Key: <value from .env>
Content-Type: application/json

{
  "type": "network_connection",
  "timestamp": "2026-10-19T09:15:02Z",
  "source": "laptop-sensor-1",
  "src_ip": "192.168.1.25",
  "dst_ip": "192.168.1.1",
  "dst_port": 445,
  "protocol": "tcp"
}
```

---

## Sensor: Scapy collector (`collectors/scapy_collector.py`)

- Sniffs on a chosen interface using Scapy with a BPF filter.
- Reports **initial TCP SYN** packets (SYN set, ACK not set) as `network_connection` events: source IP, destination IP, destination port.
- Reports **DNS query names** as `dns_query` events.
- Never stores or sends payloads.
- Batches events and sends them to the API with retry and backoff; if the API is down, keeps a small bounded buffer and drops the oldest.
- Command-line options: `--iface`, `--api-url`, `--api-key`, `--source-name`, `--list-ifaces`.
- **Windows:** install Npcap (WinPcap API-compatible mode) and run the terminal as Administrator.
- **Linux:** install libpcap and run with `sudo`, or grant `CAP_NET_RAW` to the Python binary.
- Sees only traffic the chosen computer/interface can observe. See `docs/SENSOR_SETUP.md`.

## Optional Zeek forwarder (`sensor/`)

Reads Zeek JSON `conn.log` and `dns.log` and converts them into the same event format. Build this only after the Scapy sensor works.

---

## Tools and examples

- **`tools/send_demo_events.py`** *(to be built by Member 4)*: sends synthetic events (normal traffic plus scenarios: port scan, long DNS label, repeated login failures, suspicious paths) so the whole system can be tested safely without real traffic. Options: `--scenario port_scan`, `--rate`, etc.
- **`examples/webapp_event_reporting.py`** *(to be built by Member 4)*: a small helper that a team-owned web app imports to report `auth_failure` and `http_request` events to the API (non-blocking, with timeouts so the app never slows down if CYBER-MI6 is down).

---

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `API_KEY` | Key required by sensors and apps sending events |
| `JWT_SECRET` | Signs dashboard login tokens (min 32 characters). Empty disables login and every dashboard route |
| `JWT_EXPIRE_MINUTES`, `LOGIN_RATE_LIMIT`, `LOGIN_RATE_WINDOW_SECONDS` | Token lifetime and login attempts allowed per IP per window |
| `DATABASE_PATH` | SQLite file location (default `data/cybermi6.db`) |
| `EVENT_RETENTION_DAYS` | How long events are kept |
| `PORT_SCAN_PORTS`, `PORT_SCAN_WINDOW_SECONDS` | Port scan thresholds |
| `DNS_MAX_LABEL_LENGTH`, `DNS_MIN_ENTROPY` | DNS anomaly thresholds |
| `AUTH_FAIL_COUNT`, `AUTH_FAIL_WINDOW_SECONDS` | Authentication failure thresholds |
| `ALERT_COOLDOWN_SECONDS` | Deduplication window |
| `ALLOWED_ORIGINS` | CORS origins if the dashboard is hosted separately |

Never commit `.env`.

Create the first admin account with `python -m backend.manage create-admin` (password is prompted, never passed on the command line). `python -m backend.manage reset-password <username>` recovers a locked-out account.
