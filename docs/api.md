# API reference

Base URL: `http://127.0.0.1:8000/api/`. Request bodies are JSON
(`Content-Type: application/json`); other content types are rejected.

← [Back to the README](../README.md)

## Overview

| # | Method | Endpoint | Auth | Success |
|---|---|---|---|---|
| 1 | POST | [`/api/register/`](#1-post-apiregister) | – | 201 |
| 2 | GET | [`/api/activate/<uidb64>/<token>/`](#2-get-apiactivateuidb64token) | – | 200 |
| 3 | POST | [`/api/login/`](#3-post-apilogin) | – | 200 |
| 4 | POST | [`/api/logout/`](#4-post-apilogout) | refresh cookie | 200 |
| 5 | POST | [`/api/token/refresh/`](#5-post-apitokenrefresh) | refresh cookie | 200 |
| 6 | POST | [`/api/password_reset/`](#6-post-apipassword_reset) | – | 200 |
| 7 | POST | [`/api/password_confirm/<uidb64>/<token>/`](#7-post-apipassword_confirmuidb64token) | – | 200 |
| 8 | GET | [`/api/video/`](#8-get-apivideo) | JWT | 200 |
| 9 | GET | [`/api/video/<movie_id>/<resolution>/index.m3u8`](#9-get-apivideomovie_idresolutionindexm3u8) | JWT | 200 |
| 10 | GET | [`/api/video/<movie_id>/<resolution>/<segment>/`](#10-get-apivideomovie_idresolutionsegment) | JWT | 200 |

## Authentication and request rules

- **Cookies:** the login sets the HttpOnly cookies `access_token` (30 min)
  and `refresh_token` (1 day), `SameSite=Lax`, host-only. Clients send them
  automatically (`credentials: 'include'` in the browser); the tokens are
  never needed in headers. The school frontend calls the refresh endpoint
  every 20 minutes.
- **JWT** means a valid, non-revoked `access_token` cookie. Missing or
  invalid tokens and tokens of inactive users return **401**.
- **Origin check (CSRF protection):** an unsafe request (POST) with an
  `Origin` header must come from an origin in `CSRF_TRUSTED_ORIGINS`; a POST
  that carries auth cookies must send one. Otherwise the answer is **403**
  `{"detail": "Request origin is not allowed."}`. Requests without cookies
  and without `Origin` (e.g. curl) are allowed.
- **CORS** is enabled with credentials for the trusted origins
  (default `http://localhost:5500`, `http://127.0.0.1:5500`).

## Authentication endpoints

### 1. POST `/api/register/`

```json
{ "email": "user@example.com", "password": "securepassword", "confirmed_password": "securepassword" }
```

**201** – the user is created **inactive**, the activation email is sent by
a background job:

```json
{ "user": { "id": 1, "email": "user@example.com" } }
```

**400** – field errors, e.g. `{"confirmed_password": ["Passwords do not match."]}`,
`{"password": ["This password is too short. ..."]}` (Django password
validators) or `{"email": ["Enter a valid email address."]}`. An address that
is already registered gets the generic
`{"email": ["Please check your input and try again."]}`.

The optional field `privacy_policy` (sent by the school frontend) must be
`true` when present; requests without it are valid.

> [!NOTE]
> **Deliberate deviation:** the school documentation also lists an activation
> `token` in this response. It is omitted on purpose: a usable token in the
> response would let anyone register a foreign address and activate it
> without access to the inbox. The frontend does not read this response.

### 2. GET `/api/activate/<uidb64>/<token>/`

Parameters from the activation link: base64 encoded user id and token
(valid 24 h, single use).

**200** `{"message": "Account successfully activated."}`
**400** `{"message": "Activation failed. The link is invalid or expired."}`

### 3. POST `/api/login/`

```json
{ "email": "user@example.com", "password": "securepassword" }
```

**200** – sets `access_token` and `refresh_token`:

```json
{ "detail": "Login successful", "user": { "id": 1, "username": "user@example.com" } }
```

**400** `{"detail": ["Please check your input and try again."]}` – the same
for unknown emails, wrong passwords and inactive accounts; no cookies are set.

### 4. POST `/api/logout/`

Empty body, refresh cookie required.

**200** – deletes both cookies, blacklists the refresh token and revokes the
still valid access token (stored in Redis until it would expire):

```json
{ "detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid." }
```

**400** `{"detail": "Refresh token missing."}`

### 5. POST `/api/token/refresh/`

Empty body, refresh cookie required.

**200** – sets a new `access_token` cookie:

```json
{ "detail": "Token refreshed", "access": "new_access_token" }
```

**400** `{"detail": "Refresh token missing."}` ·
**401** invalid, expired or blacklisted refresh token, or inactive user.

The `access` field follows the school documentation. The cookie remains the
actual authentication; the body is readable only by the trusted frontend
origin (CORS and origin check).

### 6. POST `/api/password_reset/`

```json
{ "email": "user@example.com" }
```

**200** for registered and unknown addresses alike (no account
enumeration); only active accounts receive the email:

```json
{ "detail": "An email has been sent to reset your password." }
```

**400** `{"email": ["Enter a valid email address."]}`

### 7. POST `/api/password_confirm/<uidb64>/<token>/`

Parameters from the reset link (valid 24 h, invalid after use).

```json
{ "new_password": "newsecurepassword", "confirm_password": "newsecurepassword" }
```

**200** – saves the new password and ends all existing sessions
(all refresh tokens of the user are blacklisted):

```json
{ "detail": "Your Password has been successfully reset." }
```

**400** `{"detail": "The reset link is invalid or has expired."}`,
`{"confirm_password": ["Passwords do not match."]}` or
`{"new_password": [...]}` (Django password validators).

## Video endpoints

### 8. GET `/api/video/`

**200** – plain JSON array (no pagination wrapper) of all videos with status
`ready`, newest first (`created_at` descending):

```json
[
  {
    "id": 1,
    "created_at": "2026-11-02T14:30:00.123456Z",
    "title": "Big Buck Bunny",
    "description": "A giant, good-natured rabbit takes revenge ...",
    "thumbnail_url": "http://127.0.0.1:8000/media/thumbnails/<name>.jpg",
    "category": "Animation"
  }
]
```

**401** `{"detail": "Authentication credentials were not provided."}`

Thumbnails are the only public media files; the frontend groups the videos
by `category`.

### 9. GET `/api/video/<movie_id>/<resolution>/index.m3u8`

`resolution`: `480p`, `720p` or `1080p`. The path ends exactly on
`index.m3u8` (no trailing slash).

**200** – HLS VOD playlist, `Content-Type: application/vnd.apple.mpegurl`
**401** without valid JWT ·
**404** `{"detail": "Video or manifest not found."}` (unknown video, video not
`ready`, unknown resolution)

### 10. GET `/api/video/<movie_id>/<resolution>/<segment>/`

`segment`: the documented short form `000.ts` or the stored file name
`segment_000.ts`, with or without trailing slash (players request segment
URIs relative to the playlist, i.e. without slash).

**200** – binary MPEG-TS data, `Content-Type: video/MP2T`
**401** without valid JWT ·
**404** `{"detail": "Video or manifest not found."}`

Segment names are validated against a fixed pattern before a file path is
built, so requests cannot leave the HLS folder.

## Try it

A Postman collection with requests and tests for all ten endpoints is in
[`docs/postman/`](postman/README.md).
