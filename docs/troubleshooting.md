# Troubleshooting

← [Back to the README](../README.md) · [Setup guide](setup.md)

## Docker

| Problem | Solution |
|---|---|
| `Cannot connect to the Docker daemon` / `dockerDesktopLinuxEngine` / `unable to get image` | Start Docker Desktop (macOS, Windows) or the service on Linux: `sudo systemctl start docker`. |
| Linux: `permission denied ... /var/run/docker.sock` | Add your user to the `docker` group ([post-install steps](https://docs.docker.com/engine/install/linux-postinstall/)), log out and in again. |
| Windows: Docker Desktop does not start | Enable WSL 2 and virtualization as described in the [Windows install guide](https://docs.docker.com/desktop/setup/install/windows-install/). |
| `exec ./backend.entrypoint.sh: no such file or directory` | The file has CRLF line endings. Switch it to `LF` (VS Code status bar) or clone again with `core.autocrlf=input` ([setup](setup.md#2-clone-the-repositories)), then `docker compose up --build -d`. |
| `port is already allocated` (8000) | Stop the other program. Find it with `lsof -i :8000` (macOS/Linux) or `netstat -ano \| findstr :8000` (Windows). |
| Linux: files in the project belong to `root` | Files created in the container (e.g. new migrations, `.coverage`) are owned by root: `sudo chown -R "$USER":"$USER" .` |
| `.env` changes have no effect | Docker reads `.env` only when the container is created: `docker compose up -d --force-recreate --no-deps web`. |
| Migration errors after model changes | Run the commands from [Migrations and admin access](setup.md#5-migrations-and-admin-access). |

## Frontend and login

| Problem | Solution |
|---|---|
| Login works, but videos fail to load or the session is lost | Open the frontend via `http://127.0.0.1:5500`, not `localhost`; check `CSRF_TRUSTED_ORIGINS`. |
| `403 Request origin is not allowed.` | The page runs on an origin that is not in `CSRF_TRUSTED_ORIGINS`. |
| Activation or reset link shows a 404 page | The web server root must be the `videoflix_frontend` folder itself ([setup](setup.md#8-frontend)). |

## Emails and videos

| Problem | Solution |
|---|---|
| No activation or reset email | Check `docker compose logs web` for RQ or SMTP errors and the `EMAIL_*` values ([email setup](setup.md#6-email-smtp-or-console)); recreate the container after `.env` changes. |
| Emails arrive late | The school entrypoint starts one RQ worker; emails wait while a video conversion runs. |
| Video stays `pending` or `processing` | One worker converts one video at a time; follow `docker compose logs -f web`. Restarting the `web` container aborts a running conversion; use the admin action *Convert selected videos again*. |
| Video status `failed` | The admin shows the FFmpeg error in the video's detail page. |

## Editor

| Problem | Solution |
|---|---|
| VS Code / Pylance: imports such as `rest_framework_simplejwt` cannot be resolved | Create the local `venv` with all packages and select `./venv` as interpreter ([editor support](setup.md#9-editor-support-optional)). |
