import os
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request
from database import get_all_machines, get_machine, update_machine_status, insert_transaction
from services.esp32 import send_pulse, get_esp32_status
from services.sync import try_immediate_sync

machines_bp = Blueprint("machines", __name__)

IS_DEV = os.environ.get("FLASK_ENV", "development") == "development"


@machines_bp.route("/machines", methods=["GET"])
def list_machines():
    machines = get_all_machines()
    for m in machines:
        m["status"] = get_esp32_status(m["esp32_ip"])
    return jsonify(machines)


@machines_bp.route("/machines/<machine_id>/start", methods=["POST"])
def start_machine(machine_id):
    machine = get_machine(machine_id)
    if not machine:
        return jsonify({"error": "Machine not found"}), 404

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    success, message = send_pulse(
        machine["esp32_ip"],
        machine["pulse_on"],
        machine["pulse_off"],
        machine["pulse_count"],
    )

    if not success and not IS_DEV:
        return jsonify({"error": message, "status": "ERROR"}), 502

    if not success and IS_DEV:
        print(f"[{timestamp}] [SIMULATED] Pulse for {machine['name']} — ESP32 unreachable in dev mode")

    txn_id = str(uuid.uuid4())
    txn_status = "COMPLETED" if success else "SIMULATED"

    insert_transaction(txn_id, machine_id, machine["vend_price"], txn_status, timestamp)
    update_machine_status(machine_id, "BUSY")

    print(f"[{timestamp}] Transaction {txn_id} recorded for {machine['name']} — {txn_status}")

    try_immediate_sync()

    return jsonify({
        "status": txn_status,
        "transaction_id": txn_id,
        "machine": machine["name"],
        "amount": machine["vend_price"],
    })


@machines_bp.route("/machines/<machine_id>/stop", methods=["POST"])
def stop_machine(machine_id):
    machine = get_machine(machine_id)
    if not machine:
        return jsonify({"error": "Machine not found"}), 404

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_machine_status(machine_id, "IDLE")
    print(f"[{timestamp}] Machine {machine['name']} stopped manually")

    return jsonify({"status": "STOPPED", "machine": machine["name"]})


@machines_bp.route("/machines/<machine_id>/status", methods=["GET"])
def machine_status(machine_id):
    machine = get_machine(machine_id)
    if not machine:
        return jsonify({"error": "Machine not found"}), 404

    status = get_esp32_status(machine["esp32_ip"])
    update_machine_status(machine_id, status)

    return jsonify({"id": machine_id, "name": machine["name"], "status": status})
