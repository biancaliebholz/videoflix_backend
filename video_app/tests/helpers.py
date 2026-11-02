"""Shared fixtures: temporary media folder, test videos and HLS files."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.tests.helpers import create_user
from video_app.models import Video
from video_app.utils import hls_dir


class TempMediaMixin:
    """Run each test class with its own empty ``MEDIA_ROOT``."""

    @classmethod
    def setUpClass(cls):
        cls.media_root = Path(tempfile.mkdtemp(prefix="videoflix-test-"))
        cls._media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)


def create_video(status=Video.Status.READY, **fields):
    defaults = {
        "title": "Big Buck Bunny",
        "description": "A giant rabbit takes revenge.",
        "category": "Animation",
        "video_file": SimpleUploadedFile("film.mp4", b"not really a video"),
    }
    return Video.objects.create(status=status, **{**defaults, **fields})


def write_hls_files(video_id, resolution="480p"):
    folder = hls_dir(video_id) / resolution
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.m3u8").write_text("#EXTM3U\nsegment_000.ts\n")
    (folder / "segment_000.ts").write_bytes(b"\x47" * 188)
    return folder


def make_test_video(target, seconds=5, audio=True):
    """Render a small real H.264 video with ffmpeg's test sources."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", f"testsrc=size=640x360:rate=25:duration={seconds}",
    ]
    if audio:
        command += ["-f", "lavfi", "-i", f"sine=duration={seconds}"]
    command += ["-c:v", "libx264", "-preset", "ultrafast", "-shortest"]
    subprocess.run([*command, str(target)], check=True)
    return Path(target)


def authenticate(client):
    user = create_user()
    token = RefreshToken.for_user(user).access_token
    client.cookies["access_token"] = str(token)
    return user
