<div align="center">

# Videoflix Backend

**Django REST backend for a Netflix-style video platform:**
email-verified accounts, JWT in HttpOnly cookies, background video conversion
and adaptive HLS streaming in 480p, 720p and 1080p.

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
2. [Technologies](#technologies)
3. [Quick Start](#quick-start)
4. [Frontend Integration](#frontend-integration)
5. [Authentication](#authentication)
6. [API Endpoints](#api-endpoints)
7. [Permissions & Security](#permissions--security)
8. [Video Processing & HLS Streaming](#video-processing--hls-streaming)
9. [Demo Videos](#demo-videos)
10. [Testing](#testing)
11. [Admin Interface](#admin-interface)
12. [Project Structure](#project-structure)
13. [Notes](#notes)

---

## Features

- Registration with email activation (account stays inactive until the link is opened)
- Login with email and password; JWT access and refresh tokens in **HttpOnly cookies**
- Token refresh, logout with refresh-token blacklist and revocation of the current access token
- Password reset by email (link valid for 24 hours)
- Video upload in the Django admin, conversion in the background with **Django RQ**
- One FFmpeg run creates **HLS** renditions in 480p, 720p and 1080p plus a thumbnail
- Authenticated delivery of playlists and segments, newest videos first, grouped by category in the frontend
- HTML emails based on the Developer Akademie design templates
- 143 automated tests, 100 % coverage of the application code

## Technologies

| Area | Technology | Version |
|---|---|---|
| Language | Python | 3.12 (`python:3.12-alpine` image) |
| Framework | Django / Django REST Framework | 5.2.18 / 3.18.3 |
| Authentication | djangorestframework-simplejwt (with token blacklist) | 5.5.1 |
| CORS | django-cors-headers | 4.9.0 |
| Database | PostgreSQL (`postgres:latest` image) | 18.6 at the time of writing |
| Cache & queue | Redis (`redis:latest` image), django-redis, Django RQ | 8.10.3 / 7.0.0 / 4.2.0 |
| Video | FFmpeg (installed in the Docker image) | 8.1.3 |
| Server | Gunicorn, WhiteNoise | 26.2.0 / 6.12.0 |

All Python packages are pinned in [`requirements.txt`](requirements.txt).

## Quick Start

Docker is the intended way to run the project. You need **Docker Desktop**
(or Docker Engine with the Compose plugin) and **git**.

### 1. Get the code and create the `.env` file

**macOS / Linux**

```bash
cd videoflix_backend
cp .env.template .env
```

**Windows (PowerShell)**

```powershell
cd videoflix_backend
Copy-Item .env.template .env
```

> [!IMPORTANT]
> On Windows, `backend.entrypoint.sh` must keep **LF** line endings.
> If git converted it to CRLF, the container stops with
> `exec ./backend.entrypoint.sh: no such file or directory`
> (see [Troubleshooting](#troubleshooting)).

### 2. Adjust the `.env` values

Replace at least `SECRET_KEY`, the `DB_*` values and the `EMAIL_*` values.
Do not rename or delete existing variables.

### 3. Build and start

```bash
docker compose up --build
```

The entrypoint waits for PostgreSQL, collects static files, runs the
migrations, creates the superuser from the `.env` values, starts the RQ worker
and finally Gunicorn on **http://127.0.0.1:8000**.

### Environment variables

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
| `EMAIL_BACKEND` | Django email backend; use `django.core.mail.backends.console.EmailBackend` to print emails to the container log | SMTP backend |
| `AUTH_COOKIE_SECURE` | Send auth cookies only via HTTPS | `False` |
| `AUTH_COOKIE_SAMESITE` | SameSite attribute of the auth cookies | `Lax` |
| `VIDEO_PROCESSING_TIMEOUT` | Maximum seconds for one conversion job | `10800` |

### Migrations inside the container

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

## Frontend Integration

The backend is built for the unchanged school frontend:
**https://github.com/Developer-Akademie-Backendkurs/project.Videoflix**

| Part | URL |
|---|---|
| Backend API | `http://127.0.0.1:8000/api/` (fixed in the frontend's `config.js`) |
| Frontend (VS Code Live Server) | `http://127.0.0.1:5500` |

> [!IMPORTANT]
> Open the frontend via **`http://127.0.0.1:5500`**, not `http://localhost:5500`.
> The auth cookies belong to `127.0.0.1`; from `localhost` the browser treats
> the API as a different site and does not send them.

Activation and password reset emails link to
`FRONTEND_URL/pages/auth/activate.html` and
`FRONTEND_URL/pages/auth/confirm_password.html`.

## Authentication

- **Email login:** custom user model `auth_app.User`; the email is unique,
  normalized to lower case and used as login name.
- **Activation:** new users are inactive. The activation link (valid 24 h,
  single use) is sent by a background job.
- **JWT in HttpOnly cookies:** `access_token` (30 min) and `refresh_token`
  (1 day), `SameSite=Lax`, host-only, not readable by JavaScript.
  The frontend refreshes the access token every 20 minutes.
- **Logout:** deletes both cookies, blacklists the refresh token and revokes
  the still valid access token in Redis until it expires.
- **Password reset:** same answer for known and unknown addresses; a reset
  ends all existing sessions of the user.

## API Endpoints

| Method | Endpoint | Auth | Success | Description |
|---|---|---|---|---|
| POST | `/api/register/` | – | 201 | Create an inactive user, send activation email |
| GET | `/api/activate/<uidb64>/<token>/` | – | 200 | Activate the account |
| POST | `/api/login/` | – | 200 | Set `access_token` and `refresh_token` cookies |
| POST | `/api/logout/` | refresh cookie | 200 | Delete cookies, blacklist refresh token |
| POST | `/api/token/refresh/` | refresh cookie | 200 | New `access_token` cookie |
| POST | `/api/password_reset/` | – | 200 | Send reset email |
| POST | `/api/password_confirm/<uidb64>/<token>/` | – | 200 | Set a new password |
| GET | `/api/video/` | JWT | 200 | JSON array of ready videos, newest first |
| GET | `/api/video/<movie_id>/<resolution>/index.m3u8` | JWT | 200 | HLS playlist (`application/vnd.apple.mpegurl`) |
| GET | `/api/video/<movie_id>/<resolution>/<segment>/` | JWT | 200 | HLS segment (`video/MP2T`) |

`resolution` is `480p`, `720p` or `1080p`. Segments are stored as
`segment_000.ts`; the short form `000.ts` from the school documentation is
accepted as well, with or without trailing slash.

**Differences to the school documentation (on purpose):**

- `POST /api/register/` returns `{"user": {"id", "email"}}` **without** the
  documented `token`. A usable activation token in the response would let
  anyone register a foreign address and activate it without access to the
  inbox. The frontend does not read this response.
- `POST /api/token/refresh/` returns `access` in the JSON body as documented.
  The cookie remains the actual authentication; the body is only readable by
  the trusted frontend origin (CORS and origin check).

## Permissions & Security

- Video endpoints require a valid, non-revoked access cookie (HTTP 401 otherwise).
- **CSRF protection** for cookie authentication: unsafe requests must come
  from an origin in `CSRF_TRUSTED_ORIGINS`; a request that carries auth
  cookies without an `Origin` header is rejected. Only JSON bodies are accepted.
- **CORS** only for the configured origins, with credentials.
- Generic error messages for login, registration and password reset, so the
  API does not reveal which accounts exist.
- Activation and reset tokens use separate secrets and cannot be swapped.
- Uploaded files get random names; HLS paths are built only from a fixed
  resolution list and segment numbers (no path traversal).
- Original uploads and HLS files are **not** public under `/media/`;
  only thumbnails are.

## Video Processing & HLS Streaming

1. Upload in the admin → the request returns as soon as the file is stored.
2. After the database commit an RQ job converts the video
   (`pending` → `processing` → `ready` / `failed`).
3. FFmpeg decodes once and encodes 480p, 720p and 1080p (H.264 + AAC),
   keeping the aspect ratio. Keyframes every 4 s match the 4 s segments, so
   seeking is exact.
4. New output replaces the old one only after a successful run.

Measured on the demo films: conversion at 1.8–3.2× realtime, playback start
and seeks in 100–500 ms in Chrome via the school frontend, no dropped frames.
Details, FFmpeg settings and measurements: [`docs/video-processing.md`](docs/video-processing.md).

## Demo Videos

Six complete short films (3–10.5 min) by the Blender Foundation / Blender
Studio, all under Creative Commons Attribution licenses. The credit is part of
each video description.

| Film | Runtime | License |
|---|---|---|
| Big Buck Bunny | 10:35 | CC BY 3.0 |
| Sprite Fright | 10:30 | CC BY 4.0 |
| Charge | 4:23 | CC BY 4.0 |
| Wing It! | 3:58 | CC BY 4.0 |
| Hero | 3:57 | CC BY 4.0 |
| Coffee Run | 3:05 | CC BY 4.0 |

The video files are not part of the repository. Sources, download links,
credits and resolutions: [`docs/demo-videos.md`](docs/demo-videos.md).

## Testing

```bash
docker compose exec web python manage.py test
```

The suite (143 tests) uses a separate test database and covers models,
serializers, services, tasks, signals, permissions and all endpoints.
The video tests run the real FFmpeg binary on generated test videos.

Coverage (installs `coverage` temporarily in the running container; it is
gone after the next image build):

```bash
docker compose exec web sh -c "pip install coverage && \
  coverage run --source=auth_app,video_app,core \
  --omit='*/migrations/*,*/tests/*,core/asgi.py,core/wsgi.py' \
  manage.py test && coverage report"
```

## Admin Interface

Open **http://127.0.0.1:8000/admin/** and log in with
`DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`
(the login field is the **email address**).

- **Users:** email-based user admin with activation status
- **Videos:** upload title, description, category and video file (thumbnail
  optional, otherwise generated); watch the processing status and errors;
  action *Convert selected videos again*

## Project Structure

```
videoflix_backend/
├── auth_app/                 # users and authentication
│   ├── api/                  # views, serializers, urls, authentication, permissions
│   ├── services/             # registration, email, password reset, JWT session
│   ├── templates/auth_app/emails/
│   ├── tests/
│   ├── models.py             # User + UserManager (email login)
│   ├── tasks.py              # RQ email jobs
│   └── utils.py              # tokens, links, cookies, origin check
├── video_app/                # videos and HLS streaming
│   ├── api/                  # list, playlist and segment views
│   ├── services/             # FFmpeg/HLS conversion, processing workflow
│   ├── tests/
│   ├── models.py             # Video with processing status
│   ├── signals.py            # queue conversion after upload, clean up files
│   ├── tasks.py              # RQ conversion job
│   └── utils.py              # upload and HLS path helpers
├── core/                     # settings, urls
├── docs/                     # demo videos, video processing details
├── gunicorn.conf.py          # threads and upload timeout for Gunicorn
├── backend.Dockerfile        # school file (unchanged)
├── backend.entrypoint.sh     # school file (unchanged)
├── docker-compose.yml        # school file (unchanged)
├── .env.template
└── requirements.txt
```

## Notes

- The Docker files (`backend.Dockerfile`, `docker-compose.yml`,
  `backend.entrypoint.sh`) are provided by the Developer Akademie and must
  stay unchanged. `gunicorn.conf.py` is read by Gunicorn automatically and
  replaces the default single sync worker with 2 workers × 4 threads.
- The entrypoint starts one RQ worker: conversions run one after another, and
  emails wait while a conversion is running. Restarting the `web` container
  aborts a running conversion; use the admin action to convert again.
- Without real SMTP credentials, set
  `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` in `.env`
  and read the emails with `docker compose logs web`.
- Never commit `.env`. Uploaded media lives in the Docker volume
  `videoflix_media`.

### Troubleshooting

- **`unable to get image 'postgres:latest'` / `dockerDesktopLinuxEngine`:**
  start Docker Desktop first.
- **`exec ./backend.entrypoint.sh: no such file or directory`:** save
  `backend.entrypoint.sh` with LF line endings (e.g. in VS Code, status bar
  `CRLF` → `LF`) and rebuild.
- **Migration errors after model changes:** run the migration commands from
  [Migrations inside the container](#migrations-inside-the-container).
