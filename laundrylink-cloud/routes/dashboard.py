import json
import requests as http_requests
from flask import Blueprint, render_template, request, jsonify
from database import (
    get_dashboard_stats, get_transactions_for_owner,
    get_locations_for_owner, get_machines_for_owner,
    get_analytics_stats, get_location_pi_url,
)

dashboard_bp = Blueprint("dashboard", __name__)

# Hardcoded to demo owner for now — in production this would use session auth
DEMO_OWNER_ID = "owner_001"
DEMO_LOCATION_ID = "loc_001"


@dashboard_bp.route("/")
def index():
    stats = get_dashboard_stats(DEMO_OWNER_ID)
    transactions = get_transactions_for_owner(DEMO_OWNER_ID, limit=100)
    locations = get_locations_for_owner(DEMO_OWNER_ID)
    machines = get_machines_for_owner(DEMO_OWNER_ID)
    analytics = get_analytics_stats(DEMO_OWNER_ID)

    return render_template(
        "dashboard.html",
        stats=stats,
        transactions=transactions,
        locations=locations,
        machines=machines,
        analytics=analytics,
        transactions_json=json.dumps(transactions),
        analytics_json=json.dumps(analytics),
        machines_json=json.dumps(machines),
        locations_json=json.dumps(locations),
    )


@dashboard_bp.route("/dashboard/analytics")
def get_analytics():
    """AJAX endpoint for date-range filtered analytics."""
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    analytics = get_analytics_stats(DEMO_OWNER_ID, start_date, end_date)
    return jsonify(analytics)


@dashboard_bp.route("/dashboard/machine/start", methods=["POST"])
def proxy_machine_start():
    """Proxy machine start command from cloud dashboard to the Pi."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    machine_id = data.get("machine_id")
    location_id = data.get("location_id")

    if not machine_id or not location_id:
        return jsonify({"error": "Missing machine_id or location_id"}), 400

    pi_url = get_location_pi_url(location_id)
    if not pi_url:
        return jsonify({"error": "Pi URL not configured for this location"}), 404

    try:
        resp = http_requests.post(f"{pi_url}/machines/{machine_id}/start", timeout=15)
        return jsonify(resp.json()), resp.status_code
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Pi unreachable: {e}"}), 502


@dashboard_bp.route("/dashboard/machine/stop", methods=["POST"])
def proxy_machine_stop():
    """Proxy machine stop command from cloud dashboard to the Pi."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    machine_id = data.get("machine_id")
    location_id = data.get("location_id")

    if not machine_id or not location_id:
        return jsonify({"error": "Missing machine_id or location_id"}), 400

    pi_url = get_location_pi_url(location_id)
    if not pi_url:
        return jsonify({"error": "Pi URL not configured for this location"}), 404

    try:
        resp = http_requests.post(f"{pi_url}/machines/{machine_id}/stop", timeout=15)
        return jsonify(resp.json()), resp.status_code
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Pi unreachable: {e}"}), 502


@dashboard_bp.route("/dashboard/machine/settings", methods=["POST"])
def update_machine_settings():
    """Placeholder — settings are managed via Pi .env file."""
    return jsonify({"status": "ok", "note": "Settings are managed via Pi .env file"}), 200


@dashboard_bp.route("/dashboard/machines/live-status")
def live_machine_status():
    """Proxy to Pi GET /machines to get real-time ESP32 connectivity."""
    pi_url = get_location_pi_url(DEMO_LOCATION_ID)
    if not pi_url:
        return jsonify({"error": "Pi URL not configured"}), 404

    try:
        resp = http_requests.get(f"{pi_url}/machines", timeout=10)
        machines = resp.json()
        # Return a simple map: { "w1": "IDLE", "w2": "OFFLINE", ... }
        status_map = {}
        for m in machines:
            status_map[m["id"]] = m.get("status", "OFFLINE")
        return jsonify(status_map)
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Pi unreachable: {e}"}), 502
