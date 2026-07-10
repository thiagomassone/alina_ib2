"""Cliente WebSocket para comunicación con el ESP32 de ALINA.

Uso:
    client = ALINAWebSocket(esp_ip="192.168.1.XX")
    client.connect()
    client.start_session()
    client.stop_session()
    client.disconnect()

Eventos disponibles (para add_listener):
    "status"         → {"calibrated": bool, "imu_t1": bool, ...}
    "posture"        → {"t1_pitch": float, "t1_roll": float, ...}
    "alert"          → {"source": "T12", "count": int}
    "session_end"    → {"duracion_min": float, "alertas_hapticas": int, ...}
    "session_status" → {"state": "running"|"paused"|"idle"}
    "connect"        → sin datos
    "disconnect"     → sin datos

IMPORTANTE — multi-listener:
    Varias vistas (Resumen, En vivo, Home) pueden necesitar enterarse del
    mismo evento al mismo tiempo. Por eso NO se usa `ws.on_connect = fn`
    (eso pisa cualquier callback anterior — si dos vistas lo hacen, solo
    gana la última). En cambio, cada vista se suscribe con:

        ws.add_listener("connect", mi_funcion, owner="en_vivo")

    El "owner" sirve para poder sacar SOLO los listeners de esa vista al
    reconstruirla (ej. al volver a entrar a una tab), sin tocar los de
    las demás:

        ws.clear_listeners("en_vivo")   # antes de volver a registrar
"""

from __future__ import annotations
import json
import threading
import websocket  # pip install websocket-client

_EVENTS = ("connect", "disconnect", "status", "posture", "alert", "session_end", "session_status")


class ALINAWebSocket:
    PORT = 81

    def __init__(self, esp_ip: str = ""):
        self.esp_ip   = esp_ip
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_status: dict | None = None

        # listeners[evento] = lista de (owner, callback)
        self._listeners: dict[str, list[tuple[str | None, callable]]] = {ev: [] for ev in _EVENTS}

    # ── Suscripción de listeners ────────────────────────────────────────────

    def add_listener(self, event: str, callback, owner: str | None = None) -> None:
        """Suscribir un callback a un evento. No pisa listeners existentes."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append((owner, callback))

    def clear_listeners(self, owner: str) -> None:
        """Sacar todos los listeners registrados por 'owner' (de cualquier evento),
        sin tocar los de otros dueños. Llamar antes de re-registrar al reconstruir
        una vista, para no ir acumulando listeners duplicados/viejos."""
        for ev in self._listeners:
            self._listeners[ev] = [(o, cb) for (o, cb) in self._listeners[ev] if o != owner]

    def _emit(self, event: str, *args) -> None:
        for owner, cb in list(self._listeners.get(event, [])):
            try:
                cb(*args)
            except Exception as e:
                print(f"[WS] Error en listener de '{event}' (owner={owner}): {e}")

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
            payload["haptic_intensity"] = haptic_intensity  # el firmware espera esta clave, no "haptic_duration_ms"
        self._send(payload)

    def test_vibration(self, duration_ms: int):
        """Disparar vibración de prueba con la duración especificada."""
        self._send({"cmd": "test_vibration", "haptic_intensity": duration_ms})  # misma clave que espera el firmware

    def wifi_reset(self):
        self._send({"cmd": "wifi_reset"})

    # ── Handlers internos ─────────────────────────────────────────────────────

    def _on_open(self, ws):
        self.connected = True
        self._emit("connect")

    def _on_close(self, ws, code, msg):
        self.connected = False
        self._emit("disconnect")

    def _on_error(self, ws, error):
        # Si la conexión se cayó (ej. ping/pong timeout), notificar desconexión
        if self.connected:
            self.connected = False
            self._emit("disconnect")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "status":
            self.last_status = data
        if msg_type in self._listeners:
            self._emit(msg_type, data)