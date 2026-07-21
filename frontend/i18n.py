"""i18n mínimo para ALINA (español ↔ inglés).

La clave de traducción es el propio string en español. `tr("Resumen de hoy")`
devuelve la traducción si el idioma activo es inglés, o el mismo string si es
español (o si no hay traducción cargada).

Importante: `tr()` lee el idioma ACTIVO en el momento de la llamada, así que hay
que llamarlo al construir la vista (no en constantes de módulo). La app se
reconstruye al cambiar de idioma (igual que con el tema), así que todas las
vistas se repintan traducidas.
"""

from __future__ import annotations

LANG = "es"

_EN: dict[str, str] = {
    # Navegación / headers
    "Resumen": "Overview",
    "En vivo": "Live",
    "Historial": "History",
    "Análisis": "Analytics",
    "Alertas": "Alerts",
    "Perfil": "Profile",
    "Resumen de hoy": "Today's summary",
    "Hola, {name}": "Hi, {name}",
    "Tu progreso postural": "Your posture progress",
    "Seguimiento de tus sesiones": "Track your sessions",
    "Tu cuenta": "Your account",
    "Notificaciones del sistema": "System notifications",
    "Monitoreo postural": "Posture monitoring",
    # Tarjeta dispositivo
    "ALINA Dispositivo": "ALINA Device",
    "Desconectado": "Disconnected",
    "Conectado": "Connected",
    "Conectando...": "Connecting...",
    "Conectar": "Connect",
    "Listo": "Ready",
    "Pendiente de calibrar": "Needs calibration",
    "Batería": "Battery",
    "Conexión": "Connection",
    "Estado": "Status",
    "Estado del dispositivo": "Device status",
    # Score / resumen
    "Puntuación postural": "Posture score",
    "Buena": "Good",
    "Neutra": "Neutral",
    "Mala": "Poor",
    "Tiempo hoy": "Time today",
    "Resumen diario": "Daily summary",
    "Buena postura": "Good posture",
    "Mala postura": "Poor posture",
    "Tu puntuación\ngeneral": "Your overall\nscore",
    # Historial
    "Semana": "Week",
    "Mes": "Month",
    "3 meses": "3 months",
    "Año": "Year",
    "Sin datos para este período": "No data for this period",
    "Sesiones recientes": "Recent sessions",
    "Todavía no hay sesiones registradas — iniciá una desde En Vivo":
        "No sessions recorded yet — start one from Live",
    # Análisis
    "Tendencia semanal": "Weekly trend",
    "Score promedio por día": "Average score per day",
    "Semana vs semana pasada": "This week vs last week",
    "Score promedio": "Average score",
    "Minutos de uso": "Minutes of use",
    "Alertas por min": "Alerts per min",
    "sin comparación": "no comparison",
    "Distribución por calidad postural": "Posture quality distribution",
    "Porcentaje del tiempo en cada estado": "Percentage of time in each state",
    "Densidad de alertas": "Alert density",
    "Alertas por minuto · menos es mejor": "Alerts per minute · lower is better",
    "Récords": "Records",
    "Mejor score": "Best score",
    "Sesión más larga": "Longest session",
    "Racha más larga": "Longest streak",
    "Todavía no hay sesiones": "No sessions yet",
    "Completá tu primera sesión para ver tu análisis.":
        "Complete your first session to see your analytics.",
    "Necesitás sesiones en al menos 2 días de esta semana.":
        "You need sessions on at least 2 days this week.",
    "Necesitás sesiones en al menos 2 días.":
        "You need sessions on at least 2 days.",
    "Todavía no hay minutos registrados.": "No minutes recorded yet.",
    "Vas mejorando: esta semana corregís menos que la anterior.":
        "You're improving: fewer corrections this week than last.",
    "Esta semana necesitaste más correcciones que la anterior.":
        "You needed more corrections this week than last.",
    # Alertas
    "Deslizá una notificación para borrarla.": "Swipe a notification to delete it.",
    "Borrar": "Delete",
    "Sin notificaciones": "No notifications",
    "Todo en orden por acá": "All clear here",
    "Sesión": "Session",
    "Récord": "Record",
    "Racha": "Streak",
    "Dispositivo": "Device",
    "Cuenta": "Account",
    "Sistema": "System",
    # Perfil
    "Preferencias": "Preferences",
    "Notificaciones": "Notifications",
    "Tema": "Theme",
    "Idioma": "Language",
    "Oscuro": "Dark",
    "Claro": "Light",
    "Guardar preferencias": "Save preferences",
    "Guardado ✓": "Saved ✓",
    "Salir de la cuenta": "Sign out of your account",
    "Salir": "Sign out",
    "Editar perfil": "Edit profile",
    "Editar nombre": "Edit name",
    "Datos personales": "Personal info",
    "Nombre": "First name",
    "Apellido": "Last name",
    "Email": "Email",
    "Edad": "Age",
    "Sexo": "Sex",
    "Masculino": "Male",
    "Femenino": "Female",
    "Prefiero no decir": "Prefer not to say",
    "Guardar perfil": "Save profile",
    "Guardar": "Save",
    "Cambiar contraseña": "Change password",
    "Cambiar foto": "Change photo",
    "Seleccioná tu foto": "Select your photo",
    "Contraseña": "Password",
    "Contraseña actual": "Current password",
    "Nueva contraseña": "New password",
    "Confirmar nueva contraseña": "Confirm new password",
    "Confirmar contraseña": "Confirm password",
    "Actualizar contraseña": "Update password",
    "Contraseña actualizada ✓": "Password updated ✓",
    "Perfil guardado ✓": "Profile saved ✓",
    "Foto actualizada ✓": "Photo updated ✓",
    "Contraseña actual incorrecta": "Current password is incorrect",
    "Las contraseñas no coinciden": "Passwords don't match",
    "Las contraseñas nuevas no coinciden": "New passwords don't match",
    "La contraseña debe tener al menos 8 caracteres":
        "Password must be at least 8 characters",
    "Mínimo 8 caracteres para la nueva contraseña":
        "At least 8 characters for the new password",
    "Ingresá tu contraseña actual": "Enter your current password",
    "La edad debe ser un número": "Age must be a number",
    "El nombre es obligatorio": "First name is required",
    "El apellido es obligatorio": "Last name is required",
    "El email es obligatorio": "Email is required",
    # Login / registro
    "Iniciar sesión": "Sign in",
    "Ingresar": "Log in",
    "Crear cuenta": "Create account",
    "Completá tus datos para comenzar": "Fill in your details to get started",
    "¿No tenés cuenta? Registrate": "No account? Sign up",
    "¿Ya tenés cuenta? Iniciá sesión": "Already have an account? Sign in",
    "Email o contraseña incorrectos": "Incorrect email or password",
    # En vivo
    "Sesión actual": "Current session",
    "Sesión en curso": "Session in progress",
    "Sin sesión activa": "No active session",
    "Sesión pausada": "Session paused",
    "Controles": "Controls",
    "Finalizar": "Finish",
    "Pausar": "Pause",
    "Reanudar": "Resume",
    "Calibrar equipo": "Calibrate device",
    "Conectá el dispositivo antes de calibrar": "Connect the device before calibrating",
    "Probar": "Test",
    "Probando vibración…": "Testing vibration…",
    "Duración de la vibración": "Vibration duration",
    "Corta": "Short",
    "Media": "Medium",
    "Larga": "Long",
    "Regular": "Regular",
    "Muy corta": "Very short",
    "Muy larga": "Very long",
    "Apagar dispositivo": "Turn off device",
    "Dirección del dispositivo": "Device address",
    "alina.local o IP manual": "alina.local or manual IP",
    "Aplicar": "Apply",
    "Comando enviado al dispositivo": "Command sent to device",
    "Sesión guardada correctamente": "Session saved successfully",
    "Sesión guardada (sin datos del dispositivo)": "Session saved (no device data)",
    "Duración guardada": "Duration saved",
    "Próximamente": "Coming soon",
    "A mejorar": "To improve",
    "Calibrando… mantené la postura 5s (el dispositivo avisa con un sonido al terminar).":
        "Calibrating… hold your posture for 5s (the device beeps when done).",
    "Racha de uso: días seguidos con al menos una sesión":
        "Usage streak: days in a row with at least one session",
    "¡Arrancó tu racha!": "Your streak started!",
    # Extras / subtítulos
    "Semanal": "Weekly",
    "Regular": "Fair",
    "activos": "active",
    "hoy": "today",
    # Títulos de notificaciones (el cuerpo lo genera el backend en español)
    "Dispositivo desconectado": "Device disconnected",
    "Tu resumen de la semana": "Your weekly summary",
    "Tu racha está en riesgo": "Your streak is at risk",
    "¡Nuevo récord de score!": "New score record!",
    "¡Nueva racha récord!": "New streak record!",
    "¡Gran sesión!": "Great session!",
    "Sesión con postura baja": "Low-posture session",
    "Dispositivo sin calibrar": "Device not calibrated",
    "Contraseña actualizada": "Password updated",
    # Meses / días (abreviados)
    "Ene": "Jan", "Feb": "Feb", "Mar": "Mar", "Abr": "Apr", "May": "May", "Jun": "Jun",
    "Jul": "Jul", "Ago": "Aug", "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dic": "Dec",
    "Lun": "Mon", "Mar.": "Tue", "Mié": "Wed", "Jue": "Thu", "Vie": "Fri", "Sáb": "Sat", "Dom": "Sun",
}


def set_lang(lang: str) -> str:
    """Fija el idioma activo. Devuelve 'es' | 'en'."""
    global LANG
    LANG = "en" if lang == "en" else "es"
    return LANG


def tr(s: str) -> str:
    """Traduce `s` al idioma activo (o lo devuelve igual si no hay traducción)."""
    if LANG == "en":
        return _EN.get(s, s)
    return s
