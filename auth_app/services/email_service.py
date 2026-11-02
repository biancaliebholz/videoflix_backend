"""Render and send the transactional emails of the authentication flows."""

from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from auth_app.utils import (
    account_activation_token,
    build_frontend_link,
    encode_uid,
)

LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "auth_app"
LOGO_FILE = LOGO_PATH / "email_logo.png"
LOGO_CID = "videoflix-logo"


def send_activation_email(user):
    token = account_activation_token.make_token(user)
    link = build_frontend_link("activate.html", encode_uid(user), token)
    send_templated_email(user, "Confirm your email", "activation", link)


def send_templated_email(user, subject, template_name, link):
    """Send a text email with HTML alternative and inline logo.

    Uses ``auth_app/emails/<template_name>.txt`` and ``.html``.
    """
    context = {"user": user, "link": link, "logo_cid": LOGO_CID}
    message = EmailMultiAlternatives(
        subject=subject,
        body=_render(template_name, "txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    html = _render(template_name, "html", context)
    message.attach_alternative(html, "text/html")
    message.attach(_inline_logo())
    message.send()


def _render(template_name, extension, context):
    return render_to_string(
        f"auth_app/emails/{template_name}.{extension}", context
    )


def _inline_logo():
    logo = MIMEImage(LOGO_FILE.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", f"<{LOGO_CID}>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    return logo
