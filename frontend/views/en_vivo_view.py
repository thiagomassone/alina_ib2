"""Tab 1 — En vivo: visualización en tiempo real + control de sesión."""

from __future__ import annotations
import time
import threading
from datetime import datetime
import flet as ft
import theme as t
import i18n
from i18n import tr
from .components import card, card_label, section_header, show_snack


# ─── SVG de espalda con IMUs ─────────────────────────────────────────────────

def _imu_color(status: str) -> str:
    return {"listo": t.GOOD, "calibrar": t.NEUTRAL, "desconectado": t.TEXT_LIGHT}.get(status, t.TEXT_LIGHT)


# El COLOR del punto sale de acá (del SVG), no del overlay:
#   - verde  = listo        - ámbar = pendiente de calibrar
#   - gris   = desconectado - rojo  = zona en mala postura
# Antes el rojo se hacía superponiendo un disco translúcido encima del punto
# verde, y el resultado era exactamente eso: un punto verde con un círculo
# rojo semitransparente arriba, nunca un punto rojo. El motivo original para
# sacar el rojo del SVG era "no regenerar la imagen entera", pero _on_posture
# YA la regenera a 5 Hz para actualizar los números de ángulo — así que no se
# ahorraba nada. El overlay ahora es solo el ARO que late (ver _pulse_ring).
def _back_svg_widget(
    imu_states: dict,
    angles: dict | None = None,
    img_ref: "ft.Ref | None" = None,
    mala: dict | None = None,
) -> ft.Control:
    """angles: {"t1_pitch", "t1_roll", "t12_pitch", "t12_roll"} — si viene None
    (todavía no llegó ningún mensaje de postura) se muestran guiones "-" en
    vez de ocultar el texto: los números siempre están en el mismo lugar,
    así no aparecen/desaparecen de la nada al iniciar o cortar una sesión."""
    import base64

    # dorsal_superior = círculo de arriba = T1 (cerca del cuello)
    # dorsal_medio     = círculo del medio = T12 (más abajo)
    sup = _imu_color(imu_states.get("dorsal_superior", "desconectado"))
    mid = _imu_color(imu_states.get("dorsal_medio",    "desconectado"))
    pel = _imu_color(imu_states.get("pelvis",           "desconectado"))

    # Mala postura pisa el color de estado, pero solo si el sensor está "listo":
    # si está desconectado o sin calibrar no hay dato real que justifique el rojo.
    m = mala or {}
    if m.get("t1")  and imu_states.get("dorsal_superior") == "listo": sup = t.BAD
    if m.get("t12") and imu_states.get("dorsal_medio")    == "listo": mid = t.BAD

    # Números de pitch/roll al lado de cada círculo — siempre se dibujan;
    # si todavía no llegó postura (angles is None) se muestra "-".
    a = angles or {}
    def _f(key: str) -> str:
        v = a.get(key)
        return f"{v:+.1f}°" if v is not None else "-"

    angulos_svg = f"""
  <text x="132" y="76" font-size="8" fill="{t.TEXT_MUTED}" font-family="sans-serif">T1</text>
  <text x="132" y="87" font-size="9" font-weight="700" fill="{t.TEXT_DARK}" font-family="sans-serif">P {_f("t1_pitch")}</text>
  <text x="132" y="98" font-size="9" font-weight="700" fill="{t.TEXT_DARK}" font-family="sans-serif">R {_f("t1_roll")}</text>
  <text x="132" y="136" font-size="8" fill="{t.TEXT_MUTED}" font-family="sans-serif">T12</text>
  <text x="132" y="147" font-size="9" font-weight="700" fill="{t.TEXT_DARK}" font-family="sans-serif">P {_f("t12_pitch")}</text>
  <text x="132" y="158" font-size="9" font-weight="700" fill="{t.TEXT_DARK}" font-family="sans-serif">R {_f("t12_roll")}</text>"""

    svg = f"""<svg viewBox="0 0 200 340" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="28" rx="22" ry="26" fill="#D9E3EE"/>
  <rect x="90" y="50" width="20" height="18" rx="4" fill="#D9E3EE"/>
  <path d="M100 60 Q78 60 64 68 Q48 78 46 100 Q44 124 50 150 Q50 180 58 210 Q68 230 100 232 Q132 230 142 210 Q150 180 150 150 Q156 124 154 100 Q152 78 136 68 Q122 60 100 60Z" fill="#D9E3EE"/>
  <path d="M44 88 Q36 120 38 155 Q40 168 48 172 Q56 176 60 164 Q66 140 68 110 Q64 92 56 86Z" fill="#D9E3EE"/>
  <path d="M156 88 Q164 120 162 155 Q160 168 152 172 Q144 176 140 164 Q134 140 132 110 Q136 92 144 86Z" fill="#D9E3EE"/>
  <path d="M60 210 Q58 235 65 248 Q80 258 100 258 Q120 258 135 248 Q142 235 140 210Z" fill="#C8D6E8"/>
  <line x1="100" y1="68" x2="100" y2="228" stroke="#B0C4D8" stroke-width="1.5" stroke-dasharray="4,4"/>
  
  <circle cx="100" cy="88"  r="16" fill="{sup}" opacity="0.2"/>
  <circle cx="100" cy="88"  r="9" fill="{sup}"/>
  <circle cx="100" cy="88"  r="4" fill="white" opacity="0.7"/>
  <circle cx="100" cy="148" r="16" fill="{mid}" opacity="0.2"/>
  <circle cx="100" cy="148" r="9" fill="{mid}"/>
  <circle cx="100" cy="148" r="4" fill="white" opacity="0.7"/>
  <circle cx="100" cy="215" r="16" fill="{pel}" opacity="0.2"/>
  <circle cx="100" cy="215" r="9"  fill="{pel}"/>
  <circle cx="100" cy="215" r="4"  fill="white" opacity="0.7"/>{angulos_svg}
</svg>"""
    return ft.Image(
        ref=img_ref,
        src_base64=base64.b64encode(svg.encode()).decode(),
        width=200, height=340, fit=ft.ImageFit.CONTAIN,
    )


_RING_SIZE = 34   # tamaño FIJO del aro. El latido se hace con scale, no con width.


def _pulse_ring(cx: int, cy: int, ring_ref: "ft.Ref[ft.Container]") -> ft.Container:
    """Aro rojo que late alrededor de un punto del diagrama cuando hay mala
    postura. Empieza invisible (opacity=0); el hilo de pulso del entry point
    solo toca `scale` y `opacity`.

    POR QUÉ scale Y NO width/height (esto era el bug del aro bailando):
      `animate` interpola width/height, pero `left`/`top` son del Positioned
      del Stack y NO se animan: saltan al valor final al instante. La versión
      vieja movía las cuatro cosas juntas para "recentrar" el aro al cambiar
      de tamaño, así que durante los 450ms de transición el left ya estaba en
      el destino mientras el width todavía viajaba → el centro se corría unos
      7px. Y como el latido dispara cada 550ms con animaciones de 450ms, nunca
      terminaba de asentarse: quedaba permanentemente descentrado.

      `scale` transforma alrededor del CENTRO del control, así que left/top se
      fijan una sola vez acá y no se tocan nunca más. Imposible que se corra.
    """
    s = _RING_SIZE
    return ft.Container(
        ref=ring_ref,
        left=cx - s / 2, top=cy - s / 2,   # se calculan UNA vez y quedan fijos
        width=s, height=s,
        border_radius=s,
        bgcolor=None,                       # sin relleno: el color lo pone el SVG
        border=ft.border.all(2.5, t.BAD),
        opacity=0,
        scale=0.55,
        animate_scale=ft.animation.Animation(450, ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.animation.Animation(450, ft.AnimationCurve.EASE_IN_OUT),
    )


def _legend_item(color: str, label: str) -> ft.Control:
    return ft.Row(
        [ft.Container(width=10, height=10, bgcolor=color, border_radius=10),
         ft.Text(tr(label), size=11, color=t.TEXT_MUTED)],
        spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

def en_vivo_view(page: ft.Page) -> ft.Control:

    # ── Estado de IMUs — se actualiza con mensajes del ESP ────────────────────
    imu_states = {
        "dorsal_superior": "desconectado",
        "dorsal_medio":    "desconectado",
        "pelvis":          "desconectado",
    }
    # Estado de postura en vivo (durante sesión): True = mala postura
    postura_mala = {"t1": False, "t12": False}

    # ── Controles reactivos ───────────────────────────────────────────────────
    back_img_ref  = ft.Ref[ft.Image]()
    t1_pulse_ref  = ft.Ref[ft.Container]()
    t12_pulse_ref = ft.Ref[ft.Container]()
    timer_text  = ft.Text("00:00", size=32, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)
    status_text = ft.Text(tr("Sin sesión activa"), size=13, color=t.TEXT_MUTED)
    conn_status = ft.Text(tr("Desconectado"), size=13, color=t.TEXT_MUTED)

    start_btn = ft.FilledButton(
        ("Start session" if i18n.LANG == "en" else "Iniciar sesión"), icon=ft.icons.PLAY_ARROW,
        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.ON_COLOR), expand=True,
    )
    pause_btn = ft.FilledButton(
        tr("Pausar"), icon=ft.icons.PAUSE,
        style=ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR),
        expand=True, visible=False,
    )
    stop_btn = ft.OutlinedButton(
        tr("Finalizar"), icon=ft.icons.STOP,
        style=ft.ButtonStyle(color=t.BAD, side=ft.BorderSide(1, t.BAD),
                             shape=ft.RoundedRectangleBorder(radius=8)),
        expand=True, visible=False,
    )

    # ── Estado local de sesión ────────────────────────────────────────────────
    # session_active  = False
    # session_paused  = False
    # session_start:  datetime | None = None
    # elapsed_seconds = 0
    # timer_running   = [False]
    
    # ── Estado de sesión — vive en page para sobrevivir cambios de pantalla ───
    if not hasattr(page, "session_active"):
        page.session_active       = False
        page.session_paused       = False
        page.session_start        = None   # datetime de inicio
        page.session_paused_total = 0.0    # segundos acumulados en pausa
        page.session_paused_at    = None   # datetime en que empezó la pausa actual
    timer_running = [False]

    # Datos que llegan del ESP al finalizar sesión
    last_session_data: dict = {}

    # def _fmt_time(s: int) -> str:
    #     h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    #     return f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

    # def _tick():
    #     nonlocal elapsed_seconds
    #     while timer_running[0]:
    #         time.sleep(1)
    #         if timer_running[0] and not session_paused:
    #             elapsed_seconds += 1
    #             timer_text.value = _fmt_time(elapsed_seconds)
    #             try: page.update()
    #             except: break
    
    def _fmt_time(s: int) -> str:
        s = int(s)
        h, m, sec = s // 3600, (s % 3600) // 60, s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

    def _elapsed_now() -> float:
        """Segundos transcurridos desde el inicio, descontando pausas."""
        if not page.session_start:
            return 0.0
        total = (datetime.now() - page.session_start).total_seconds()
        # Restar las pausas ya acumuladas
        total -= page.session_paused_total
        # Si está pausada ahora mismo, restar también la pausa en curso
        if page.session_paused and page.session_paused_at:
            total -= (datetime.now() - page.session_paused_at).total_seconds()
        return max(0.0, total)

    def _tick():
        while timer_running[0]:
            time.sleep(1)
            if timer_running[0]:
                timer_text.value = _fmt_time(_elapsed_now())
                try: page.update()
                except: break


    def _redibujar(angles: dict | None = None):
        """Regenerar el SVG con el estado actual de imu_states / postura_mala.

        OJO: los puntos son una IMAGEN base64. Tocar imu_states no cambia nada
        en pantalla hasta que la imagen se vuelve a generar — page.update() no
        alcanza. Ese era el bug de los puntos verdes con el equipo apagado:
        _on_ws_disconnect ponía el dict en "desconectado" y actualizaba la
        página, pero la imagen seguía siendo la misma de antes. Por eso ahora
        TODOS los caminos que tocan el estado pasan por acá.
        """
        if back_img_ref.current:
            back_img_ref.current.src_base64 = _back_svg_widget(
                imu_states, angles, mala=postura_mala
            ).src_base64

    # ── WebSocket callbacks ───────────────────────────────────────────────────
    ws = getattr(page, "ws_client", None)

    # Timestamp del último "posture" recibido. Se usa para detectar si el ESP
    # se reinició mientras estábamos desconectados (ver _resync_sesion).
    ultimo_posture = [0.0]

    def _resync_sesion():
        """Al reconectar con una sesión activa: ¿el ESP todavía la tiene?

        Cortar la alimentación con el switch NO es una caída de WiFi: el ESP
        reinicia y arranca en SESION_IDLE. Y el firmware solo manda posture
        con `estadoSesion == SESION_RUNNING`, así que en IDLE no manda nada
        más: la app cree que la sesión sigue y el muñequito se queda mudo.

        No se lo podemos preguntar (wsEnviarStatus no incluye el estado de
        sesión), así que lo deducimos por SILENCIO: si estuviera corriendo,
        el posture llega a 5 Hz. Tres segundos sin uno solo ⇒ no está en
        RUNNING ⇒ se reinició ⇒ le re-mandamos start_session.

        Que sea por silencio y no incondicional es lo que salva los datos:
        si fue solo un hipo de WiFi, el ESP siguió prendido acumulando
        alertasHapticas/minBuena/minMala, el posture vuelve al instante y no
        mandamos nada. Un start_session a ciegas se los borraría todos.
        """
        marca = ultimo_posture[0]
        time.sleep(3)
        if not page.session_active or page.session_paused:
            return
        if ultimo_posture[0] != marca:
            return   # llegó postura: el ESP siguió vivo, no tocar nada
        if ws and ws.connected:
            ws.start_session()

    def _on_ws_connect():
        conn_status.value = tr("Conectado")
        conn_status.color = t.GOOD
        try: page.update()
        except: pass
        # Solo si NO está pausada: en pausa el ESP tampoco manda posture, así
        # que el silencio no probaría nada y le estaríamos reiniciando los
        # contadores de una sesión que está sana.
        if getattr(page, "session_active", False) and not page.session_paused:
            threading.Thread(target=_resync_sesion, daemon=True).start()

    def _on_ws_disconnect():
        conn_status.value = tr("Desconectado")
        conn_status.color = t.BAD
        for k in imu_states:
            imu_states[k] = "desconectado"
        # Sin dispositivo no hay postura que mostrar: apagar los aros (si se
        # cayó justo con mala postura, el aro seguiría latiendo para siempre
        # sobre un equipo que no está) y volver los ángulos a "-".
        postura_mala["t1"] = postura_mala["t12"] = False
        _redibujar()
        try: page.update()
        except: pass

    def _on_status(data: dict):
        imu_states["dorsal_superior"] = "listo" if data.get("imu_t1")  else "desconectado"
        imu_states["dorsal_medio"]    = "listo" if data.get("imu_t12") else "desconectado"
        imu_states["pelvis"]          = "listo" if data.get("imu_rpsis") else "desconectado"
        

        try:
            page.api.update_device_status(calibrated=bool(data.get("calibrated")))
        except Exception:
            pass

        if not data.get("calibrated"):
            for k in imu_states:
                if imu_states[k] == "listo":
                    imu_states[k] = "calibrar"

        _redibujar()

        try: page.update()
        except: pass
        
    # Umbrales de mala postura (los mismos del firmware) — se usan tanto para
    # decidir el color/aro en vivo acá como referencia visual; la alerta real
    # (vibración) la decide el ESP con su propia ventana deslizante, así que
    # esto puede marcar "mala" antes de que el dispositivo llegue a vibrar.
    def _es_mala_t1(p, r):
        return (p < -11.2) or (abs(r) > 22.4)
    def _es_mala_t12(p, r):
        return (p < -4.5)

    def _on_posture(data: dict):
        # Los ángulos solo tienen sentido durante una sesión activa — si el
        # ESP manda "posture" fuera de sesión (o llega alguno colgado justo
        # al cortar), lo ignoramos en vez de mostrar un 0.0° que parece un
        # dato real y no lo es. Fuera de sesión el diagrama se queda en "-",
        # igual que cuando está desconectado.
        if not page.session_active:
            return
        ultimo_posture[0] = time.time()
        t1p, t1r   = data.get("t1_pitch", 0),  data.get("t1_roll", 0)
        t12p, t12r = data.get("t12_pitch", 0), data.get("t12_roll", 0)
        # Calcular si cada zona está en mala postura — el hilo de pulso (más
        # abajo) lee este dict y anima los aros solo, no hace falta redibujar
        # nada acá para eso.
        postura_mala["t1"]  = _es_mala_t1(t1p, t1r)
        postura_mala["t12"] = _es_mala_t12(t12p, t12r)
        # Redibujar el muñequito solo para actualizar los números de ángulo
        # (esto sí regenera la imagen base, pero ya no incluye el pulso —
        # el pulso es 100% del hilo de abajo, con animación nativa de Flet,
        # así que regenerar la imagen para los números no lo interrumpe).
        _redibujar({"t1_pitch": t1p, "t1_roll": t1r, "t12_pitch": t12p, "t12_roll": t12r})
        try: page.update()
        except: pass

    # ── Hilo del latido — anima los aros con transiciones nativas de Flet ────
    # Cortar el hilo de una visita anterior a esta tab antes de arrancar el
    # nuevo: cada vez que se reconstruía la vista quedaba un hilo más vivo para
    # siempre, todos llamando page.update() sobre refs viejos.
    old_pulse = getattr(page, "_pulse_running", None)
    if old_pulse is not None:
        old_pulse[0] = False
    pulse_running = [True]
    page._pulse_running = pulse_running

    def _pulse_loop():
        grown = False
        while pulse_running[0]:
            time.sleep(0.55)
            grown = not grown
            for zona, ref in (("t1", t1_pulse_ref), ("t12", t12_pulse_ref)):
                ring = ref.current
                if not ring:
                    continue
                if postura_mala.get(zona):
                    # Solo scale y opacity. left/top/width/height NO se tocan.
                    ring.scale   = 1.0 if grown else 0.55
                    ring.opacity = 0.9 if grown else 0.5
                else:
                    ring.opacity = 0
            try: page.update()
            except: pass

    threading.Thread(target=_pulse_loop, daemon=True).start()

    def _on_session_end(data: dict):
        nonlocal last_session_data
        last_session_data = data
        # Guardar sesión en el backend
        try:
            page.api.create_session(
                # started_at=session_start.isoformat() if session_start else datetime.now().isoformat(),
                # duracion_min=data.get("duracion_min", elapsed_seconds / 60),
                started_at=page.session_start.isoformat() if page.session_start else datetime.now().isoformat(),
                duracion_min=data.get("duracion_min", _elapsed_now() / 60),
                alertas_hapticas=data.get("alertas_hapticas", 0),
                min_buena=data.get("min_buena", 0.0),
                min_mala=data.get("min_mala", 0.0),
            )
            show_snack(page, "Sesión guardada correctamente", bgcolor=t.TEAL)
            on_session_saved()  # notificar al resumen
        except Exception as e:
            show_snack(page, f"Error guardando sesión: {e}", bgcolor=t.BAD)

    def _on_session_status(data: dict):
        state = data.get("state")
        if state == "running":
            status_text.value = tr("Sesión en curso")
            status_text.color = t.GOOD
        elif state == "paused":
            status_text.value = tr("Sesión pausada")
            status_text.color = t.NEUTRAL
        elif state == "idle":
            status_text.value = tr("Sin sesión activa")
            status_text.color = t.TEXT_MUTED
        try: page.update()
        except: pass
        
    def _on_alert(data: dict):
        # El ESP vibró por mala postura → avisar al resumen para que sume +1
        try:
            on_alert_relay()
        except Exception:
            pass

    # Registrar callbacks si hay ws_client en page — vía multi-listener, así
    # no se pisan con lo que registran Resumen/Home para los mismos eventos.
    if ws:
        ws.clear_listeners("en_vivo")
        ws.add_listener("connect",        _on_ws_connect,     owner="en_vivo")
        ws.add_listener("disconnect",     _on_ws_disconnect,  owner="en_vivo")
        ws.add_listener("status",         _on_status,         owner="en_vivo")
        ws.add_listener("posture",        _on_posture,        owner="en_vivo")
        ws.add_listener("alert",          _on_alert,          owner="en_vivo")
        ws.add_listener("session_end",    _on_session_end,    owner="en_vivo")
        ws.add_listener("session_status", _on_session_status, owner="en_vivo")
        if ws.connected:
            conn_status.value = tr("Conectado")
            conn_status.color = t.GOOD
        # Solo replayar el último status si SEGUIMOS conectados: last_status
        # queda cacheado para siempre, así que sin este guard, cambiar de tab
        # con el equipo apagado repintaba los puntos en verde.
        if ws.connected and getattr(ws, "last_status", None):
            _on_status(ws.last_status)
        else:
            _redibujar()

    # ── Handlers de botones ───────────────────────────────────────────────────

    # def start_session(_):
    #     nonlocal session_active, session_paused, session_start, elapsed_seconds
    #     session_active  = True
    #     session_paused  = False
    #     session_start   = datetime.now()
    #     elapsed_seconds = 0
    #     start_btn.visible = False
    #     pause_btn.visible = True
    #     stop_btn.visible  = True
    #     status_text.value = "Sesión en curso"
    #     status_text.color = t.GOOD
    #     timer_text.value  = "00:00"
    #     timer_running[0]  = True
    #     threading.Thread(target=_tick, daemon=True).start()
    #     if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
    #         page.ws_client.start_session()
    #     page.update()
    
    def start_session(_):
        page.session_active       = True
        page.session_paused       = False
        page.session_start        = datetime.now()
        page.session_paused_total = 0.0
        page.session_paused_at    = None
        start_btn.visible = False
        pause_btn.visible = True
        stop_btn.visible  = True
        status_text.value = tr("Sesión en curso")
        status_text.color = t.GOOD
        timer_text.value  = "00:00"
        timer_running[0]  = True
        threading.Thread(target=_tick, daemon=True).start()
        if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
            page.ws_client.start_session()
        page.update()

    # def toggle_pause(_):
    #     nonlocal session_paused
    #     session_paused = not session_paused
    #     if session_paused:
    #         pause_btn.text  = "Reanudar"
    #         pause_btn.icon  = ft.icons.PLAY_ARROW
    #         pause_btn.style = ft.ButtonStyle(bgcolor=t.GOOD, color=t.ON_COLOR)
    #         if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
    #             page.ws_client.pause_session()
    #     else:
    #         pause_btn.text  = "Pausar"
    #         pause_btn.icon  = ft.icons.PAUSE
    #         pause_btn.style = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR)
    #         if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
    #             page.ws_client.resume_session()
    #     page.update()
    
    def toggle_pause(_):
        page.session_paused = not page.session_paused
        if page.session_paused:
            # Empieza la pausa: anotar el momento
            page.session_paused_at = datetime.now()
            pause_btn.text  = tr("Reanudar")
            pause_btn.icon  = ft.icons.PLAY_ARROW
            pause_btn.style = ft.ButtonStyle(bgcolor=t.GOOD, color=t.ON_COLOR)
            if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
                page.ws_client.pause_session()
        else:
            # Termina la pausa: sumar lo que duró al acumulado
            if page.session_paused_at is not None:
                page.session_paused_total += (datetime.now() - page.session_paused_at).total_seconds()
                page.session_paused_at = None
            pause_btn.text  = tr("Pausar")
            pause_btn.icon  = ft.icons.PAUSE
            pause_btn.style = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR)
            if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
                page.ws_client.resume_session()
        page.update()

    # def stop_session(_):
    #     nonlocal session_active, session_paused, elapsed_seconds
    #     timer_running[0] = False
    #     session_active   = False
    #     session_paused   = False
    #     start_btn.visible = True
    #     pause_btn.visible = False
    #     stop_btn.visible  = False
    #     pause_btn.text    = "Pausar"
    #     pause_btn.icon    = ft.icons.PAUSE
    #     pause_btn.style   = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR)
    #     if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
    #         # El ESP responde con session_end que dispara _on_session_end
    #         page.ws_client.stop_session()
    #     else:
    #         # Sin ESP: guardar con datos del timer local
    #         try:
    #             page.api.create_session(
    #                 started_at=session_start.isoformat() if session_start else datetime.now().isoformat(),
    #                 duracion_min=elapsed_seconds / 60,
    #                 alertas_hapticas=0,
    #                 min_buena=0.0,
    #                 min_mala=0.0,
    #             )
    #             page.snack_bar = ft.SnackBar(
    #                 ft.Text("Sesión guardada (sin datos del dispositivo)", color=t.ON_COLOR),
    #                 bgcolor=t.NEUTRAL)
    #         except Exception as e:
    #             page.snack_bar = ft.SnackBar(
    #                 ft.Text(f"Error: {e}", color=t.ON_COLOR), bgcolor=t.BAD)
    #         page.snack_bar.open = True
    #     status_text.value = "Sin sesión activa"
    #     status_text.color = t.TEXT_MUTED
    #     timer_text.value  = "00:00"
    #     elapsed_seconds   = 0
    #     page.update()
    
    def stop_session(_):
        timer_running[0] = False
        # Calcular duración real (descontando pausas) antes de limpiar el estado
        elapsed = _elapsed_now()
        page.session_active = False
        page.session_paused = False
        start_btn.visible = True
        pause_btn.visible = False
        stop_btn.visible  = False
        pause_btn.text    = tr("Pausar")
        pause_btn.icon    = ft.icons.PAUSE
        pause_btn.style   = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR)
        if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
            # El ESP responde con session_end que dispara _on_session_end
            page.ws_client.stop_session()
        else:
            # Sin ESP: guardar con datos del timer local
            try:
                page.api.create_session(
                    started_at=page.session_start.isoformat() if page.session_start else datetime.now().isoformat(),
                    duracion_min=elapsed / 60,
                    alertas_hapticas=0,
                    min_buena=0.0,
                    min_mala=0.0,
                )
                show_snack(page, "Sesión guardada (sin datos del dispositivo)", bgcolor=t.NEUTRAL)
            except Exception as e:
                show_snack(page, f"Error: {e}", bgcolor=t.BAD)
        # Limpiar estado de sesión
        page.session_start        = None
        page.session_paused_total = 0.0
        page.session_paused_at    = None
        status_text.value = tr("Sin sesión activa")
        status_text.color = t.TEXT_MUTED
        timer_text.value  = "00:00"
        # Los ángulos y los aros de mala postura son datos de la sesión que
        # terminó — volver a "-" y apagar los aros en vez de dejar el último
        # valor pegado en pantalla.
        postura_mala["t1"]  = False
        postura_mala["t12"] = False
        _redibujar()
        page.update()

    start_btn.on_click  = start_session
    pause_btn.on_click  = toggle_pause
    stop_btn.on_click   = stop_session
    
    # ── Restaurar estado si ya hay una sesión activa (al volver a esta vista) ──
    if page.session_active:
        start_btn.visible = False
        pause_btn.visible = True
        stop_btn.visible  = True
        if page.session_paused:
            status_text.value = tr("Sesión pausada")
            status_text.color = t.NEUTRAL
            pause_btn.text  = tr("Reanudar")
            pause_btn.icon  = ft.icons.PLAY_ARROW
            pause_btn.style = ft.ButtonStyle(bgcolor=t.GOOD, color=t.ON_COLOR)
        else:
            status_text.value = tr("Sesión en curso")
            status_text.color = t.GOOD
            pause_btn.text  = tr("Pausar")
            pause_btn.icon  = ft.icons.PAUSE
            pause_btn.style = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.ON_COLOR)
        timer_text.value = _fmt_time(_elapsed_now())
        # Reanudar el hilo del timer (solo si no está pausada)
        timer_running[0] = True
        threading.Thread(target=_tick, daemon=True).start()

    def refresh():
        """Llamado por el timer global. Con el multi-listener de ws_client ya
        no hace falta re-registrar los callbacks acá (nadie nos los pisa
        mientras estamos en esta tab) — solo refrescamos el estado de
        conexión mostrado, por si cambió."""
        ws = getattr(page, "ws_client", None)
        if ws:
            if ws.connected:
                conn_status.value = tr("Conectado")
                conn_status.color = t.GOOD
            else:
                conn_status.value = tr("Desconectado")
                conn_status.color = t.BAD

    # home_view sobreescribe esto con referencia al resumen
    def on_session_saved():
        pass
    
    def on_alert_relay():
        pass

    col = ft.Column(
        [
            section_header(tr("En vivo"), tr("Estado del dispositivo")),
            ft.Container(height=10),

            # ── Diagrama + leyenda ─────────────────────────────────────────
            card(
                ft.Column(
                    [
                        card_label("IMUs"),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Stack(
                                        [
                                            _back_svg_widget(imu_states, img_ref=back_img_ref, mala=postura_mala),
                                            _pulse_ring(100, 88,  t1_pulse_ref),
                                            _pulse_ring(100, 148, t12_pulse_ref),
                                        ],
                                        width=200, height=340,
                                    ),
                                    # El Stack de adentro necesita medidas fijas (200x340) para
                                    # que los aros de pulso se superpongan en el lugar correcto
                                    # sobre el SVG. Este Container de afuera sí es elástico
                                    # (expand=True) para ocupar el espacio libre del Row y
                                    # centrar el dibujo ahí — si no, queda pegado a la izquierda
                                    # y no se recentra al agrandar la ventana.
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(tr("Estado"), size=11, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                                        ft.Container(height=6),
                                        _legend_item(t.GOOD,       "Listo"),
                                        _legend_item(t.NEUTRAL,    "Pendiente de calibrar"),
                                        _legend_item(t.BAD,        "Mala postura"),
                                        _legend_item(t.TEXT_LIGHT, "Desconectado"),
                                    ],
                                    spacing=6,
                                    horizontal_alignment=ft.CrossAxisAlignment.START,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                    ],
                    spacing=0,
                )
            ),

            # ── Timer + controles ──────────────────────────────────────────
            card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        card_label(tr("Sesión actual")),
                                        ft.Container(height=4),
                                        timer_text,
                                        status_text,
                                    ],
                                    spacing=2, expand=True,
                                ),
                                ft.Icon(ft.icons.TIMER_OUTLINED, color=t.TEAL_SOFT, size=40),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),
                        ft.Row([start_btn, pause_btn, stop_btn], spacing=8),
                    ],
                    spacing=0,
                )
            ),

            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    col.refresh          = refresh
    col.on_session_saved = on_session_saved
    col.on_alert_relay   = on_alert_relay
    return col