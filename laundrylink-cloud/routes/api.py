from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
from database import validate_api_key, get_owner_id_for_location, insert_transactions, upsert_machines, update_location_pi_url

api_bp = Blueprint("api", __name__, url_prefix="/api")


def require_api_key(f):
    """Decorator that validates Bearer token and injects owner_id."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401

        api_key = auth_header[7:]
        owner_id = validate_api_key(api_key)
        if not owner_id:
            return jsonify({"error": "Invalid API key"}), 401

        kwargs["owner_id"] = owner_id
        return f(*args, **kwargs)
    return decorated


@api_bp.route("/transactions", methods=["POST"])
@require_api_key
def receive_transactions(owner_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    location_id = data.get("location_id")
    transactions = data.get("transactions")

    if not location_id:
        return jsonify({"error": "Missing location_id"}), 400
    if not transactions or not isinstance(transactions, list):
        return jsonify({"error": "Missing or invalid transactions array"}), 400

    # Verify the location belongs to this API key's owner
    location_owner = get_owner_id_for_location(location_id)
    if not location_owner:
        return jsonify({"error": f"Location '{location_id}' not found"}), 404
    if location_owner != owner_id:
        return jsonify({"error": "API key does not have access to this location"}), 403

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = insert_transactions(transactions, location_id, synced_at)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Received {len(transactions)} transaction(s) from {location_id}, inserted {inserted} new")

    return jsonify({
        "status": "ok",
        "received": len(transactions),
        "inserted": inserted,
    }), 201


@api_bp.route("/machines", methods=["POST"])
@require_api_key
def receive_machines(owner_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    location_id = data.get("location_id")
    machines = data.get("machines")

    if not location_id:
        return jsonify({"error": "Missing location_id"}), 400
    if not machines or not isinstance(machines, list):
        return jsonify({"error": "Missing or invalid machines array"}), 400

    location_owner = get_owner_id_for_location(location_id)
    if not location_owner:
        return jsonify({"error": f"Location '{location_id}' not found"}), 404
    if location_owner != owner_id:
        return jsonify({"error": "API key does not have access to this location"}), 403

    count = upsert_machines(machines, location_id)

    # Store Pi URL if provided in payload
    pi_url = data.get("pi_url")
    if pi_url:
        update_location_pi_url(location_id, pi_url)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Synced {count} machine(s) from {location_id}")

    return jsonify({"status": "ok", "synced": count}), 200
