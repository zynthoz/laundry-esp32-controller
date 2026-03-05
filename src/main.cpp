#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

#include <FS.h>
#include <SPIFFS.h>
#include <string>

// wifi ssid and password loaded from .env
std::string ssid;
std::string password;

// Static IP config loaded from .env
IPAddress local_IP;
IPAddress gateway;
IPAddress subnet;
IPAddress primaryDNS;
#define SW_PIN 32

// ─── # of Pulses Per Machine ─────────
// Dryer - 4 pulses
// Washer - 2 pulses
// ─────────────────────────────────────

// ─── Pulse Config (overridden by UI) ─
int pulseOnMs  = 500;
int pulseOffMs = 500;
int numPulses  = 3;
// ─────────────────────────────────────

void activateSwitch();

WebServer server(80);
bool machineState = false;

const char* htmlPage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>LaundryLink</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0d0d0f;
      --card: #141418;
      --border: #2a2a32;
      --accent: #00e5ff;
      --accent2: #7c3aed;
      --text: #e8e8f0;
      --muted: #555568;
      --on: #00c853;
      --off: #ff1744;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background-image: radial-gradient(ellipse at 20% 50%, rgba(124,58,237,0.08) 0%, transparent 60%),
                        radial-gradient(ellipse at 80% 20%, rgba(0,229,255,0.06) 0%, transparent 50%);
    }

    .header {
      text-align: center;
      margin-bottom: 32px;
    }
    .header h1 {
      font-family: 'Space Mono', monospace;
      font-size: 2.2em;
      letter-spacing: -1px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header p {
      color: var(--muted);
      font-size: 0.85em;
      margin-top: 6px;
      font-family: 'Space Mono', monospace;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 28px;
      width: 100%;
      max-width: 380px;
      box-shadow: 0 0 40px rgba(0,0,0,0.4);
    }

    /* ── Status ── */
    .status-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 28px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }
    .status-label {
      font-size: 0.78em;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 1.5px;
      font-family: 'Space Mono', monospace;
    }
    .status-badge {
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 0.85em;
      font-weight: 700;
      font-family: 'Space Mono', monospace;
      letter-spacing: 1px;
    }
    .badge-on  { background: rgba(0,200,83,0.12);  color: var(--on);  border: 1px solid rgba(0,200,83,0.3); }
    .badge-off { background: rgba(255,23,68,0.10); color: var(--off); border: 1px solid rgba(255,23,68,0.25); }
    .badge-sending { background: rgba(0,229,255,0.10); color: var(--accent); border: 1px solid rgba(0,229,255,0.25); }

    /* ── Sliders ── */
    .sliders { margin-bottom: 24px; }
    .slider-row {
      margin-bottom: 18px;
    }
    .slider-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .slider-name {
      font-size: 0.78em;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--muted);
      font-family: 'Space Mono', monospace;
    }
    .slider-value {
      font-size: 0.9em;
      font-family: 'Space Mono', monospace;
      color: var(--accent);
      font-weight: 700;
      min-width: 60px;
      text-align: right;
    }
    input[type=range] {
      width: 100%;
      height: 4px;
      -webkit-appearance: none;
      appearance: none;
      background: var(--border);
      border-radius: 2px;
      outline: none;
      cursor: pointer;
    }
    input[type=range]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      cursor: pointer;
      box-shadow: 0 0 8px rgba(0,229,255,0.4);
      transition: transform 0.15s;
    }
    input[type=range]::-webkit-slider-thumb:hover {
      transform: scale(1.2);
    }
    input[type=range]::-moz-range-thumb {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      cursor: pointer;
      border: none;
    }

    /* ── Divider ── */
    .divider {
      height: 1px;
      background: var(--border);
      margin: 20px 0;
    }

    /* ── Button ── */
    .btn-start {
      display: block;
      width: 100%;
      padding: 18px;
      font-size: 1em;
      font-weight: 700;
      font-family: 'Space Mono', monospace;
      letter-spacing: 2px;
      text-transform: uppercase;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      color: #0d0d0f;
      transition: opacity 0.2s, transform 0.15s;
      position: relative;
      overflow: hidden;
    }
    .btn-start:hover  { opacity: 0.9; transform: translateY(-1px); }
    .btn-start:active { transform: translateY(1px); opacity: 0.8; }
    .btn-start:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

    /* ── Config summary ── */
    .config-summary {
      margin-top: 20px;
      padding: 14px;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--border);
      border-radius: 10px;
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      text-align: center;
    }
    .config-item span:first-child {
      display: block;
      font-size: 0.65em;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      font-family: 'Space Mono', monospace;
      margin-bottom: 4px;
    }
    .config-item span:last-child {
      font-size: 1em;
      font-weight: 700;
      font-family: 'Space Mono', monospace;
      color: var(--text);
    }

    .footer {
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.75em;
      font-family: 'Space Mono', monospace;
      letter-spacing: 1px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>LaundryLink</h1>
    <p>Washing Machine Controller</p>
  </div>

  <div class="card">
    <div class="status-row">
      <span class="status-label">Status</span>
      <span class="status-badge badge-off" id="badge">IDLE</span>
    </div>

    <div class="sliders">

      <div class="slider-row">
        <div class="slider-header">
          <span class="slider-name">Pulse ON Duration</span>
          <span class="slider-value" id="onVal">500ms</span>
        </div>
        <input type="range" id="pulseOn" min="50" max="3000" step="50" value="500"
          oninput="document.getElementById('onVal').textContent = this.value + 'ms'; updateSummary()">
      </div>

      <div class="slider-row">
        <div class="slider-header">
          <span class="slider-name">Pulse OFF Duration</span>
          <span class="slider-value" id="offVal">500ms</span>
        </div>
        <input type="range" id="pulseOff" min="50" max="3000" step="50" value="500"
          oninput="document.getElementById('offVal').textContent = this.value + 'ms'; updateSummary()">
      </div>

      <div class="slider-row">
        <div class="slider-header">
          <span class="slider-name">Number of Pulses</span>
          <span class="slider-value" id="pulseCountVal">2</span>
        </div>
        <input type="range" id="pulseCount" min="1" max="20" step="1" value="2"
          oninput="document.getElementById('pulseCountVal').textContent = this.value; updateSummary()">
      </div>

    </div>

    <div class="config-summary">
      <div class="config-item">
        <span>ON</span>
        <span id="sumOn">500ms</span>
      </div>
      <div class="config-item">
        <span>OFF</span>
        <span id="sumOff">500ms</span>
      </div>
      <div class="config-item">
        <span>PULSES</span>
        <span id="sumCount">2</span>
      </div>
    </div>

    <div class="divider"></div>

    <button class="btn-start" id="startBtn" onclick="startMachine()">
      ▶ START MACHINE
    </button>
  </div>

  <div class="footer">LaundryLink v1.0 — Debug Mode</div>

  <script>
    function updateSummary() {
      document.getElementById('sumOn').textContent    = document.getElementById('pulseOn').value + 'ms';
      document.getElementById('sumOff').textContent   = document.getElementById('pulseOff').value + 'ms';
      document.getElementById('sumCount').textContent = document.getElementById('pulseCount').value;
    }

    function startMachine() {
      const on    = document.getElementById('pulseOn').value;
      const off   = document.getElementById('pulseOff').value;
      const count = document.getElementById('pulseCount').value;

      const btn  = document.getElementById('startBtn');
      const badge = document.getElementById('badge');

      btn.disabled = true;
      badge.textContent = 'SENDING';
      badge.className   = 'status-badge badge-sending';

      fetch(`/control?on=${on}&off=${off}&count=${count}`)
        .then(r => r.text())
        .then(state => {
          badge.textContent = 'DONE';
          badge.className   = 'status-badge badge-on';
          btn.disabled = false;
          setTimeout(() => {
            badge.textContent = 'IDLE';
            badge.className   = 'status-badge badge-off';
          }, 3000);
        })
        .catch(() => {
          badge.textContent = 'ERROR';
          badge.className   = 'status-badge badge-off';
          btn.disabled = false;
        });
    }

    function getStatus() {
      fetch('/status')
        .then(r => r.text())
        .then(s => {
          if (s !== 'BUSY') {
            document.getElementById('badge').textContent = 'IDLE';
            document.getElementById('badge').className   = 'status-badge badge-off';
          }
        })
        .catch(() => {});
    }

    setInterval(getStatus, 3000);
    updateSummary();
  </script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleControl() {
  if (server.hasArg("on"))    pulseOnMs  = server.arg("on").toInt();
  if (server.hasArg("off"))   pulseOffMs = server.arg("off").toInt();
  if (server.hasArg("count")) numPulses  = server.arg("count").toInt();

  Serial.printf("Config → ON:%dms  OFF:%dms  PULSES:%d\n", pulseOnMs, pulseOffMs, numPulses);

  machineState = true;
  activateSwitch();
  machineState = false;

  server.send(200, "text/plain", "DONE");
}

void handleStatus() {
  server.send(200, "text/plain", machineState ? "BUSY" : "IDLE");
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

void setup() {

  delay(8000);
  Serial.begin(115200);
  Serial.println("Booting...");

  pinMode(SW_PIN, OUTPUT);
  digitalWrite(SW_PIN, LOW);

  if (!SPIFFS.begin(true)) {
    Serial.println("Failed to mount SPIFFS");
    return;
  }
  File envFile = SPIFFS.open("/.env", "r");
  if (!envFile) {
    Serial.println("Failed to open .env file");
    return;
  }
  String envContent = envFile.readString();
  envFile.close();

  int idx;
  idx = envContent.indexOf("WIFI_SSID=");
  if (idx != -1) ssid = envContent.substring(idx + 10, envContent.indexOf('\n', idx)).c_str();
  idx = envContent.indexOf("WIFI_PASSWORD=");
  if (idx != -1) password = envContent.substring(idx + 14, envContent.indexOf('\n', idx)).c_str();
  idx = envContent.indexOf("STATIC_IP=");
  if (idx != -1) {
    String ip = envContent.substring(idx + 10, envContent.indexOf('\n', idx));
    int ip1, ip2, ip3, ip4;
    sscanf(ip.c_str(), "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4);
    local_IP = IPAddress(ip1, ip2, ip3, ip4);
  }
  idx = envContent.indexOf("GATEWAY=");
  if (idx != -1) {
    String ip = envContent.substring(idx + 8, envContent.indexOf('\n', idx));
    int ip1, ip2, ip3, ip4;
    sscanf(ip.c_str(), "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4);
    gateway = IPAddress(ip1, ip2, ip3, ip4);
  }
  idx = envContent.indexOf("SUBNET=");
  if (idx != -1) {
    String ip = envContent.substring(idx + 7, envContent.indexOf('\n', idx));
    int ip1, ip2, ip3, ip4;
    sscanf(ip.c_str(), "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4);
    subnet = IPAddress(ip1, ip2, ip3, ip4);
  }
  idx = envContent.indexOf("PRIMARY_DNS=");
  if (idx != -1) {
    String ip = envContent.substring(idx + 12, envContent.indexOf('\n', idx));
    int ip1, ip2, ip3, ip4;
    sscanf(ip.c_str(), "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4);
    primaryDNS = IPAddress(ip1, ip2, ip3, ip4);
  }

  WiFi.mode(WIFI_STA);
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS)) {
    Serial.println("Static IP Failed!");
  }

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid.c_str(), password.c_str());
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

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

void activateSwitch() {
  Serial.printf("Sending %d pulses — ON:%dms OFF:%dms\n", numPulses, pulseOnMs, pulseOffMs);
  for (int i = 0; i < numPulses; i++) {
    digitalWrite(SW_PIN, HIGH);
    delay(pulseOnMs);
    digitalWrite(SW_PIN, LOW);
    delay(pulseOffMs);
    Serial.printf("Pulse %d/%d sent\n", i + 1, numPulses);
  }
  Serial.println("All pulses sent.");
}