"""Path helpers for uploaded videos and their HLS output.

Requested resolutions and segment names are validated against fixed
patterns before any path is built, so URLs cannot escape the HLS folder.
"""

import re
from pathlib import Path
from uuid import uuid4

from django.conf import settings

RESOLUTIONS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}
PLAYLIST_NAME = "index.m3u8"
# Accepts generated names (segment_000.ts) and the short form of the school
# docs (000.ts); only the captured digits are used to build the file name.
SEGMENT_PATTERN = re.compile(r"(?:segment_)?(\d{3,6})\.ts")


def video_upload_path(instance, filename):
    """Random file name, so uploads are not guessable and never collide."""
    return f"videos/{uuid4().hex}{Path(filename).suffix.lower()}"


def thumbnail_upload_path(instance, filename):
    """Random file name for uploaded and generated thumbnails."""
    return f"thumbnails/{uuid4().hex}{Path(filename).suffix.lower()}"


def hls_dir(video_id):
    """HLS folder of a video; ``int()`` rejects anything but an id."""
    return Path(settings.MEDIA_ROOT) / "hls" / str(int(video_id))


def playlist_path(video_id, resolution):
    """Playlist path for a known resolution, otherwise ``None``."""
    if resolution not in RESOLUTIONS:
        return None
    return hls_dir(video_id) / resolution / PLAYLIST_NAME


def segment_path(video_id, resolution, segment):
    """Stored file for ``000.ts`` or ``segment_000.ts``, else ``None``."""
    match = SEGMENT_PATTERN.fullmatch(segment)
    if resolution not in RESOLUTIONS or match is None:
        return None
    return hls_dir(video_id) / resolution / f"segment_{match.group(1)}.ts"
