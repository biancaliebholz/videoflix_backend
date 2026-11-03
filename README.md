<div align="center">

# Videoflix Backend

**Django REST backend for a Netflix-style video platform:**
email-verified accounts, JWT in HttpOnly cookies, background video conversion
and HLS streaming in 480p, 720p and 1080p.

![Python](https://img.shields.io/badge/Python-3.12-FF9800?style=flat-square&logo=python&logoColor=FF9800&labelColor=0F172A)
![Django](https://img.shields.io/badge/Django-5.2-FF9800?style=flat-square&logo=django&logoColor=FF9800&labelColor=0F172A)
![DRF](https://img.shields.io/badge/DRF-3.18-FF9800?style=flat-square&logo=django&logoColor=FF9800&labelColor=0F172A)
![SimpleJWT](https://img.shields.io/badge/SimpleJWT-5.5-FF9800?style=flat-square&logo=jsonwebtokens&logoColor=FF9800&labelColor=0F172A)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-FF9800?style=flat-square&logo=postgresql&logoColor=FF9800&labelColor=0F172A)
![Redis](https://img.shields.io/badge/Redis-8-FF9800?style=flat-square&logo=redis&logoColor=FF9800&labelColor=0F172A)
![Django RQ](https://img.shields.io/badge/Django_RQ-4.2-FF9800?style=flat-square&labelColor=0F172A)
![FFmpeg](https://img.shields.io/badge/FFmpeg-8.1-FF9800?style=flat-square&logo=ffmpeg&logoColor=FF9800&labelColor=0F172A)
![Docker](https://img.shields.io/badge/Docker_Compose-ready-FF9800?style=flat-square&logo=docker&logoColor=FF9800&labelColor=0F172A)
![Coverage](https://img.shields.io/badge/coverage-100%25-FF9800?style=flat-square&labelColor=0F172A)

</div>

---

## Table of Contents

1. [Features](#features)
2. [Technologies & Architecture](#technologies--architecture)
3. [Quick Start](#quick-start)
4. [Frontend Integration](#frontend-integration)
5. [Authentication & Security](#authentication--security)
6. [Video Processing](#video-processing)
7. [Testing](#testing)
8. [Project Structure](#project-structure)
9. [Documentation](#documentation)

---

## Features

- Registration with email activation; accounts stay inactive until the link is opened
- Login with email and password; JWT access and refresh tokens in **HttpOnly cookies**
- Token refresh, logout with refresh-token blacklist and revocation of the current access token
- Password reset by email (link valid for 24 hours)
- Video upload in the Django admin, conversion in the background with **Django RQ**
- One FFmpeg run creates HLS renditions in **480p, 720p and 1080p** plus a thumbnail;
  the quality is chosen in the player (one playlist per resolution, no automatic bitrate switching)
- Authenticated delivery of playlists and segments, newest videos first, grouped by category in the frontend
- HTML emails based on the Developer Akademie design templates
- 147 automated tests, 100 % coverage of the application code, Postman collection for all endpoints

## Technologies & Architecture

| Area | Technology | Version |
|---|---|---|
| Language / framework | Python, Django, Django REST Framework | 3.12 / 5.2.18 / 3.18.3 |
| Authentication | djangorestframework-simplejwt (token blacklist), django-cors-headers | 5.5.1 / 4.9.0 |
| Database | PostgreSQL (`postgres:latest` image) | 18.6 at the time of writing |
| Cache & queue | Redis (`redis:latest` image), django-redis, Django RQ | 8.10.3 / 7.0.0 / 4.2.0 |
| Video | FFmpeg (installed in the Docker image) | 8.1.3 |
| Server | Gunicorn (2 workers × 4 threads), WhiteNoise | 26.2.0 / 6.12.0 |

All Python packages are pinned in [`requirements.txt`](requirements.txt).

```
Browser (school frontend, :5500) ──REST + cookies──▶ Django/DRF (:8000) ──▶ PostgreSQL
                                                         │
                         admin upload ──▶ signal ──▶ Redis queue ──▶ RQ worker ──▶ FFmpeg ──▶ HLS files
```

Each app separates responsibilities: `api/` (views, serializers, permissions),
`services/` (business logic), `tasks.py` (thin RQ jobs), `utils.py` (small
helpers) and `signals.py` (queue conversions, clean up files).

## Quick Start

You need **Docker Desktop** (macOS, Windows with WSL 2) or **Docker Engine
with the Compose plugin** (Linux), plus **git**. Detailed steps, all
environment variables and email setup: [docs/setup.md](docs/setup.md).

**macOS / Linux**

```bash
git clone https://github.com/biancaliebholz/videoflix_backend.git
cd videoflix_backend
cp .env.template .env
```

**Windows (PowerShell)**

```powershell
git clone --config core.autocrlf=input https://github.com/biancaliebholz/videoflix_backend.git
cd videoflix_backend
Copy-Item .env.template .env
```

Set at least `SECRET_KEY`, `DB_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD` and the
`EMAIL_*` values in `.env`. For local tests without SMTP add
`EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`; the emails then
appear in the container log. Start (same commands in all terminals):

```bash
docker compose up --build -d
docker compose logs -f web      # ready at "Listening at: http://0.0.0.0:8000"
```

The entrypoint runs the migrations, creates the superuser from `.env` and
starts the RQ worker and Gunicorn. API: **http://127.0.0.1:8000/api/**, admin:
**http://127.0.0.1:8000/admin/** (`DJANGO_SUPERUSER_EMAIL`); stop: `docker compose stop`.

> [!CAUTION]
> `docker compose down -v` deletes the volumes: database, uploaded videos and
> HLS files are gone. Problems: [docs/troubleshooting.md](docs/troubleshooting.md).

## Frontend Integration

The backend is built for the unchanged school frontend
**[project.Videoflix](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix)**
(separate repository, not part of this one). Clone it next to the backend,
open its folder in VS Code and start `index.html` with **Live Server**
(alternatives in [docs/setup.md](docs/setup.md#8-frontend)).

| Part | URL |
|---|---|
| Backend API | `http://127.0.0.1:8000/api/` (fixed in the frontend's `shared/js/config.js`) |
| Frontend | `http://127.0.0.1:5500` |

> [!IMPORTANT]
> Use **`http://127.0.0.1:5500`**, not `localhost:5500`: the auth cookies
> belong to `127.0.0.1`. Activation and reset emails link to
> `FRONTEND_URL/pages/auth/activate.html` and `.../confirm_password.html`.

## Authentication & Security

- **Email login** (custom user model, unique lower-case emails); activation
  and reset links are valid for 24 h, work once and use separate secrets.
- **Cookies:** `access_token` (30 min) and `refresh_token` (1 day),
  HttpOnly, `SameSite=Lax`, host-only. Inactive accounts cannot log in or use
  tokens.
- **Logout** blacklists the refresh token and revokes the access token in
  Redis; a password reset ends all sessions.
- **CSRF protection** for cookie authentication via an origin check, CORS
  only for trusted origins, JSON bodies only.
- **Generic error messages** for registration, login and password reset, so
  the API does not reveal which accounts exist.
- **Media:** originals and HLS files are served only through authenticated
  views; only thumbnails are public. Paths are built from validated values.

All ten endpoints with requests, responses and status codes:
**[docs/api.md](docs/api.md)**.

> [!NOTE]
> Deliberate deviation from the school documentation: `POST /api/register/`
> returns no activation `token`, because a usable token would bypass the email
> verification ([details](docs/api.md#1-post-apiregister)).

## Video Processing

1. Upload in the admin → the request returns as soon as the file is stored.
2. After the database commit a signal queues an RQ job in **Redis**
   (`pending` → `processing` → `ready` / `failed`).
3. **FFmpeg** decodes once and encodes 480p, 720p and 1080p (H.264 + AAC),
   keeping the aspect ratio. Keyframes every 4 s match the 4 s segments, so
   seeking is exact and all renditions share the same timeline.
4. New output replaces the old one only after a successful run; files of
   deleted videos are removed, also when the deletion happens during a
   conversion.

Redis is the main-memory layer: Django cache (django-redis, e.g. revoked
access tokens) and queue for Django RQ; the school entrypoint starts one RQ
worker, so conversions run one after another. Details and measurements:
[docs/video-processing.md](docs/video-processing.md). The six demo films
(Blender open movies, CC BY) are **not** in the repository; sources, licenses
and how to add them: [docs/demo-videos.md](docs/demo-videos.md).

## Testing

```bash
docker compose exec web python manage.py test
```

147 tests (separate test database) cover models, serializers, services,
tasks, signals, permissions and all endpoints; video tests run real FFmpeg.
Coverage is **100 %** for `auth_app`, `video_app` and `core`, excluding
migrations, tests and the Django-generated entry points `core/asgi.py` and
`core/wsgi.py` (99 % with these two files):

```bash
docker compose exec web sh -c "pip install coverage && coverage run --source=auth_app,video_app,core --omit='*/migrations/*,*/tests/*,core/asgi.py,core/wsgi.py' manage.py test && coverage report"
```

`coverage` is installed only in the running container. Code style: PEP 8
(79 characters), functions with at most 14 lines. A Postman collection with
35 requests for all endpoints: [docs/postman/](docs/postman/README.md).

## Project Structure

```
videoflix_backend/
├── auth_app/                 # users, registration, JWT cookie session, password reset
│   ├── api/                  # views, serializers, urls, authentication, permissions
│   ├── services/             # registration, email, password reset, session
│   ├── templates/auth_app/emails/
│   ├── tests/
│   ├── models.py · tasks.py · utils.py
├── video_app/                # videos and HLS streaming
│   ├── api/                  # list, playlist and segment views
│   ├── services/             # FFmpeg/HLS conversion, processing workflow
│   ├── tests/
│   ├── models.py · signals.py · tasks.py · utils.py
├── core/                     # settings, urls
├── docs/                     # API, setup, troubleshooting, videos, Postman
├── gunicorn.conf.py          # threads and upload timeout for Gunicorn
├── backend.Dockerfile · backend.entrypoint.sh · docker-compose.yml   # school files (unchanged)
├── .env.template
└── requirements.txt
```

## Documentation

| Document | Content |
|---|---|
| [docs/api.md](docs/api.md) | All ten endpoints, request rules, cookies, status codes |
| [docs/setup.md](docs/setup.md) | Setup for macOS, Windows and Linux, environment variables, email, editor support |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Typical Docker, Windows, Linux, frontend and email problems |
| [docs/video-processing.md](docs/video-processing.md) | Processing flow, FFmpeg settings, measurements, Gunicorn |
| [docs/demo-videos.md](docs/demo-videos.md) | Demo films: sources, licenses, credits, adding them |
| [docs/postman/](docs/postman/README.md) | Postman collection and how to run it |

The Docker files are provided by the Developer Akademie and stay unchanged;
`gunicorn.conf.py` is picked up by Gunicorn automatically.
