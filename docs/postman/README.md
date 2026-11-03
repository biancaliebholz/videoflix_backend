# Postman collection

← [Back to the README](../../README.md) · [API reference](../api.md)

| File | Content |
|---|---|
| [`Videoflix.postman_collection.json`](Videoflix.postman_collection.json) | 35 requests with tests for all ten endpoints, including 400, 401 and 404 cases |
| [`Videoflix.local.postman_environment.json`](Videoflix.local.postman_environment.json) | Local environment: `base_url`, `frontend_origin`, `video_id`, `resolution`, `segment` |

## Contents of the collection

1. **Registration & activation:** password mismatch, registration (no
   activation token in the response), duplicate email, login before
   activation (400, no cookies), invalid and valid activation link, reuse of
   the link.
2. **Session & videos:** 401 for the video list, playlist and segment without
   login, refresh and logout without cookie (400), wrong password, login
   (HttpOnly cookies), video list (fields, newest first), playlist and segment
   (content types, MPEG-TS sync byte), 404 for unknown resolution, video and
   segment, token refresh, logout, 401 after logout and for the blacklisted
   refresh token.
3. **Password reset:** invalid email format, unknown and registered email
   (same answer), invalid link, password mismatch, reset, reuse of the link,
   login with old (400) and new password (200), logout.

## Run it

1. Start the backend and switch to the **console email backend**, so no real
   emails are sent:

   ```env
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
   ```

   Apply with `docker compose up -d --force-recreate --no-deps web`
   (see [setup](../setup.md#6-email-smtp-or-console)).
2. Import both files in Postman (*Import* → select the two JSON files) and
   select the environment **Videoflix local**.
3. Delete stored cookies for `127.0.0.1` (*Cookies* below the *Send* button).
4. Send the requests in order. Two requests need values from an email:
   - after *Register – success*: copy the activation link from
     `docker compose logs web` into the collection variable `activation_link`;
   - after *Password reset – registered email*: copy the reset link into
     `reset_link`.

   The pre-request scripts extract `uid` and `token` from the links.

## How it works

- **Credentials:** `test_email`, `test_password` and `new_password` are
  generated per run by the collection pre-request script. The files contain
  no real passwords, tokens or SMTP data.
- **Cookies:** the login sets the HttpOnly cookies; Postman's cookie jar sends
  them with the following requests.
- **Origin:** every request sends `Origin: {{frontend_origin}}`, because the
  backend rejects POST requests with auth cookies from unknown origins.
- **Blacklist check:** the login test keeps the refresh token in
  `old_refresh_token` only until *Token refresh – blacklisted refresh token*,
  which removes the variable again.
- **Video:** if `video_id` is not in the video list, the first listed video is
  used for the HLS requests.

## Clean up

The API has no endpoint to delete users. Remove the test users afterwards:

```bash
docker compose exec web python manage.py shell -c "from auth_app.models import User; print(User.objects.filter(email__startswith='postman.', email__endswith='@example.com').delete())"
```

Afterwards remove the `EMAIL_BACKEND` line from `.env` again if you use SMTP
and recreate the container.

## Verification status

The collection was executed against the running backend with a minimal
script runner that reads the collection file (Newman was not installed):
35/35 requests and 65/65 assertions passed. An import and run in the
Postman app itself has not been performed yet.
