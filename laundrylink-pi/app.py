import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from database import init_db, upsert_machine
from routes.machines import machines_bp
from routes.transactions import transactions_bp
from services.sync import init_sync

load_dotenv()


def validate_env():
    """Validate required .env keys exist. Fail fast with clear errors."""
    required = ["CLOUD_URL", "API_KEY", "LOCATION_ID"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"FATAL: Missing required .env keys: {', '.join(missing)}")
        sys.exit(1)


def load_machines():
    """Parse MACHINE_* keys from .env dynamically. Returns list of machine configs."""
    machine_pattern = re.compile(r"^MACHINE_([A-Z0-9]+)_IP$")
    machines = []

    for key, value in os.environ.items():
        match = machine_pattern.match(key)
        if not match:
            continue

        machine_key = match.group(1)
        prefix = f"MACHINE_{machine_key}_"

        ip = value
        name = os.environ.get(f"{prefix}NAME", machine_key)
        machine_type = os.environ.get(f"{prefix}TYPE", "washer")
        pulse_on = int(os.environ.get(f"{prefix}PULSE_ON", "50"))
        pulse_off = int(os.environ.get(f"{prefix}PULSE_OFF", "50"))
        pulse_count = int(os.environ.get(f"{prefix}PULSE_COUNT", "2"))
        vend_price = int(os.environ.get(f"{prefix}VEND_PRICE", "60"))

        machine_id = machine_key.lower()

        machines.append({
            "id": machine_id,
            "name": name,
            "type": machine_type,
            "esp32_ip": ip,
            "pulse_on": pulse_on,
            "pulse_off": pulse_off,
            "pulse_count": pulse_count,
            "vend_price": vend_price,
        })

    if not machines:
        print("FATAL: No machines configured in .env (expected MACHINE_<ID>_IP keys)")
        sys.exit(1)

    return machines


def create_app():
    app = Flask(__name__)
    app.register_blueprint(machines_bp)
    app.register_blueprint(transactions_bp)
    return app


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"  LaundryLink Pi — Local Manager")
    print(f"  Started at {timestamp}")
    print(f"{'='*50}\n")

    validate_env()

    cloud_url = os.environ["CLOUD_URL"]
    api_key = os.environ["API_KEY"]
    location_id = os.environ["LOCATION_ID"]

    print(f"Location ID:  {location_id}")
    print(f"Cloud URL:    {cloud_url}")
    print()

    init_db()
    print("Database initialized.\n")

    machines = load_machines()
    for m in machines:
        upsert_machine(
            m["id"], m["name"], m["type"], m["esp32_ip"],
            m["pulse_on"], m["pulse_off"], m["pulse_count"], m["vend_price"],
        )
        print(f"  Machine: {m['name']}")
        print(f"    ID:       {m['id']}")
        print(f"    Type:     {m['type']}")
        print(f"    ESP32 IP: {m['esp32_ip']}")
        print(f"    Pulses:   {m['pulse_count']}x @ {m['pulse_on']}ms ON / {m['pulse_off']}ms OFF")
        print(f"    Vend:     {m['vend_price']} pesos")
        print()

    init_sync(cloud_url, api_key, location_id)

    is_dev = os.environ.get("FLASK_ENV", "development") == "development"
    host = "127.0.0.1" if is_dev else "0.0.0.0"
    port = int(os.environ.get("PORT", "5000"))

    print(f"Server: http://{host}:{port}")
    print(f"Mode:   {'development' if is_dev else 'production'}\n")

    app = create_app()
    app.run(host=host, port=port, debug=is_dev)


if __name__ == "__main__":
    main()
