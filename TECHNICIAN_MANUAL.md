# LaundryLink — Technician Setup Manual

## System Overview

LaundryLink has **three components** that work together:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   ESP32      │◄────────│  Pi Server   │────────►│ Cloud Server │
│ (per machine)│  HTTP   │ (per site)   │  HTTP   │ (Supabase)   │
│ Port: 80     │ control │ Port: 5000   │  sync   │ Port: 4000   │
└──────────────┘         └──────────────┘         └──────────────┘
```

| Component | What it does | Runs on |
|---|---|---|
| **ESP32** | Controls a physical machine (washer/dryer) via relay pulses | ESP32 board (one per machine) |
| **Pi Server** | Receives vend commands, talks to ESP32s, stores transactions locally, syncs to cloud | PC or Raspberry Pi (one per location) |
| **Cloud Server** | Receives synced data from all Pi locations, stores in Supabase, serves dashboard | PC (local dev) |

---

## Prerequisites

Before you begin, make sure you have:

- [ ] Python 3.10+ installed
- [ ] PlatformIO (VS Code extension) installed
- [ ] A free **Supabase** project at https://supabase.com
- [ ] ESP32 board(s) wired to relay(s) on **GPIO 32**
- [ ] All devices on the **same Wi-Fi network**

---

## STEP 1 — Set Up Supabase (Database)

1. Go to https://supabase.com → create a new project (or use an existing one).
2. Open the **SQL Editor** in the Supabase dashboard.
3. Copy the entire contents of `laundrylink-cloud/supabase_schema.sql` and run it.
   This creates these tables:

   | Table | Purpose |
   |---|---|
   | `owners` | Laundromat owner accounts |
   | `api_keys` | API keys linked to owners (used by Pi for auth) |
   | `locations` | Physical laundromat sites |
   | `transactions` | Every vend cycle synced from Pi |
   | `machines` | Machine registry synced from Pi |

4. Go to **Project Settings → API** and copy:
   - **Project URL** (e.g., `https://xxxxxx.supabase.co`)
   - **service_role key** (the secret one, NOT the anon key)

---

## STEP 2 — Configure & Start the Cloud Server

### 2.1 — Create the `.env` file

```
cd laundrylink-cloud
```

Create a file named `.env` with:

```env
# Server
PORT=4000
FLASK_ENV=development
SECRET_KEY=change-me-in-production

# Supabase (paste your values from Step 1)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 2.2 — Install dependencies

```
pip install -r requirements.txt
```

### 2.3 — Start the cloud server

```
python app.py
```

You should see:

```
LaundryLink Cloud — SaaS Backend
Supabase database connected.
Demo data seeded (owner_001 / sk_test_abc123 / loc_001).
Dashboard: http://127.0.0.1:4000/
```

On first start, **demo data is automatically seeded** into Supabase:

| What | Value |
|---|---|
| Owner | `owner_001` / "Demo Owner" |
| API Key | `sk_test_abc123` |
| Location | `loc_001` / "Demo Laundromat" |

> **Keep this terminal running.** The Pi server needs it.

---

## STEP 3 — Flash the ESP32(s)

Each machine (washer or dryer) needs one ESP32.

### 3.1 — Create the ESP32 `.env` file

In the project root, create a file at `data/.env` (this gets uploaded to SPIFFS):

```env
WIFI_SSID=YourWiFiName
WIFI_PASSWORD=YourWiFiPassword
STATIC_IP=172.20.10.5
GATEWAY=172.20.10.1
SUBNET=255.255.255.0
PRIMARY_DNS=8.8.8.8
```

> **Each ESP32 must have a unique STATIC_IP** so the Pi can talk to it.  
> Example: Washer 1 = `172.20.10.5`, Dryer 1 = `172.20.10.6`, etc.

### 3.2 — Upload filesystem & flash firmware

1. Connect the ESP32 via USB.
2. In VS Code with PlatformIO:
   - Run **"Upload Filesystem Image"** (uploads `.env` to SPIFFS)
   - Run **"Upload"** (flashes the firmware)
3. Open the Serial Monitor (115200 baud) — you should see:

```
WiFi Connected!
IP Address: 172.20.10.5
Server started!
```

### 3.3 — Verify

Open a browser to `http://172.20.10.5` — you should see the LaundryLink control page. Press "START MACHINE" to test the relay.

> Repeat Steps 3.1–3.3 for each machine, changing `STATIC_IP` each time.

---

## STEP 4 — Configure & Start the Pi Server

### 4.1 — Create the `.env` file

```
cd laundrylink-pi
```

Create a file named `.env`:

```env
# Cloud connection
CLOUD_URL=http://localhost:4000
API_KEY=sk_test_abc123

# Location
LOCATION_ID=loc_001

# Flask
FLASK_ENV=development
PORT=5000

# Machine config — one block per machine
# Format: MACHINE_<ID>_<PROPERTY>
# ID can be anything (W1, W2, D1, etc.)

MACHINE_W1_IP=172.20.10.5
MACHINE_W1_NAME=Washer 1
MACHINE_W1_TYPE=washer
MACHINE_W1_PULSE_ON=50
MACHINE_W1_PULSE_OFF=50
MACHINE_W1_PULSE_COUNT=2
MACHINE_W1_VEND_PRICE=60

MACHINE_D1_IP=172.20.10.6
MACHINE_D1_NAME=Dryer 1
MACHINE_D1_TYPE=dryer
MACHINE_D1_PULSE_ON=50
MACHINE_D1_PULSE_OFF=50
MACHINE_D1_PULSE_COUNT=4
MACHINE_D1_VEND_PRICE=20
```

#### Machine config explained:

| Property | Meaning | Example |
|---|---|---|
| `MACHINE_W1_IP` | Static IP of the ESP32 for this machine | `172.20.10.5` |
| `MACHINE_W1_NAME` | Human-readable name | `Washer 1` |
| `MACHINE_W1_TYPE` | `washer` or `dryer` | `washer` |
| `MACHINE_W1_PULSE_ON` | Relay ON duration in milliseconds | `50` |
| `MACHINE_W1_PULSE_OFF` | Relay OFF duration in milliseconds | `50` |
| `MACHINE_W1_PULSE_COUNT` | Number of relay pulses to send | `2` |
| `MACHINE_W1_VEND_PRICE` | Price per cycle in pesos | `60` |

> **To add more machines**, add another block with a different ID:
> ```
> MACHINE_W2_IP=172.20.10.7
> MACHINE_W2_NAME=Washer 2
> MACHINE_W2_TYPE=washer
> MACHINE_W2_PULSE_ON=50
> MACHINE_W2_PULSE_OFF=50
> MACHINE_W2_PULSE_COUNT=2
> MACHINE_W2_VEND_PRICE=60
> ```

### 4.2 — Install dependencies

```
pip install -r requirements.txt
```

### 4.3 — Start the Pi server

```
python app.py
```

You should see:

```
LaundryLink Pi — Local Manager
Location ID:  loc_001
Cloud URL:    http://localhost:4000

Database initialized.

  Machine: Washer 1
    ID:       w1
    Type:     washer
    ESP32 IP: 172.20.10.5
    Pulses:   2x @ 50ms ON / 50ms OFF
    Vend:     60 pesos

Background sync scheduler started (transactions: 60s, machines: 120s)
Server: http://127.0.0.1:5000
```

---

## STEP 5 — Verify the System

### Test a vend cycle

Send a POST request to the Pi to start a machine:

```
curl -X POST http://localhost:5000/machines/w1/start
```

Expected response:

```json
{
  "status": "COMPLETED",
  "transaction_id": "...",
  "machine": "Washer 1",
  "amount": 60
}
```

### Check machine status

```
curl http://localhost:5000/machines
```

### Check the cloud dashboard

Open `http://localhost:4000/` in a browser. After up to 60 seconds (the sync interval), you should see the transaction appear.

---

## STEP 6 — Creating & Assigning Users (Owners)

There is **no self-service registration UI** yet. To add a new owner, you need to insert rows into Supabase manually.

### 6.1 — Create a new owner

Go to **Supabase → SQL Editor** and run:

```sql
-- 1. Create the owner
INSERT INTO owners (id, name, email)
VALUES ('owner_002', 'Juan Dela Cruz', 'juan@example.com');

-- 2. Create an API key for them
INSERT INTO api_keys (key, owner_id, created_at)
VALUES ('sk_live_juans_key_here', 'owner_002', NOW());

-- 3. Create their location
INSERT INTO locations (id, owner_id, name, pi_url)
VALUES ('loc_002', 'owner_002', 'Juans Laundromat', 'http://192.168.1.50:5000');
```

### 6.2 — Configure their Pi

On the new location's Pi, create `.env`:

```env
CLOUD_URL=http://localhost:4000
API_KEY=sk_live_juans_key_here
LOCATION_ID=loc_002
PORT=5000
FLASK_ENV=development

MACHINE_W1_IP=192.168.1.100
MACHINE_W1_NAME=Washer 1
MACHINE_W1_TYPE=washer
MACHINE_W1_PULSE_ON=50
MACHINE_W1_PULSE_OFF=50
MACHINE_W1_PULSE_COUNT=2
MACHINE_W1_VEND_PRICE=60
```

> The `API_KEY` and `LOCATION_ID` must match what you inserted in Supabase.  
> The cloud verifies that the API key's owner actually owns the location — mismatches get a 403 error.

### How auth works (summary):

```
Pi sends:  API_KEY=sk_live_juans_key_here  +  LOCATION_ID=loc_002
                    │                                   │
Cloud checks:       │                                   │
   api_keys table:  sk_live_juans_key_here → owner_002  │
   locations table: loc_002 → owner_002 ─────────────── ✓ match → allowed
```

---

## Quick Reference: Startup Order

Always start services in this order:

| Order | Component | Command | Port |
|---|---|---|---|
| 1 | Cloud server | `cd laundrylink-cloud && python app.py` | 4000 |
| 2 | ESP32(s) | Power on (auto-connect to Wi-Fi) | 80 |
| 3 | Pi server | `cd laundrylink-pi && python app.py` | 5000 |

---

## Quick Reference: Pi API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/machines` | List all machines and their live status |
| `POST` | `/machines/<id>/start` | Start a vend cycle (sends pulse to ESP32) |
| `POST` | `/machines/<id>/stop` | Manually mark machine as IDLE |
| `GET` | `/machines/<id>/status` | Get single machine status |
| `GET` | `/transactions` | List recent transactions |

---

## Quick Reference: Cloud API Endpoints

| Method | Endpoint | Auth | What it does |
|---|---|---|---|
| `POST` | `/api/transactions` | Bearer API_KEY | Receive synced transactions from Pi |
| `POST` | `/api/machines` | Bearer API_KEY | Receive machine registry from Pi |
| `GET` | `/` | None | Dashboard (web UI) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Pi says `FATAL: Missing required .env keys` | Check `.env` has `CLOUD_URL`, `API_KEY`, `LOCATION_ID` |
| Pi says `Cloud unreachable` | Make sure the cloud server is running first on port 4000 |
| Pi says `HTTP 401` | API key in Pi `.env` doesn't match any row in Supabase `api_keys` table |
| Pi says `HTTP 403` | The API key's owner doesn't own the location ID — check Supabase |
| ESP32 won't connect | Verify `WIFI_SSID`, `WIFI_PASSWORD`, and `STATIC_IP` in the ESP32 `data/.env` |
| Machine shows OFFLINE | ESP32 is not powered or not on the same network — ping its IP |
| No data on dashboard | Wait 60s for sync, or check cloud terminal for errors |
| `SIMULATED` transactions | ESP32 unreachable but dev mode allows it — machine still records the transaction |
