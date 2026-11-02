"""Background processing of uploaded videos and cleanup of their files."""

import shutil
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage

from video_app.models import Video
from video_app.services.hls_service import (
    convert_to_hls,
    extract_thumbnail,
    probe_video,
)
from video_app.utils import hls_dir


def process_video(video_id):
    """Create thumbnail and HLS renditions and track the status.

    A failure is stored on the video and re-raised so the RQ job is marked
    as failed as well. Deleted videos are skipped silently.
    """
    video = Video.objects.filter(pk=video_id).first()
    if video is None:
        return
    _update(video, status=Video.Status.PROCESSING, processing_error="")
    try:
        _convert(video)
    except Exception as error:
        _update(video, status=Video.Status.FAILED, processing_error=str(error))
        raise
    _update(video, status=Video.Status.READY)


def delete_video_files(video_file_name, thumbnail_name, video_id):
    for name in (video_file_name, thumbnail_name):
        if name:
            default_storage.delete(name)
    shutil.rmtree(hls_dir(video_id), ignore_errors=True)


def _convert(video):
    source = video.video_file.path
    info = probe_video(source)
    _update(video, duration=info.duration)
    if not video.thumbnail:
        _create_thumbnail(video, source, info.duration)
    convert_to_hls(source, hls_dir(video.pk), info.has_audio)


def _create_thumbnail(video, source, duration):
    """Use a frame at 10 % of the runtime, past black intro frames."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / f"{video.pk}.jpg"
        extract_thumbnail(source, target, at_seconds=duration * 0.1)
        with target.open("rb") as image:
            video.thumbnail.save(target.name, File(image), save=False)
    _update(video, thumbnail=video.thumbnail.name)


def _update(video, **fields):
    """Write fields without ``save()`` so no model signals fire."""
    Video.objects.filter(pk=video.pk).update(**fields)
    for name, value in fields.items():
        setattr(video, name, value)
