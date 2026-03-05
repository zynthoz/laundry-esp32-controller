import os
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """No-op: tables and functions are managed via supabase_schema.sql in the Supabase SQL Editor."""
    pass


def seed_demo_data():
    """Insert demo owner, API key, and location if they don't exist."""
    existing = supabase.table("owners").select("id").eq("id", "owner_001").execute()
    if existing.data:
        return

    supabase.table("owners").insert({
        "id": "owner_001",
        "name": "Demo Owner",
        "email": "demo@laundrylink.ph",
    }).execute()

    supabase.table("api_keys").insert({
        "key": "sk_test_abc123",
        "owner_id": "owner_001",
        "created_at": "2026-01-01T00:00:00+00:00",
    }).execute()

    supabase.table("locations").insert({
        "id": "loc_001",
        "owner_id": "owner_001",
        "name": "Demo Laundromat",
        "pi_url": "http://localhost:5000",
    }).execute()


def validate_api_key(api_key):
    """Return owner_id if the key is valid, else None."""
    result = supabase.table("api_keys").select("owner_id").eq("key", api_key).execute()
    if result.data:
        return result.data[0]["owner_id"]
    return None


def get_owner_id_for_location(location_id):
    """Return owner_id for a given location, or None."""
    result = supabase.table("locations").select("owner_id").eq("id", location_id).execute()
    if result.data:
        return result.data[0]["owner_id"]
    return None


def insert_transactions(transactions, location_id, synced_at):
    """Bulk insert transactions from a Pi sync. Returns count inserted."""
    rows = []
    for t in transactions:
        rows.append({
            "id": t["id"],
            "location_id": location_id,
            "machine_id": t["machine_id"],
            "amount": t["amount"],
            "status": t["status"],
            "started_at": t["started_at"],
            "ended_at": t.get("ended_at"),
            "synced_at": synced_at,
        })

    if not rows:
        return 0

    # upsert with on_conflict="id" to skip duplicates (no update needed)
    result = supabase.table("transactions").upsert(rows, on_conflict="id").execute()
    return len(result.data) if result.data else 0


def get_transactions_for_owner(owner_id, limit=100):
    """Get recent transactions across all locations owned by this owner."""
    result = supabase.rpc("get_transactions_for_owner", {
        "p_owner_id": owner_id,
        "p_limit": limit,
    }).execute()
    return result.data if result.data else []


def get_locations_for_owner(owner_id):
    result = supabase.table("locations").select("*").eq("owner_id", owner_id).execute()
    return result.data if result.data else []


def upsert_machines(machines, location_id):
    """Insert or update machines from a Pi sync. Returns count upserted."""
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for m in machines:
        rows.append({
            "id": m["id"],
            "location_id": location_id,
            "name": m["name"],
            "type": m["type"],
            "vend_price": m.get("vend_price", 60),
            "status": m.get("status", "IDLE"),
            "pulse_on": m.get("pulse_on", 50),
            "pulse_off": m.get("pulse_off", 50),
            "pulse_count": m.get("pulse_count", 2),
            "updated_at": now,
        })

    if not rows:
        return 0

    result = supabase.table("machines").upsert(rows, on_conflict="id,location_id").execute()
    return len(result.data) if result.data else 0


def get_machines_for_owner(owner_id):
    """Get all machines across all locations owned by this owner."""
    result = supabase.rpc("get_machines_for_owner", {
        "p_owner_id": owner_id,
    }).execute()
    return result.data if result.data else []


def update_machine_status_cloud(machine_id, location_id, status):
    """Update a machine's status in the cloud DB."""
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("machines").update({
        "status": status,
        "updated_at": now,
    }).eq("id", machine_id).eq("location_id", location_id).execute()


def get_dashboard_stats(owner_id):
    """Get summary stats for the owner dashboard."""
    result = supabase.rpc("get_dashboard_stats", {
        "p_owner_id": owner_id,
    }).execute()

    if result.data:
        return result.data
    return {
        "total_revenue": 0,
        "total_transactions": 0,
        "location_count": 0,
        "today_revenue": 0,
    }


def get_analytics_stats(owner_id, start_date=None, end_date=None):
    """Return analytics metrics for a date range."""
    params = {"p_owner_id": owner_id}
    if start_date:
        params["p_start_date"] = start_date
    if end_date:
        params["p_end_date"] = end_date

    result = supabase.rpc("get_analytics_stats", params).execute()

    if result.data:
        return result.data
    return {
        "total_revenue": 0,
        "total_cycles": 0,
        "avg_per_cycle": 0,
        "revenue_by_day": [],
        "cycles_by_day": [],
        "machine_usage": [],
    }


def get_location_pi_url(location_id):
    """Return the Pi URL for a location, or None."""
    result = supabase.table("locations").select("pi_url").eq("id", location_id).execute()
    if result.data and result.data[0].get("pi_url"):
        return result.data[0]["pi_url"]
    return None


def update_location_pi_url(location_id, pi_url):
    """Store the Pi's URL for a location."""
    supabase.table("locations").update({
        "pi_url": pi_url,
    }).eq("id", location_id).execute()
