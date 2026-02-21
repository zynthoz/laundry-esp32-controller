#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

const char* ssid     = "pi-test";
const char* password = "12345678";
#define SW_PIN 32

WebServer server(80);
bool machineState = false;

const char* htmlPage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>LaundryLink</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Arial, sans-serif;
      background: #1a1a2e;
      color: white;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    h1 { font-size: 2.5em; margin-bottom: 5px; }
    .subtitle { color: #888; margin-bottom: 40px; font-size: 0.9em; }
    .card {
      background: #16213e;
      border-radius: 20px;
      padding: 40px;
      width: 100%;
      max-width: 350px;
      text-align: center;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .status-label { font-size: 0.9em; color: #888; margin-bottom: 10px; }
    .status-badge {
      display: inline-block;
      padding: 8px 24px;
      border-radius: 20px;
      font-size: 1.2em;
      font-weight: bold;
      margin-bottom: 30px;
    }
    .badge-on  { background: #1a472a; color: #4CAF50; }
    .badge-off { background: #4a1a1a; color: #f44336; }
    .btn {
      display: block;
      width: 100%;
      padding: 18px;
      font-size: 1.1em;
      font-weight: bold;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      margin-bottom: 12px;
      transition: opacity 0.2s;
    }
    .btn:hover  { opacity: 0.85; }
    .btn:active { opacity: 0.7; }
    .btn-on  { background: #4CAF50; color: white; }
    .btn-off { background: #f44336; color: white; }
    .footer { margin-top: 30px; color: #444; font-size: 0.8em; }
  </style>
</head>
<body>
  <h1>LaundryLink</h1>
  <p class="subtitle">Washing Machine Controller</p>
  <div class="card">
    <div class="status-label">Current Status</div>
    <div class="status-badge badge-off" id="badge">Loading...</div>
    <button class="btn btn-on"  onclick="control('on')">Turn ON</button>
    <button class="btn btn-off" onclick="control('off')">Turn OFF</button>
  </div>
  <div class="footer">LaundryLink v1.0</div>
  <script>
    function updateBadge(state) {
      const badge = document.getElementById('badge');
      if (state === 'ON') {
        badge.textContent = 'ON';
        badge.className = 'status-badge badge-on';
      } else {
        badge.textContent = 'OFF';
        badge.className = 'status-badge badge-off';
      }
    }
    function control(action) {
      fetch('/control?action=' + action)
        .then(r => r.text())
        .then(state => updateBadge(state))
        .catch(() => updateBadge('ERROR'));
    }
    function getStatus() {
      fetch('/status')
        .then(r => r.text())
        .then(state => updateBadge(state))
        .catch(() => updateBadge('ERROR'));
    }
    setInterval(getStatus, 3000);
    getStatus();
  </script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleControl() {
  if (server.hasArg("action")) {
    String action = server.arg("action");
    if (action == "on") {
      machineState = true;
      digitalWrite(SW_PIN, HIGH);
      Serial.println("Machine turned ON");
      server.send(200, "text/plain", "ON");
    }
    else if (action == "off") {
      machineState = false;
      digitalWrite(SW_PIN, LOW);
      Serial.println("Machine turned OFF");
      server.send(200, "text/plain", "OFF");
    }
    else {
      server.send(400, "text/plain", "Invalid action");
    }
  } else {
    server.send(400, "text/plain", "Missing action");
  }
}

void handleStatus() {
  server.send(200, "text/plain", machineState ? "ON" : "OFF");
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

void setup() {
  Serial.begin(115200);
    Serial.begin(9600);
  Serial.println("Booting...");

  pinMode(SW_PIN, OUTPUT);
  digitalWrite(SW_PIN, LOW);

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print("nigga");
  }

  Serial.println("");
  Serial.println("WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("Open that IP in your browser");

  server.on("/",        handleRoot);
  server.on("/control", handleControl);
  server.on("/status",  handleStatus);
  server.onNotFound(    handleNotFound);

  server.begin();
  Serial.println("Server started!");
}

void loop() {
  server.handleClient();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.reconnect();
    delay(5000);
  }
}