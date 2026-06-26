"""Cliente WebSocket para comunicación con el ESP32 de ALINA.

Uso:
    client = ALINAWebSocket(esp_ip="192.168.1.XX")
    client.connect()
    client.start_session()
    client.stop_session()
    client.disconnect()

Callbacks disponibles:
    on_status(data)       → {"calibrated": bool, "imu_t1": bool, ...}
    on_posture(data)      → {"t1_pitch": float, "t1_roll": float, ...}
    on_alert(data)        → {"source": "T12", "count": int}
    on_session_end(data)  → {"duracion_min": float, "alertas_hapticas": int, ...}
    on_session_status(data) → {"state": "running"|"paused"|"idle"}
    on_connect()
    on_disconnect()
"""

from __future__ import annotations
import json
import threading
import websocket  # pip install websocket-client


class ALINAWebSocket:
    PORT = 81

    def __init__(self, esp_ip: str = ""):
        self.esp_ip   = esp_ip
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_status: dict | None = None

        # Callbacks — asignar desde la UI
        self.on_status:         callable = None
        self.on_posture:        callable = None
        self.on_alert:          callable = None
        self.on_session_end:    callable = None
        self.on_session_status: callable = None
        self.on_connect:        callable = None
        self.on_disconnect:     callable = None

    # ── Conexión ──────────────────────────────────────────────────────────────

    def connect(self, esp_ip: str | None = None):
        """Conectar al WebSocket del ESP32."""
        if esp_ip:
            self.esp_ip = esp_ip
        if not self.esp_ip:
            raise ValueError("esp_ip no configurado")

        url = f"ws://{self.esp_ip}:{self.PORT}"
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            #kwargs={"reconnect": 5},   # reintentar cada 5s si se desconecta
            kwargs={
                "reconnect": 5,
                "ping_interval": 5,   # mandar ping cada 5s
                "ping_timeout": 3,    # si no responde en 3s, cerrar
            },
            daemon=True,
        )
        self._thread.start()

    def disconnect(self):
        if self._ws:
            self._ws.close()

    # ── Enviar comandos ───────────────────────────────────────────────────────

    def _send(self, cmd: dict):
        if self._ws and self.connected:
            self._ws.send(json.dumps(cmd))

    def start_session(self):
        self._send({"cmd": "start_session"})

    def pause_session(self):
        self._send({"cmd": "pause_session"})

    def resume_session(self):
        self._send({"cmd": "resume_session"})

    def stop_session(self):
        self._send({"cmd": "stop_session"})

    def calibrate(self):
        self._send({"cmd": "calibrate"})

    def set_config(self, device_name: str | None = None, haptic_intensity: int | None = None):
        payload: dict = {"cmd": "set_config"}
        if device_name is not None:
            payload["device_name"] = device_name
        if haptic_intensity is not None:
            payload["haptic_duration_ms"] = haptic_intensity
        self._send(payload)

    def test_vibration(self, duration_ms: int):
        """Disparar vibración de prueba con la duración especificada."""
        self._send({"cmd": "test_vibration", "haptic_duration_ms": duration_ms})

    def wifi_reset(self):
        self._send({"cmd": "wifi_reset"})

    # ── Handlers internos ─────────────────────────────────────────────────────

    def _on_open(self, ws):
        self.connected = True
        if self.on_connect:
            self.on_connect()

    def _on_close(self, ws, code, msg):
        print(f"[WS CLOSE] code={code} msg={msg}")   # ← temporal
        self.connected = False
        if self.on_disconnect:
            self.on_disconnect()

    def _on_error(self, ws, error):
        print(f"[WS] Error: {error}") # temporal
        # Si la conexión se cayó (ej. ping/pong timeout), notificar desconexión
        if self.connected:
            self.connected = False
            if self.on_disconnect:
                self.on_disconnect()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "status":
            self.last_status = data
        dispatch = {
            "status":         self.on_status,
            "posture":        self.on_posture,
            "alert":          self.on_alert,
            "session_end":    self.on_session_end,
            "session_status": self.on_session_status,
        }
        cb = dispatch.get(msg_type)
        if cb:
            cb(data)