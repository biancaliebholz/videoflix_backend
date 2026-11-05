# Setup guide (macOS, Windows, Linux)

Detailed installation and configuration. The short version is the
[Quick Start in the README](../README.md#quick-start).

> [!NOTE]
> Tested on macOS with Docker Desktop (Docker Engine 29.9, Compose 5.6).
> The Windows and Linux commands follow the official Docker documentation
> but have not been tested on these systems.

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the repositories](#2-clone-the-repositories)
3. [Create the `.env` file](#3-create-the-env-file)
4. [Start, stop and check the containers](#4-start-stop-and-check-the-containers)
5. [Migrations and admin access](#5-migrations-and-admin-access)
6. [Email: SMTP or console](#6-email-smtp-or-console)
7. [Environment variables](#7-environment-variables)
8. [Frontend](#8-frontend)
9. [Editor support (optional)](#9-editor-support-optional)

Problems? See [troubleshooting.md](troubleshooting.md).

## 1. Prerequisites

Docker is the intended way to run the project; Python, PostgreSQL, Redis and
FFmpeg run inside the containers.

| System | Install | Docs |
|---|---|---|
| macOS | Docker Desktop | [Install on Mac](https://docs.docker.com/desktop/setup/install/mac-install/) |
| Windows 10/11 | Docker Desktop with the WSL 2 backend | [Install on Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |
| Linux | Docker Engine with the Compose plugin (or Docker Desktop) | [Install Docker Engine](https://docs.docker.com/engine/install/), [post-install steps](https://docs.docker.com/engine/install/linux-postinstall/) |

You also need [git](https://git-scm.com/downloads). Check the installation
(same commands in all terminals):

```bash
docker --version
docker compose version
git --version
```

## 2. Clone the repositories

Backend and school frontend are separate repositories. A sibling layout keeps
both easy to find:

```
videoflix/
├── videoflix_backend/    # this repository
└── videoflix_frontend/   # school frontend
```

**macOS / Linux**

```bash
mkdir videoflix && cd videoflix
git clone https://github.com/biancaliebholz/videoflix_backend.git videoflix_backend
git clone https://github.com/Developer-Akademie-Backendkurs/project.Videoflix.git videoflix_frontend
cd videoflix_backend
```

**Windows (PowerShell)**

```powershell
mkdir videoflix; cd videoflix
git clone --config core.autocrlf=input https://github.com/biancaliebholz/videoflix_backend.git videoflix_backend
git clone https://github.com/Developer-Akademie-Backendkurs/project.Videoflix.git videoflix_frontend
cd videoflix_backend
```

`core.autocrlf=input` keeps the LF line endings that `backend.entrypoint.sh`
needs inside the Linux container.

## 3. Create the `.env` file

**macOS / Linux**

```bash
cp .env.template .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.template .env
```

Replace at least `SECRET_KEY`, `DB_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD` and
the `EMAIL_*` values (see [section 6](#6-email-smtp-or-console)). Do not
rename or delete variables. A new secret key can be created without a local
Python installation:

```bash
docker run --rm python:3.12-alpine python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Never commit `.env`; it is git-ignored.

## 4. Start, stop and check the containers

```bash
docker compose up --build -d
docker compose logs -f web
```

The entrypoint waits for PostgreSQL, collects static files, runs the
migrations, creates the superuser from the `.env` values, starts the RQ worker
and finally Gunicorn. The backend is ready when the log shows
`Listening at: http://0.0.0.0:8000`; stop following the log with `Ctrl+C`.

| Task | Command |
|---|---|
| Status of the containers | `docker compose ps` |
| Logs (Gunicorn, RQ worker, console emails) | `docker compose logs -f web` |
| Stop (keeps containers and data) | `docker compose stop` |
| Start again | `docker compose start` |
| Remove containers (keeps volumes and data) | `docker compose down` |
| Rebuild after `requirements.txt` changes | `docker compose up --build -d` |

> [!CAUTION]
> `docker compose down -v` also deletes the volumes: database, uploaded videos
> and HLS files are gone.

The backend runs on **http://127.0.0.1:8000**. Only port 8000 is published;
PostgreSQL and Redis are reachable inside the Docker network only. Uploads,
HLS files and thumbnails live in the volume `videoflix_media`.

## 5. Migrations and admin access

The entrypoint migrates on every start. After model changes:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

Admin: **http://127.0.0.1:8000/admin/**, log in with `DJANGO_SUPERUSER_EMAIL`
and `DJANGO_SUPERUSER_PASSWORD` (the login field is the email address).

- **Users:** email-based user admin with activation status.
- **Videos:** upload title, description, category (selected from a fixed
  list) and video file (thumbnail optional, otherwise generated; a removed
  thumbnail is generated again); watch the processing status, duration and
  errors; action *Convert selected videos again*.

Another superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

## 6. Email: SMTP or console

Activation and password reset emails are sent by the RQ worker.

**SMTP** (real delivery), e.g. with an app password of your mail provider:

```env
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=you@example.com
```

Use port `465` with `EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False`; never set
both to `True`.

**Console backend** (local tests without SMTP): add this line to `.env`; the
emails including their links appear in `docker compose logs web`.

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

> [!IMPORTANT]
> Docker reads `.env` only when the container is created, so
> `docker compose restart` keeps the old values. Apply changes with
> `docker compose up -d --force-recreate --no-deps web`. This aborts a
> running video conversion.

## 7. Environment variables

| Name | Description | Default |
|---|---|---|
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | Superuser created on start | `admin` / `admin@example.com` / `adminpassword` |
| `SECRET_KEY` | Django secret key (**required**) | – |
| `DEBUG` | Debug mode | `False` (template: `True`) |
| `ALLOWED_HOSTS` | Allowed host names | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Trusted frontend origins, also used for CORS | `http://localhost:5500,http://127.0.0.1:5500` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection | `videoflix_db`, `videoflix_user`, –, `db`, `5432` |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_LOCATION` | Redis for RQ and the cache | `redis`, `6379`, `0`, `redis://redis:6379/1` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL` | SMTP settings | `localhost`, `587`, –, –, `True`, `False`, `EMAIL_HOST_USER` |

Optional variables (not in the template, all have defaults):

| Name | Description | Default |
|---|---|---|
| `FRONTEND_URL` | Base URL for activation and reset links | `http://127.0.0.1:5500` |
| `EMAIL_BACKEND` | Django email backend (see [section 6](#6-email-smtp-or-console)) | SMTP backend |
| `AUTH_COOKIE_SECURE` | Send auth cookies only via HTTPS | `False` |
| `AUTH_COOKIE_SAMESITE` | SameSite attribute of the auth cookies | `Lax` |
| `VIDEO_PROCESSING_TIMEOUT` | Maximum seconds for one conversion job | `10800` |

## 8. Frontend

Open the `videoflix_frontend` folder itself in VS Code (*File → Open Folder*)
and start it with the extension
[Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer):
right-click `index.html` → **Open with Live Server**. Without VS Code, any
static server on port 5500 works, started inside `videoflix_frontend`:

```bash
python3 -m http.server 5500 --bind 127.0.0.1   # macOS / Linux
py -m http.server 5500 --bind 127.0.0.1        # Windows
```

Open **`http://127.0.0.1:5500`**, not `localhost:5500`: the auth cookies
belong to `127.0.0.1`. The frontend folder must be the web server root,
because the emails link to `FRONTEND_URL/pages/auth/activate.html` and
`FRONTEND_URL/pages/auth/confirm_password.html`.

## 9. Editor support (optional)

The application runs in Docker. A local virtual environment with Python 3.12
is only needed so that the editor (e.g. VS Code with Pylance) can resolve the
imports.

**macOS / Linux**

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
py -3.12 -m venv venv
venv\Scripts\pip install -r requirements.txt
```

Then select this interpreter in VS Code: *Command Palette* →
**Python: Select Interpreter** → `./venv`. `venv/` is git-ignored.
