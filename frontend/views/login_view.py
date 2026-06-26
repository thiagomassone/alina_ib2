"""Vista de login y registro."""

from __future__ import annotations

import flet as ft
import httpx
import theme as t
from .components import alina_logo_mark


def _field(label: str, password: bool = False, keyboard=ft.KeyboardType.TEXT, autofocus: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        autofocus=autofocus,
        password=password,
        can_reveal_password=password,
        keyboard_type=keyboard,
        border_color=t.DIVIDER,
        focused_border_color=t.TEAL,
        label_style=ft.TextStyle(color=t.TEXT_MUTED, size=12),
        text_style=ft.TextStyle(color=t.TEXT_DARK, size=14),
        border_radius=8,
    )


def login_view(page: ft.Page, on_success) -> ft.View:
    email_f    = _field("Email", keyboard=ft.KeyboardType.EMAIL, autofocus=True)
    password_f = _field("Contraseña", password=True)
    error      = ft.Text("", color=t.BAD, size=13)

    def do_login(_=None):
        error.value = ""
        try:
            page.api.login(email_f.value.strip(), password_f.value)
            on_success()
        except httpx.HTTPStatusError as e:
            error.value = "Email o contraseña incorrectos" if e.response.status_code == 401 else str(e)
            page.update()
        except Exception as e:
            error.value = f"Error de conexión: {e}"
            page.update()

    email_f.on_submit    = do_login
    password_f.on_submit = do_login

    return ft.View(
        route="/login",
        bgcolor=t.BG,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        # Logo
                        ft.Container(
                            content=ft.Column(
                                [
                                    alina_logo_mark(size=64),
                                    ft.Text("ALINA", size=28, weight=ft.FontWeight.W_700, color=t.NAVY),
                                    ft.Text("Monitoreo postural", size=13, color=t.TEXT_MUTED),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=4,
                            ),
                            padding=ft.padding.only(bottom=32),
                        ),

                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Iniciar sesión", size=20, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                    ft.Container(height=8),
                                    email_f,
                                    password_f,
                                    error,
                                    ft.Container(height=4),
                                    ft.FilledButton(
                                        "Ingresar",
                                        on_click=do_login,
                                        width=320,
                                        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                                    ),
                                    ft.TextButton(
                                        "¿No tenés cuenta? Registrate",
                                        on_click=lambda _: page.go("/register"),
                                        style=ft.ButtonStyle(color=t.TEAL),
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10,
                            ),
                            bgcolor=t.CARD,
                            border_radius=16,
                            padding=24,
                            shadow=ft.BoxShadow(blur_radius=12, color=t.SHADOW, offset=ft.Offset(0, 2)),
                            width=368,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=24,
            )
        ],
    )


def register_view(page: ft.Page) -> ft.View:
    nombre_f   = _field("Nombre", autofocus=True)
    apellido_f = _field("Apellido")
    email_f    = _field("Email", keyboard=ft.KeyboardType.EMAIL)
    password_f = _field("Contraseña", password=True)
    confirm_f  = _field("Confirmar contraseña", password=True)
    error      = ft.Text("", color=t.BAD, size=13)

    def do_register(_=None):
        error.value = ""
        if not nombre_f.value.strip():
            error.value = "El nombre es obligatorio"
            page.update()
            return
        if not apellido_f.value.strip():
            error.value = "El apellido es obligatorio"
            page.update()
            return
        if not email_f.value.strip():
            error.value = "El email es obligatorio"
            page.update()
            return
        if len(password_f.value) < 8:
            error.value = "La contraseña debe tener al menos 8 caracteres"
            page.update()
            return
        if password_f.value != confirm_f.value:
            error.value = "Las contraseñas no coinciden"
            page.update()
            return
        try:
            page.api.register(
                nombre=nombre_f.value.strip(),
                apellido=apellido_f.value.strip(),
                email=email_f.value.strip(),
                password=password_f.value,
            )
            page.api.login(email_f.value.strip(), password_f.value)
            page.go("/")
        except httpx.HTTPStatusError as e:
            error.value = e.response.json().get("detail", str(e))
            page.update()
        except Exception as e:
            error.value = f"Error: {e}"
            page.update()

    nombre_f.on_submit   = do_register
    apellido_f.on_submit = do_register
    email_f.on_submit    = do_register
    password_f.on_submit = do_register
    confirm_f.on_submit  = do_register

    return ft.View(
        route="/register",
        bgcolor=t.BG,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Crear cuenta", size=20, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                    ft.Text("Completá tus datos para comenzar", size=13, color=t.TEXT_MUTED),
                                    ft.Container(height=8),
                                    ft.Row([
                                        ft.Container(content=nombre_f,   expand=True),
                                        ft.Container(content=apellido_f, expand=True),
                                    ], spacing=8),
                                    email_f,
                                    password_f,
                                    confirm_f,
                                    error,
                                    ft.Container(height=4),
                                    ft.FilledButton(
                                        "Crear cuenta",
                                        on_click=do_register,
                                        width=320,
                                        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                                    ),
                                    ft.TextButton(
                                        "¿Ya tenés cuenta? Iniciá sesión",
                                        on_click=lambda _: page.go("/login"),
                                        style=ft.ButtonStyle(color=t.TEAL),
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10,
                            ),
                            bgcolor=t.CARD,
                            border_radius=16,
                            padding=24,
                            shadow=ft.BoxShadow(blur_radius=12, color=t.SHADOW, offset=ft.Offset(0, 2)),
                            width=368,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=24,
            )
        ],
    )