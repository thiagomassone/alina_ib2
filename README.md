# ALINA - IB2

Aplicación con interfaz gráfica multiplataforma: corre **hoy como web app** (PC y celular vía navegador) y mañana, con el mismo código, se puede empaquetar como **app nativa para iOS y Android**.

## Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite
- **Frontend**: [Flet](https://flet.dev/) (Python sobre Flutter) — una sola base de código para web, desktop y mobile
- **Auth**: JWT con `python-jose` + hash de contraseñas con `bcrypt`

## Estructura del repo

```
alina-ib2/
├── backend/
│   ├── app/
│   │   ├── main.py            # Entry point FastAPI
│   │   ├── config.py          # Settings (lee .env)
│   │   ├── database.py        # Engine + sesión SQLAlchemy
│   │   ├── models.py          # Tablas: User, UserPreferences
│   │   ├── schemas.py         # Schemas Pydantic
│   │   ├── security.py        # Hash + JWT
│   │   └── routers/
│   │       ├── auth.py        # /auth/register, /auth/login
│   │       └── preferences.py # /preferences/me (GET/PATCH)
│   └── .env.example
├── frontend/
│   ├── main.py                # Entry point Flet
│   ├── api_client.py          # Wrapper HTTP del backend
│   └── views/
│       ├── login_view.py
│       └── home_view.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup local (una sola vez)

```bash
# 1. Cloná el repo
git clone https://github.com/thiagomassone/alina_ib2
cd alina-ib2

# 2. Creá y activá un entorno virtual
python -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Instalá las dependencias
pip install -r requirements.txt

# 4. Configurá variables de entorno del backend
cp backend/.env.example backend/.env
# Editá backend/.env y poné un SECRET_KEY largo y aleatorio
```

## Correr el proyecto

Necesitás **dos terminales** (una para el backend, otra para el frontend), ambas con el venv activado.

### Terminal 1 — backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API en `http://localhost:8000`
- Docs interactivas en `http://localhost:8000/docs`

### Terminal 2 — frontend (Flet)

```bash
cd frontend
flet run main.py                  # como app de escritorio
# flet run --web main.py          # como web app (abre en el navegador)
```

## A futuro: empaquetar para móvil

Con el mismo código del frontend:

```bash
cd frontend
flet build apk        # Android
flet build ipa        # iOS (requiere macOS + Xcode)
flet build web        # bundle estático para desplegar en cualquier hosting
```

## Convenciones para el equipo

- Trabajar en ramas (`feature/<nombre>`) y abrir Pull Requests contra `main`.
- No commitear el archivo `.env` ni la base `*.db` (ya están en `.gitignore`).
- Si agregás dependencias: `pip install <paquete>` y actualizar `requirements.txt` con `pip freeze | grep <paquete>` (o a mano, manteniendo versiones fijas).

## Publicar el repo en GitHub

```bash
# Desde la raíz del proyecto
git init
git add .
git commit -m "Estructura inicial del proyecto"
git branch -M main

# Crear el repo vacío en https://github.com/new (sin README ni .gitignore)
git remote add origin https://github.com/<tu-usuario>/alina-ib2.git
git push -u origin main
```

Después, en **Settings → Collaborators** invitás a tus compañeros del equipo.


Cambios:
frontend/views/
├── components.py       ← helpers compartidos (card, pill, dot, etc.)
├── home_view.py        ← solo el shell con la NavigationBar (20 líneas)
├── resumen_view.py     ← Tab 0
├── en_vivo_view.py     ← Tab 1 (placeholder)
├── historial_view.py   ← Tab 2
├── analisis_view.py    ← Tab 3 (placeholder)
├── alertas_view.py     ← Tab 4 (placeholder)
└── perfil_view.py      ← Tab 5

Score de cada sesión:
score = 100 - (alertas_hápticas / minutos_sesión) * factor

Score de Resumen = promedio de todas las sesiones del usuario