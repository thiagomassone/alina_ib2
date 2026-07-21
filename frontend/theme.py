"""Paleta y constantes visuales de ALINA (con soporte de modo claro/oscuro).

Los colores viven en dos paletas (_LIGHT / _DARK) y `set_mode()` reasigna los
nombres a nivel módulo. Como las vistas leen `t.NAVY`, `t.CARD`, etc. al
construirse, para que un cambio de modo se vea hay que RECONSTRUIR la vista
(lo hace home_view al arrancar y el perfil al guardar preferencias).

Regla importante:
    - CARD / BG / DIVIDER / TEXT_* cambian con el modo (superficies y textos).
    - ON_COLOR es SIEMPRE blanco: texto/íconos sobre fondos de color (badges,
      botones, avatar). No usar CARD para eso, porque en oscuro CARD es gris.
"""

from __future__ import annotations

# Texto/íconos sobre superficies de color — constante en ambos modos.
ON_COLOR = "#FFFFFF"

_LIGHT = {
    "NAVY": "#1A2E4D",
    "TEAL": "#03A097",
    "TEAL_SOFT": "#C8EDEB",
    "BG": "#F3F5F8",
    "CARD": "#FFFFFF",
    "DIVIDER": "#E5E9F0",
    "TEXT_DARK": "#1A2E4D",
    "TEXT_MUTED": "#6B7785",
    "TEXT_LIGHT": "#9AA4B0",
    "GOOD": "#03A097",
    "NEUTRAL": "#F59E0B",
    "BAD": "#EF4444",
    "SHADOW": "#0F2C4D14",
}

_DARK = {
    "NAVY": "#EAEEF5",        # texto primario claro (NAVY = texto en esta app)
    "TEAL": "#03A097",        # acento de marca, se mantiene
    "TEAL_SOFT": "#123C37",   # tinte teal oscuro (indicador de nav, fondos suaves)
    "BG": "#0E1420",          # fondo de pantalla
    "CARD": "#182231",        # superficie de tarjetas (elevada sobre BG)
    "DIVIDER": "#29354A",
    "TEXT_DARK": "#EAEEF5",   # texto principal
    "TEXT_MUTED": "#9BA6B6",
    "TEXT_LIGHT": "#6B7688",
    "GOOD": "#03A097",
    "NEUTRAL": "#F59E0B",
    "BAD": "#EF4444",
    "SHADOW": "#00000040",
}

_PALETTES = {"light": _LIGHT, "dark": _DARK}
MODE = "light"

# Estos se (re)asignan en set_mode(); se declaran acá para que existan al importar.
NAVY = TEAL = TEAL_SOFT = BG = CARD = DIVIDER = ""
TEXT_DARK = TEXT_MUTED = TEXT_LIGHT = GOOD = NEUTRAL = BAD = SHADOW = ""


def set_mode(mode: str) -> str:
    """Cambia la paleta activa. Devuelve el modo aplicado ('light' | 'dark')."""
    global MODE, NAVY, TEAL, TEAL_SOFT, BG, CARD, DIVIDER
    global TEXT_DARK, TEXT_MUTED, TEXT_LIGHT, GOOD, NEUTRAL, BAD, SHADOW
    mode = "dark" if mode == "dark" else "light"
    p = _PALETTES[mode]
    NAVY = p["NAVY"]; TEAL = p["TEAL"]; TEAL_SOFT = p["TEAL_SOFT"]
    BG = p["BG"]; CARD = p["CARD"]; DIVIDER = p["DIVIDER"]
    TEXT_DARK = p["TEXT_DARK"]; TEXT_MUTED = p["TEXT_MUTED"]; TEXT_LIGHT = p["TEXT_LIGHT"]
    GOOD = p["GOOD"]; NEUTRAL = p["NEUTRAL"]; BAD = p["BAD"]; SHADOW = p["SHADOW"]
    MODE = mode
    return mode


set_mode("light")
