"""Paleta y constantes visuales de ALINA.

Centralizamos los colores acá para que toda la app respete la identidad
visual definida por el equipo.

Paleta:
    - NAVY        azul marino del logo (texto primario, marca)
    - TEAL        turquesa del logo (#03A097 — color oficial del equipo)
    - TEAL_SOFT   variante clara para fondos sutiles / secciones de chart
    - BG          gris muy claro de fondo de pantalla
    - CARD        blanco puro para tarjetas
    - TEXT_DARK   texto principal (= NAVY)
    - TEXT_MUTED  subtítulos, labels
    - TEXT_LIGHT  texto terciario
    - GOOD        verde (postura buena, conectado)
    - NEUTRAL     ámbar (postura neutra, advertencia leve)
    - BAD         rojo (postura mala, alerta)
    - DIVIDER     gris para separadores
"""

from __future__ import annotations

# Marca
NAVY = "#1A2E4D"
TEAL = "#03A097"          # color oficial del equipo
TEAL_SOFT = "#C8EDEB"

# Superficies
BG = "#F3F5F8"
CARD = "#FFFFFF"
DIVIDER = "#E5E9F0"

# Tipografía
TEXT_DARK = "#1A2E4D"
TEXT_MUTED = "#6B7785"
TEXT_LIGHT = "#9AA4B0"

# Estados de postura / sistema
GOOD = "#03A097"          # unificado con TEAL para consistencia con el mockup
NEUTRAL = "#F59E0B"
BAD = "#EF4444"

# Sombra reutilizable
SHADOW = "#0F2C4D14"