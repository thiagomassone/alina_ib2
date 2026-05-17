"""Vista de login y registro."""

from __future__ import annotations

import flet as ft
import httpx


def login_view(page: ft.Page, on_success) -> ft.View:
    """Construye la vista /login. ``on_success`` se llama tras autenticar OK."""

    username = ft.TextField(label="Usuario", autofocus=True, width=320)
    password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=320)
    error = ft.Text("", color=ft.Colors.RED_400)

    def do_login(_):
        error.value = ""
        try:
            page.api.login(username.value or "", password.value or "")
            on_success()
        except httpx.HTTPStatusError as e:
            error.value = "Usuario o contraseña incorrectos" if e.response.status_code == 401 else str(e)
            page.update()
        except Exception as e:
            error.value = f"Error de conexión: {e}"
            page.update()

    def go_register(_):
        page.go("/register")

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("ALINA - IB2", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("Iniciar sesión", size=18, color=ft.Colors.GREY_700),
                        ft.Container(height=20),
                        username,
                        password,
                        error,
                        ft.FilledButton("Entrar", on_click=do_login, width=320),
                        ft.TextButton("Crear cuenta nueva", on_click=go_register),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=40,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def register_view(page: ft.Page) -> ft.View:
    username = ft.TextField(label="Usuario", autofocus=True, width=320)
    email = ft.TextField(label="Email", width=320)
    password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=320)
    error = ft.Text("", color=ft.Colors.RED_400)

    def do_register(_):
        error.value = ""
        try:
            page.api.register(username.value or "", email.value or "", password.value or "")
            page.api.login(username.value or "", password.value or "")
            page.go("/")
        except httpx.HTTPStatusError as e:
            error.value = e.response.json().get("detail", str(e))
            page.update()
        except Exception as e:
            error.value = f"Error: {e}"
            page.update()

    return ft.View(
        route="/register",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Crear cuenta", size=28, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        username,
                        email,
                        password,
                        error,
                        ft.FilledButton("Registrarme", on_click=do_register, width=320),
                        ft.TextButton("Volver", on_click=lambda _: page.go("/login")),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=40,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
