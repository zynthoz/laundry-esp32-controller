import requests
from datetime import datetime


def send_pulse(esp32_ip, pulse_on, pulse_off, pulse_count):
    """Send pulse command to ESP32 and return (success, message)."""
    url = f"http://{esp32_ip}/control?on={pulse_on}&off={pulse_off}&count={pulse_count}"
    timeout = ((pulse_on + pulse_off) * pulse_count / 1000) + 5

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Sending pulse to {esp32_ip}: on={pulse_on} off={pulse_off} count={pulse_count} (timeout={timeout:.1f}s)")

    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.text.strip() == "DONE":
            print(f"[{timestamp}] Pulse complete from {esp32_ip}: DONE")
            return True, "DONE"
        else:
            print(f"[{timestamp}] Unexpected response from {esp32_ip}: {resp.status_code} {resp.text}")
            return False, f"Unexpected response: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        print(f"[{timestamp}] ESP32 unreachable at {esp32_ip}: {e}")
        return False, f"ESP32 unreachable: {e}"


def get_esp32_status(esp32_ip):
    """Poll ESP32 for current status. Returns 'BUSY', 'IDLE', or 'OFFLINE'."""
    url = f"http://{esp32_ip}/status"
    try:
        resp = requests.get(url, timeout=3)
        status = resp.text.strip()
        if status in ("BUSY", "IDLE"):
            return status
        return "IDLE"
    except requests.exceptions.RequestException:
        return "OFFLINE"
