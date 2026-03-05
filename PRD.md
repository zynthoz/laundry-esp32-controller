# LaundryLink — Product Requirements Document

## Quick Start

```bash
# 1. ESP32 — flash firmware (one-time, from repo root)
pio run --target uploadfs    # upload .env to SPIFFS
pio run --target upload      # flash firmware

# 2. Cloud — start first
cd laundrylink-cloud
cp .env.example .env
pip install -r requirements.txt
python app.py                # runs on http://localhost:4000

# 3. Pi — start second (new terminal)
cd laundrylink-pi
cp .env.example .env         # edit with your machine IPs
pip install -r requirements.txt
python app.py                # runs on http://localhost:5000

# 4. Start a machine
curl -X POST http://localhost:5000/machines/w1/start

# 5. View dashboard
open http://localhost:4000
```

---

## Overview

LaundryLink is a three-tier IoT system for automating commercial laundry machine vending. It replaces physical coin mechanisms with software-controlled pulse signals, enabling cashless operation, remote monitoring, and centralized transaction logging.

**Tiers:**

| Tier | Device | Role |
|------|--------|------|
| 1 | ESP32 (DOIT DevKit V1) | Hardware pulse controller — sends coin-simulating pulses to the machine's optocoupler |
| 2 | Raspberry Pi | Local location manager — operator API, offline-first SQLite, ESP32 orchestration |
| 3 | Cloud Server | Multi-tenant SaaS backend — owner dashboard, transaction aggregation, machine status |

---

## Hardware Context

- **Machine:** LG FH069FDP Commercial Washer (and compatible dryers)
- **ESP32 Board:** DOIT DevKit V1, GPIO32 through PC817 optocoupler
- **Washer config:** 2 pulses, 50ms ON / 50ms OFF (hardware verified)
- **Dryer config:** 4 pulses, 50ms ON / 50ms OFF (hardware verified)
- **Washer vend price:** 60 pesos
- **Dryer vend price:** 20 pesos
- **Coin value:** 5 pesos per pulse

---

## Architecture

```
┌─────────────┐     HTTP      ┌─────────────┐     HTTP      ┌─────────────┐
│   ESP32(s)  │◄─────────────►│ Raspberry Pi │──────────────►│   Cloud     │
│  /control   │  LAN (Wi-Fi)  │  Flask API   │   Internet    │  Flask API  │
│  /status    │               │  SQLite      │               │  SQLite     │
│  GPIO32     │               │  Port 5000   │               │  Port 4000  │
└─────────────┘               └─────────────┘               └─────────────┘
                                    │                              │
                             Operator hits               Owner views
                             POST /machines/w1/start     dashboard at /
```

**Data flow:**
1. Operator sends `POST /machines/<id>/start` to the Pi
2. Pi sends pulse command to the ESP32 (`GET /control?on=50&off=50&count=2`)
3. ESP32 triggers GPIO32 pulses through the optocoupler
4. Pi records the transaction locally in SQLite
5. Pi syncs the transaction to the cloud (every 60s, or immediately after recording)
6. Cloud dashboard displays aggregated data for the owner

---

## Prerequisites

- **Python 3.10+** (for both Pi and Cloud)
- **PlatformIO** (for ESP32 firmware)
- **SQLite** (bundled with Python, no separate install needed)
- **Network:** ESP32 and Pi must be on the same Wi-Fi LAN. Cloud server needs internet access.

---

## Project Structure

```
laundryLink/
├── src/main.cpp                  # ESP32 firmware (PlatformIO/Arduino)
├── platformio.ini                # ESP32 build config
├── laundrylink-pi/               # Raspberry Pi local manager
│   ├── app.py                    # Entry point
│   ├── database.py               # SQLite data layer
│   ├── .env                      # Machine + cloud config (create from .env.example)
│   ├── .env.example              # Template
│   ├── requirements.txt          # Python dependencies
│   ├── routes/
│   │   ├── machines.py           # Machine API endpoints
│   │   └── transactions.py       # Transaction API endpoints
│   └── services/
│       ├── esp32.py              # ESP32 HTTP communication
│       └── sync.py               # Background cloud sync
└── laundrylink-cloud/            # Cloud SaaS backend
    ├── app.py                    # Entry point
    ├── database.py               # SQLite data layer
    ├── .env                      # Server config (create from .env.example)
    ├── .env.example              # Template
    ├── requirements.txt          # Python dependencies
    ├── routes/
    │   ├── api.py                # API endpoints (transactions, machines)
    │   └── dashboard.py          # Dashboard route
    └── templates/
        └── dashboard.html        # Owner dashboard UI
```

---

## Getting Started

### 1. ESP32 Firmware

The ESP32 firmware is a PlatformIO/Arduino project in the repo root.

**Configuration:**

Create a `.env` file on the ESP32's SPIFFS filesystem:

```
WIFI_SSID=YourNetworkName
WIFI_PASSWORD=YourPassword
STATIC_IP=172.20.10.5
GATEWAY=172.20.10.1
SUBNET=255.255.255.0
PRIMARY_DNS=8.8.8.8
```

**Build and upload:**

```bash
# From the repo root (laundryLink/)
pio run --target upload
```

**Upload SPIFFS with .env:**

```bash
pio run --target uploadfs
```

**Verify:**

Once booted, the ESP32 serves a web UI at its static IP (e.g., `http://172.20.10.5`). You can test pulse control manually from the browser.

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Debug web UI with sliders and start button |
| `/control?on=50&off=50&count=2` | GET | Send pulse command. Returns `DONE` when complete. |
| `/status` | GET | Returns `BUSY` (during pulse) or `IDLE` |

---

### 2. Cloud Server

The cloud server should be started **first** so the Pi can sync to it on boot.

```bash
cd laundrylink-cloud

# Create and configure .env
cp .env.example .env
# Edit .env if needed (defaults are fine for local dev)
```

**.env configuration:**

| Key | Default | Description |
|-----|---------|-------------|
| `PORT` | `4000` | Server port |
| `FLASK_ENV` | `development` | `development` binds to 127.0.0.1, `production` binds to 0.0.0.0 |
| `SECRET_KEY` | `change-me-in-production` | Flask session secret |

**Install dependencies and run:**

```bash
pip install -r requirements.txt
python app.py
```

**Expected boot output:**

```
==================================================
  LaundryLink Cloud — SaaS Backend
  Started at 2026-03-05 10:00:00
==================================================

Database initialized.
Demo data seeded (owner_001 / sk_test_abc123 / loc_001).

Dashboard: http://127.0.0.1:4000/
API:       http://127.0.0.1:4000/api/transactions
Mode:      development
```

**Dashboard:** Open `http://localhost:4000` in a browser to see the owner dashboard.

**Demo credentials (seeded on first run):**

| Entity | ID |
|--------|----|
| Owner | `owner_001` |
| API Key | `sk_test_abc123` |
| Location | `loc_001` |

**Cloud API endpoints:**

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | None | Owner dashboard |
| `/api/transactions` | POST | Bearer token | Receive transaction sync from Pi |
| `/api/machines` | POST | Bearer token | Receive machine registry sync from Pi |

---

### 3. Raspberry Pi

```bash
cd laundrylink-pi

# Create and configure .env
cp .env.example .env
# Edit .env with your actual machine IPs and cloud URL
```

**.env configuration:**

| Key | Example | Description |
|-----|---------|-------------|
| `CLOUD_URL` | `http://localhost:4000` | Cloud server URL |
| `API_KEY` | `sk_test_abc123` | Cloud API key for this location |
| `LOCATION_ID` | `loc_001` | This Pi's location identifier |
| `FLASK_ENV` | `development` | `development` allows simulated starts when ESP32 is offline |
| `PORT` | `5000` | Pi server port |

**Adding machines** — define each machine using the `MACHINE_<KEY>_*` pattern:

```env
# Washer
MACHINE_W1_IP=172.20.10.5
MACHINE_W1_NAME=Washer 1
MACHINE_W1_TYPE=washer
MACHINE_W1_PULSE_ON=50
MACHINE_W1_PULSE_OFF=50
MACHINE_W1_PULSE_COUNT=2
MACHINE_W1_VEND_PRICE=60

# Dryer
MACHINE_D1_IP=172.20.10.6
MACHINE_D1_NAME=Dryer 1
MACHINE_D1_TYPE=dryer
MACHINE_D1_PULSE_ON=50
MACHINE_D1_PULSE_OFF=50
MACHINE_D1_PULSE_COUNT=4
MACHINE_D1_VEND_PRICE=20
```

The `<KEY>` (e.g., `W1`, `D1`) must be uppercase alphanumeric. The machine ID in the database becomes the lowercase version (`w1`, `d1`).

**Install dependencies and run:**

```bash
pip install -r requirements.txt
python app.py
```

**Expected boot output:**

```
==================================================
  LaundryLink Pi — Local Manager
  Started at 2026-03-05 10:01:00
==================================================

Location ID:  loc_001
Cloud URL:    http://localhost:4000

Database initialized.

  Machine: Washer 1
    ID:       w1
    Type:     washer
    ESP32 IP: 172.20.10.5
    Pulses:   2x @ 50ms ON / 50ms OFF
    Vend:     60 pesos

  Machine: Dryer 1
    ID:       d1
    Type:     dryer
    ESP32 IP: 172.20.10.6
    Pulses:   4x @ 50ms ON / 50ms OFF
    Vend:     20 pesos

Background sync scheduler started (transactions: 60s, machines: 120s)
Synced 2 machine(s) to cloud
Server: http://127.0.0.1:5000
Mode:   development
```

**Pi API endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /machines` | GET | List all machines with live ESP32 status |
| `POST /machines/<id>/start` | POST | Start a machine (pulse + record transaction) |
| `GET /machines/<id>/status` | GET | Poll a single machine's ESP32 status |
| `GET /transactions` | GET | List recent transactions |

---

## Operating the System

### Starting a Machine

**From the Pi API (typical operator flow):**

```bash
curl -X POST http://localhost:5000/machines/w1/start
```

Response:
```json
{
  "status": "COMPLETED",
  "transaction_id": "a1b2c3d4-...",
  "machine": "Washer 1",
  "amount": 60
}
```

**What happens internally:**
1. Pi looks up machine `w1` in SQLite
2. Pi sends `GET http://172.20.10.5/control?on=50&off=50&count=2` to the ESP32
3. ESP32 fires 2 pulses through GPIO32 via optocoupler
4. Machine receives simulated coin credits and starts its cycle
5. Pi records a transaction (amount=60, status=COMPLETED)
6. Pi updates machine status to BUSY
7. Pi immediately syncs the transaction to the cloud

### Dev Mode (No Hardware)

When `FLASK_ENV=development` and the ESP32 is unreachable, the Pi allows the operation to proceed with status `SIMULATED`. This enables development and testing without physical hardware.

### Cloud Dashboard

The cloud dashboard at `http://localhost:4000` shows:
- **Stats cards** — today's revenue, total revenue, transaction count, location count
- **Machines panel** — all registered machines with status (Idle/Busy/Offline), start toggle switches, countdown timers, and vend prices
- **Transactions table** — recent transactions with time, location, machine, amount, and status

The dashboard auto-refreshes every 60 seconds.

### Background Sync

The Pi runs two background sync jobs:

| Job | Interval | Description |
|-----|----------|-------------|
| Transaction sync | 60 seconds | Pushes unsynced transactions to cloud. Offline-first: if cloud is unreachable, transactions queue locally and retry on the next cycle. |
| Machine sync | 120 seconds | Pushes machine registry (names, types, prices, status) to cloud so the dashboard can display them. Also runs once on startup. |

---

## Adding a New Machine

1. Connect the new ESP32 to the LAN with a static IP
2. Upload the firmware and SPIFFS `.env` to the ESP32
3. Add the machine config block to the Pi's `.env`:
   ```env
   MACHINE_W2_IP=172.20.10.7
   MACHINE_W2_NAME=Washer 2
   MACHINE_W2_TYPE=washer
   MACHINE_W2_PULSE_ON=50
   MACHINE_W2_PULSE_OFF=50
   MACHINE_W2_PULSE_COUNT=2
   MACHINE_W2_VEND_PRICE=60
   ```
4. Restart the Pi: `python app.py`
5. The new machine will auto-register in the Pi database and sync to the cloud within 120 seconds

---

## Adding a New Location

1. On the cloud, add a new location to the `locations` table (or extend `seed_demo_data`)
2. Generate a new API key for the location
3. Set up a new Pi with its own `.env` pointing to the new `LOCATION_ID` and `API_KEY`
4. Each Pi operates independently and syncs to the same cloud

---

## Database Schema

### Pi (`laundrylink-pi/laundrylink.db`)

**machines**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Machine key (e.g., `w1`) |
| name | TEXT | Display name |
| type | TEXT | `washer` or `dryer` |
| esp32_ip | TEXT | ESP32 static IP address |
| pulse_on | INTEGER | Pulse ON duration in ms |
| pulse_off | INTEGER | Pulse OFF duration in ms |
| pulse_count | INTEGER | Number of pulses |
| vend_price | INTEGER | Price in pesos |
| status | TEXT | `IDLE`, `BUSY`, or `OFFLINE` |

**transactions**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| machine_id | TEXT | FK to machines.id |
| amount | INTEGER | Vend price at time of transaction |
| status | TEXT | `COMPLETED` or `SIMULATED` |
| started_at | TEXT | Timestamp |
| ended_at | TEXT | Nullable |
| synced | INTEGER | 0 = unsynced, 1 = synced to cloud |

### Cloud (`laundrylink-cloud/laundrylink-cloud.db`)

**owners**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Owner identifier |
| name | TEXT | Owner name |
| email | TEXT UNIQUE | Owner email |

**api_keys**
| Column | Type | Description |
|--------|------|-------------|
| key | TEXT PK | API key string |
| owner_id | TEXT FK | References owners.id |
| created_at | TEXT | Timestamp |

**locations**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Location identifier |
| owner_id | TEXT FK | References owners.id |
| name | TEXT | Location display name |

**transactions**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID (from Pi) |
| location_id | TEXT FK | References locations.id |
| machine_id | TEXT | Machine key |
| amount | INTEGER | Vend price |
| status | TEXT | `COMPLETED` or `SIMULATED` |
| started_at | TEXT | Timestamp (from Pi) |
| ended_at | TEXT | Nullable |
| synced_at | TEXT | When the cloud received it |

**machines**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Machine key (composite PK with location_id) |
| location_id | TEXT FK | References locations.id |
| name | TEXT | Display name |
| type | TEXT | `washer` or `dryer` |
| vend_price | INTEGER | Price in pesos |
| status | TEXT | `IDLE`, `BUSY`, or `OFFLINE` |
| updated_at | TEXT | Last sync timestamp |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Pi prints `ESP32 unreachable` | ESP32 is off or wrong IP | Check ESP32 power and verify IP in `.env` matches the ESP32's SPIFFS `.env` |
| Pi prints `[QUEUED] Cloud unreachable` | Cloud server is down or URL is wrong | Check `CLOUD_URL` in Pi `.env` and ensure cloud is running |
| Dashboard shows no machines | Pi hasn't synced yet | Wait up to 120s or restart the Pi (syncs on boot) |
| Transaction status is `SIMULATED` | ESP32 was offline during the start command (dev mode only) | Normal in dev mode. In production, the request would return a 502 error instead. |
| Cloud DB missing tables | First run after adding new tables | Delete `laundrylink-cloud.db` and restart — `init_db()` recreates all tables |
| `FATAL: Missing required .env keys` | Pi `.env` is missing `CLOUD_URL`, `API_KEY`, or `LOCATION_ID` | Copy from `.env.example` and fill in values |
| `FATAL: No machines configured` | Pi `.env` has no `MACHINE_*_IP` keys | Add at least one machine block following the naming convention |

---

## Port Reference

| Service | Default Port | Configurable via |
|---------|-------------|-----------------|
| ESP32 web server | 80 | Hardcoded in firmware |
| Raspberry Pi API | 5000 | `PORT` in Pi `.env` |
| Cloud server | 4000 | `PORT` in Cloud `.env` |

---

## Security Notes

- **API keys** are sent as Bearer tokens in the `Authorization` header. In production, use HTTPS.
- **ESP32 endpoints** have no authentication — they are only accessible on the local LAN.
- The Pi `.env` file contains the cloud API key. Do not commit it to version control.
- The cloud `SECRET_KEY` should be changed from the default in production.
- The demo data (`owner_001`, `sk_test_abc123`) is for development only.
