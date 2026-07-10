"""Tab 5 — Perfil: info usuario y preferencias."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, divider, section_header, show_snack


def _avatar(foto_b64: str | None, nombre: str, size: int = 52) -> ft.Control:
    if foto_b64:
        return ft.Container(
            content=ft.Image(src_base64=foto_b64.split(",")[-1], fit=ft.ImageFit.COVER),
            width=size, height=size, border_radius=size,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
    initial = (nombre[0].upper() if nombre else "?")
    return ft.Container(
        content=ft.Text(initial, size=size * 0.4, weight=ft.FontWeight.W_700, color=t.CARD),
        width=size, height=size, bgcolor=t.TEAL, border_radius=size,
        alignment=ft.alignment.center,
    )


def _field(label: str, value: str, password: bool = False, keyboard=ft.KeyboardType.TEXT) -> ft.TextField:
    return ft.TextField(
        label=label, value=value,
        password=password, can_reveal_password=password,
        keyboard_type=keyboard,
        border_color=t.DIVIDER, focused_border_color=t.TEAL,
        label_style=ft.TextStyle(color=t.TEXT_MUTED, size=12),
        text_style=ft.TextStyle(color=t.TEXT_DARK, size=14),
        border_radius=8,
    )


# ── Vista de edición de perfil (pantalla completa) ────────────────────────────

def _edit_profile_view(page: ft.Page, user: dict, on_saved) -> ft.View:
    nombre_f   = _field("Nombre",   user.get("nombre")   or "")
    apellido_f = _field("Apellido", user.get("apellido") or "")
    edad_f     = _field("Edad",     str(user.get("edad") or ""), keyboard=ft.KeyboardType.NUMBER)
    email_f    = _field("Email",    user.get("email")    or "", keyboard=ft.KeyboardType.EMAIL)

    sexo_dd = ft.Dropdown(
        label="Sexo",
        value=user.get("sexo") or None,
        options=[
            ft.dropdown.Option("M",    "Masculino"),
            ft.dropdown.Option("F",    "Femenino"),
            ft.dropdown.Option("otro", "Prefiero no decir"),
        ],
        border_color=t.DIVIDER, focused_border_color=t.TEAL, border_radius=8,
    )

    pass_actual_f = _field("Contraseña actual",           "", password=True)
    pass_nuevo_f  = _field("Nueva contraseña",            "", password=True)
    pass_conf_f   = _field("Confirmar nueva contraseña",  "", password=True)

    status_text = ft.Text("", size=13, visible=False)  # kept for compat, hidden

    def _show_snack(msg: str, color: str):
        show_snack(page, msg, bgcolor=color)
    foto_status = ft.Text("", size=11, color=t.TEXT_MUTED)
    avatar_ref  = ft.Ref[ft.Container]()

    display_name = " ".join(filter(None, [user.get("nombre"), user.get("apellido")])) or user.get("email", "")

    def pick_foto(_):
        picker = ft.FilePicker(on_result=on_foto_result)
        page.overlay.append(picker)
        page.update()
        picker.pick_files(
            dialog_title="Seleccioná tu foto",
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
            allow_multiple=False,
        )

    def on_foto_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        f = e.files[0]
        try:
            with open(f.path, "rb") as fh:
                data = fh.read()
            ext = f.name.split(".")[-1].lower()
            ct = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            result = page.api.upload_foto(data, ct)
            foto_status.value = "Foto actualizada ✓"
            foto_status.color = t.GOOD
            avatar_ref.current.content = _avatar(result.get("foto_b64"), nombre_f.value or "?", size=80)
            on_saved(result)
        except Exception as ex:
            foto_status.value = f"Error al subir: {ex}"
            foto_status.color = t.BAD
        page.update()

    def save_profile(_):
        try:
            edad_val = int(edad_f.value) if edad_f.value.strip() else None
        except ValueError:
            _show_snack("La edad debe ser un número", t.BAD)
            return
        try:
            result = page.api.update_profile(
                nombre=nombre_f.value.strip() or None,
                apellido=apellido_f.value.strip() or None,
                edad=edad_val,
                sexo=sexo_dd.value,
                email=email_f.value.strip() or None,
            )
            _show_snack("Perfil guardado ✓", t.GOOD)
            on_saved(result)
            page.update()
        except Exception as ex:
            _show_snack(f"Error: {ex}", t.BAD)
            page.update()

    def change_password(_):
        if not pass_actual_f.value:
            _show_snack("Ingresá tu contraseña actual", t.BAD)
            return
        if pass_nuevo_f.value != pass_conf_f.value:
            _show_snack("Las contraseñas nuevas no coinciden", t.BAD)
            return
        if len(pass_nuevo_f.value) < 8:
            _show_snack("Mínimo 8 caracteres para la nueva contraseña", t.BAD)
            return
        try:
            page.api.change_password(pass_actual_f.value, pass_nuevo_f.value)
            _show_snack("Contraseña actualizada ✓", t.GOOD)
            pass_actual_f.value = pass_nuevo_f.value = pass_conf_f.value = ""
            page.update()
        except Exception:
            _show_snack("Contraseña actual incorrecta", t.BAD)

    def go_back(_):
        page.views.pop()
        page.update()

    return ft.View(
        route="/perfil/editar",
        bgcolor=t.BG,
        padding=0,
        appbar=ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=go_back, icon_color=t.NAVY),
            title=ft.Text("Editar perfil", size=18, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
            bgcolor=t.CARD,
            elevation=1,
        ),
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=20),
                content=ft.Column(
                    [
                        # Avatar
                        ft.Column(
                            [
                                ft.Container(
                                    ref=avatar_ref,
                                    content=_avatar(user.get("foto_b64"), display_name, size=80),
                                    alignment=ft.alignment.center,
                                ),
                                ft.Container(height=8),
                                ft.Row(
                                    [
                                        ft.TextButton(
                                            "Cambiar foto",
                                            icon=ft.icons.CAMERA_ALT_OUTLINED,
                                            on_click=pick_foto,
                                            style=ft.ButtonStyle(color=t.TEAL),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                foto_status,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),

                        ft.Container(height=8),

                        # Datos personales
                        card(ft.Column(
                            [
                                card_label("Datos personales"),
                                ft.Container(height=12),
                                nombre_f,
                                apellido_f,
                                ft.Row([
                                    ft.Container(content=edad_f, expand=True),
                                    ft.Container(content=sexo_dd, expand=True),
                                ], spacing=12),
                                email_f,
                                ft.Container(height=4),
                                ft.FilledButton(
                                    "Guardar perfil",
                                    icon=ft.icons.SAVE_OUTLINED,
                                    on_click=save_profile,
                                    style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                                    width=float("inf"),
                                ),
                            ],
                            spacing=10,
                        )),

                        # Cambiar contraseña
                        card(ft.Column(
                            [
                                card_label("Cambiar contraseña"),
                                ft.Container(height=12),
                                pass_actual_f,
                                pass_nuevo_f,
                                pass_conf_f,
                                ft.Container(height=4),
                                ft.FilledButton(
                                    "Actualizar contraseña",
                                    icon=ft.icons.LOCK_OUTLINED,
                                    on_click=change_password,
                                    style=ft.ButtonStyle(bgcolor=t.NAVY, color=t.CARD),
                                    width=float("inf"),
                                ),
                            ],
                            spacing=10,
                        )),

                        status_text,
                        ft.Container(height=20),
                    ],
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                expand=True,
            ),
        ],
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def perfil_view(page: ft.Page) -> ft.Control:
    try:
        user = page.api.get_me()
    except Exception:
        user = {"email": ""}

    try:
        prefs = page.api.get_preferences()
    except Exception:
        prefs = {"theme": "light", "language": "es", "notifications_enabled": True}

    display_name = " ".join(filter(None, [user.get("nombre"), user.get("apellido")])) or user.get("email", "")

    avatar_ref = ft.Ref[ft.Container]()
    name_ref   = ft.Ref[ft.Text]()
    email_ref  = ft.Ref[ft.Text]()
    sexo_edad_ref = ft.Ref[ft.Text]()

    def on_profile_saved(updated: dict):
        nonlocal user
        user = updated
        new_name = " ".join(filter(None, [updated.get("nombre"), updated.get("apellido")])) or updated.get("email", "")
        name_ref.current.value  = new_name
        email_ref.current.value = updated.get("email", "")
        avatar_ref.current.content = _avatar(updated.get("foto_b64"), new_name, size=52)
        sexo_label = {"M": "Masculino", "F": "Femenino", "otro": "Prefiero no decir"}.get(updated.get("sexo", ""), "")
        edad_str = f"{updated['edad']} años" if updated.get("edad") else ""
        sexo_edad_ref.current.value = " · ".join(filter(None, [sexo_label, edad_str]))
        page.update()

    def open_edit(_):
        edit_view = _edit_profile_view(page, user, on_saved=on_profile_saved)
        page.views.append(edit_view)
        page.update()

    # Preferencias
    theme_dd = ft.Dropdown(
        label="Tema", value=prefs.get("theme", "light"),
        options=[ft.dropdown.Option("light", "Claro"), ft.dropdown.Option("dark", "Oscuro")],
        border_color=t.DIVIDER, focused_border_color=t.TEAL,
    )
    lang_dd = ft.Dropdown(
        label="Idioma", value=prefs.get("language", "es"),
        options=[
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("pt", "Português"),
        ],
        border_color=t.DIVIDER, focused_border_color=t.TEAL,
    )
    notif_sw   = ft.Switch(value=prefs.get("notifications_enabled", True), active_color=t.TEAL)
    pref_status = ft.Text("", size=12)

    def save_prefs(_):
        try:
            page.api.update_preferences(
                theme=theme_dd.value,
                language=lang_dd.value,
                notifications_enabled=notif_sw.value,
            )
            page.theme_mode = ft.ThemeMode.DARK if theme_dd.value == "dark" else ft.ThemeMode.LIGHT
            pref_status.value = "Guardado ✓"
            pref_status.color = t.GOOD
        except Exception as ex:
            pref_status.value = f"Error: {ex}"
            pref_status.color = t.BAD
        page.update()

    def logout(_):
        page.api.logout()
        page.go("/login")

    sexo_label = {"M": "Masculino", "F": "Femenino", "otro": "Prefiero no decir"}.get(user.get("sexo", ""), "")
    edad_str   = f"{user['edad']} años" if user.get("edad") else ""
    sexo_edad  = " · ".join(filter(None, [sexo_label, edad_str]))

    return ft.Column(
        [
            section_header("Perfil", "Tu cuenta"),
            ft.Container(height=10),

            # Card usuario
            ft.GestureDetector(
                on_tap=open_edit,
                content=card(
                    ft.Row(
                        [
                            ft.Container(ref=avatar_ref, content=_avatar(user.get("foto_b64"), display_name)),
                            ft.Column(
                                [
                                    ft.Text(ref=name_ref, value=display_name, size=15, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                    ft.Text(ref=email_ref, value=user.get("email", ""), size=12, color=t.TEXT_MUTED),
                                    ft.Text(ref=sexo_edad_ref, value=sexo_edad, size=11, color=t.TEXT_LIGHT),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=20),
                        ],
                        spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=14,
                ),
            ),

            # Preferencias
            card(
                ft.Column(
                    [
                        card_label("Preferencias"),
                        ft.Container(height=8),
                        ft.Row(
                            [ft.Text("Notificaciones", size=13, color=t.TEXT_DARK, expand=True), notif_sw],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        divider(),
                        ft.Container(height=4),
                        theme_dd,
                        lang_dd,
                        ft.Container(height=4),
                        ft.FilledButton(
                            "Guardar preferencias",
                            on_click=save_prefs,
                            style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                        ),
                        pref_status,
                    ],
                    spacing=10,
                )
            ),

            # Salir
            card(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Sesión", size=13, color=t.TEXT_MUTED),
                                ft.Text("Salir de la cuenta", size=14, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.OutlinedButton("Salir", icon=ft.icons.LOGOUT, on_click=logout, style=ft.ButtonStyle(color=t.NAVY)),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),

            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )