"""Textos de notificaciones en el idioma del usuario (es/en).

El backend genera el título y el cuerpo según la preferencia de idioma del
usuario al momento de crear la notificación.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from .models import UserPreferences


def user_lang(db: DBSession, user_id: int) -> str:
    pref = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    return "en" if (pref and pref.language == "en") else "es"


def _cuando(dt: datetime, en: bool) -> str:
    return f"{dt.strftime('%d/%m')} {'at' if en else 'a las'} {dt.strftime('%H:%M')}"


def notif_text(key: str, lang: str, **k) -> tuple[str, str]:
    """Devuelve (titulo, mensaje) para el tipo/params dados, en es o en."""
    en = lang == "en"

    if key == "session_score_low":
        c = _cuando(k["dt"], en)
        if en:
            return ("Low-posture session",
                    f"Your session on {c} ({k['dur']}) scored {k['score']}/100. "
                    f"Try to keep your back straighter.")
        return ("Sesión con postura baja",
                f"Tu sesión del {c} ({k['dur']}) tuvo un score de {k['score']}/100. "
                f"Intentá mantener la espalda más erguida.")

    if key == "buena_sesion":
        c = _cuando(k["dt"], en)
        if en:
            return ("Great session!",
                    f"Your session on {c} ({k['dur']}) finished with {k['score']}/100. Keep it up!")
        return ("¡Gran sesión!",
                f"Tu sesión del {c} ({k['dur']}) cerró con {k['score']}/100. ¡Seguí así!")

    if key == "record_score":
        c = _cuando(k["dt"], en)
        if en:
            return ("New score record!",
                    f"You beat your best with {k['score']}/100 on your session on {c}.")
        return ("¡Nuevo récord de score!",
                f"Superaste tu mejor marca con {k['score']}/100 en tu sesión del {c}.")

    if key == "record_racha":
        if en:
            return ("New streak record!",
                    f"You reached {k['dias']} days in a row using ALINA. Your best streak!")
        return ("¡Nueva racha récord!",
                f"Llegaste a {k['dias']} días seguidos usando ALINA. ¡Tu mejor racha!")

    if key == "calibration_pending":
        if en:
            return ("Device not calibrated",
                    "Your ALINA isn't calibrated. Calibrate it before your next session "
                    "so alerts are accurate.")
        return ("Dispositivo sin calibrar",
                "Tu ALINA no está calibrado. Calibralo antes de tu próxima sesión "
                "para que las alertas sean precisas.")

    if key == "racha_en_riesgo":
        if en:
            return ("Your streak is at risk",
                    f"You haven't used ALINA today. Do a session so you don't break "
                    f"your {k['dias']}-day streak.")
        return ("Tu racha está en riesgo",
                f"Todavía no usaste ALINA hoy. Hacé una sesión para no cortar "
                f"tu racha de {k['dias']} días.")

    if key == "resumen_semanal":
        return (("Your weekly summary" if en else "Tu resumen de la semana"), k["mensaje"])

    if key == "device_disconnected":
        if en:
            return ("Device disconnected",
                    "Lost connection with your ALINA. Make sure it's on and in range.")
        return ("Dispositivo desconectado",
                "Se perdió la conexión con tu ALINA. Revisá que esté encendido y en rango.")

    if key == "password_changed":
        if en:
            return ("Password updated",
                    "Your password was changed successfully. If it wasn't you, contact support.")
        return ("Contraseña actualizada",
                "Tu contraseña fue cambiada exitosamente. Si no fuiste vos, contactá al soporte.")

    return ("", "")


def resumen_semanal_msg(act: float, prev: float | None, lang: str) -> str:
    """Cuerpo del resumen semanal (comparación de score) en el idioma dado."""
    en = lang == "en"
    if prev is None or prev == 0:
        if en:
            return f"This week your average score was {act:.0f}/100. Keep adding sessions!"
        return f"Esta semana tu score promedio fue {act:.0f}/100. ¡Seguí sumando sesiones!"
    delta = (act - prev) / prev * 100
    if delta >= 0:
        if en:
            return f"This week you improved {delta:.0f}% (average score {act:.0f}/100). Nice work!"
        return f"Esta semana mejoraste un {delta:.0f}% (score promedio {act:.0f}/100). ¡Buen trabajo!"
    if en:
        return f"This week your score dropped {abs(delta):.0f}% ({act:.0f}/100). You'll bounce back."
    return f"Esta semana tu score bajó un {abs(delta):.0f}% ({act:.0f}/100). La próxima repuntás."