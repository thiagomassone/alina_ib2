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
import time
import websocket  # pip install websocket-client

_EVENTS = ("connect", "disconnect", "status", "posture", "alert", "session_end", "session_status")

# Timeout del handshake TCP. Sin esto, un connect() a una IP que no existe deja
# el hilo trabado en socket.connect() hasta que el SO se rinda — ~75s en macOS —
# y close() no lo interrumpe, porque todavía no hay socket que cerrar. O sea:
# cada vez que el usuario se equivoca escribiendo la IP, un hilo colgado por más
# de un minuto. Con 5s se limpian solos.
#
# Es global al módulo websocket, pero ws_client es el único que lo usa en la app.
# MEDIDO: no afecta al loop de lectura — una conexión establecida sigue viva sin
# cortes (el read usa su propio timeout, el de ping_timeout).
websocket.setdefaulttimeout(5)


class ALINAWebSocket:
    PORT = 81

    # Si no llega NADA del ESP (ni mensaje, ni pong al ping de run_forever) en
    # este tiempo, lo damos por desconectado. Tiene que ser holgado respecto de
    # ping_interval=5 para no cortar por un hipo de la red: con 12s toleramos
    # dos pings perdidos seguidos antes de bajar el pulgar.
    RX_TIMEOUT = 12.0

    def __init__(self, esp_ip: str = ""):
        self.esp_ip   = esp_ip
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_status: dict | None = None
        self.last_rx  = 0.0      # timestamp del último frame recibido del ESP
        self._watchdog: threading.Thread | None = None

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

    def _teardown(self) -> None:
        """Bajar la conexión actual del todo, si hay alguna.

        POR QUÉ HACE FALTA: run_forever(reconnect=5) reintenta PARA SIEMPRE.
        Ese hilo no muere solo — hay que pedirle que pare. Antes connect()
        sobrescribía self._ws con uno nuevo y el viejo se quedaba huérfano,
        reintentando la IP vieja de por vida. Con tocar "Conectar" dos veces
        (o probar con localhost, que falle, y después poner alina.local) ya
        te quedaban dos hilos compitiendo. Y si el zombi llegaba a conectar,
        disparaba SU _on_open y te pisaba el flag y los eventos de la buena.
        """
        old_ws, old_thread = self._ws, self._thread
        self._ws = None
        self._thread = None
        if old_ws is None:
            return

        # Desarmar los callbacks ANTES de cerrar: close() no es instantáneo
        # (si run_forever está durmiendo entre reintentos, tarda hasta 5s en
        # enterarse) y no queremos que ese zombi toque el estado mientras
        # agoniza. WebSocketApp chequea `if callback:` antes de invocarlos,
        # así que ponerlos en None es seguro.
        old_ws.on_open = old_ws.on_message = None
        old_ws.on_error = old_ws.on_close = old_ws.on_pong = None

        try:
            old_ws.close()   # pone keep_running=False → corta el loop de reconexión
        except Exception:
            pass

        # El flag lo bajamos nosotros, porque el on_close del viejo ya no existe.
        self._mark_disconnected()

        if (old_thread and old_thread.is_alive()
                and old_thread is not threading.current_thread()):
            old_thread.join(timeout=2)

    def connect(self, esp_ip: str | None = None):
        """Conectar al WebSocket del ESP32. Si ya había una conexión, la cierra."""
        if esp_ip:
            self.esp_ip = esp_ip
        if not self.esp_ip:
            raise ValueError("esp_ip no configurado")

        self._teardown()
        self.last_rx = 0.0   # que el watchdog no mida contra la conexión anterior

        url = f"ws://{self.esp_ip}:{self.PORT}"
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_pong=self._on_pong,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={
                "reconnect": 5,
                "ping_interval": 5,   # mandar ping cada 5s
                "ping_timeout": 3,    # (no dispara nunca — ver _watchdog_loop)
            },
            daemon=True,
        )
        self._thread.start()

        if self._watchdog is None:
            self._watchdog = threading.Thread(target=self._watchdog_loop, daemon=True)
            self._watchdog.start()

    def disconnect(self):
        self._teardown()

    # ── Enviar comandos ───────────────────────────────────────────────────────

    def _send(self, cmd: dict) -> bool:
        """Devuelve True si se mandó. NUNCA lanza: si el socket ya estaba
        cerrado (ej. apagaste el ESP y el TCP quedó colgado sin FIN), el flag
        `connected` todavía dice True y el guard de abajo da verde igual — así
        que la única defensa real es atrapar el fallo del send y usarlo como
        señal de desconexión. Antes esto explotaba y la excepción terminaba
        como 'Future exception was never retrieved' en la consola de Flet."""
        if not self._ws or not self.connected:
            return False
        try:
            self._ws.send(json.dumps(cmd))
            return True
        except Exception:
            self._mark_disconnected()
            return False

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

    # ── Estado de conexión ────────────────────────────────────────────────────

    def _mark_disconnected(self) -> None:
        """Único lugar donde se baja el flag. Idempotente: si ya estaba en
        False no vuelve a emitir 'disconnect' (si no, on_close + on_error +
        watchdog dispararían el mismo evento tres veces por cada caída)."""
        if not self.connected:
            return
        self.connected = False
        self._emit("disconnect")

    def _watchdog_loop(self) -> None:
        """Detecta el caso en que el ESP se apaga de golpe.

        Apagar el dispositivo NO cierra el TCP: no hay FIN, el socket queda
        colgado y on_close/on_error nunca se disparan. Entonces el flag
        `connected` se queda en True para siempre y la app sigue mostrando
        'Conectado' con el equipo apagado.

        La señal de vida es `last_rx`, que se refresca con CUALQUIER frame:
        un mensaje del firmware o un pong al ping que run_forever manda cada
        5s. Si no llega nada por RX_TIMEOUT, damos la conexión por muerta.

        MEDIDO CONTRA EL ESP REAL: el firmware contesta los pongs, pero el
        `ping_timeout=3` de websocket-client NO dispara nunca — la librería
        manda los pings y el ESP responde, pero nadie vigila que dejen de
        volver. Por eso este hilo NO es una red de seguridad: es el único
        que detecta el corte de alimentación. Cortando el switch, la caída
        se detecta a los ~12.9s (RX_TIMEOUT + hasta 1s de este sleep).
        """
        while True:
            time.sleep(1)
            if self.connected and self.last_rx:
                if time.time() - self.last_rx > self.RX_TIMEOUT:
                    self._mark_disconnected()

    # ── Handlers internos ─────────────────────────────────────────────────────

    def _on_open(self, ws):
        self.connected = True
        self.last_rx = time.time()
        self._emit("connect")

    def _on_close(self, ws, code, msg):
        self._mark_disconnected()

    def _on_error(self, ws, error):
        self._mark_disconnected()

    def _on_pong(self, ws, data):
        # El pong es la única prueba de vida que existe fuera de sesión: el
        # firmware no manda nada hasta que arranca una sesión.
        self.last_rx = time.time()

    def _on_message(self, ws, message):
        self.last_rx = time.time()
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "status":
            self.last_status = data
        if msg_type in self._listeners:
            self._emit(msg_type, data)