"""Background processing of uploaded videos and cleanup of their files."""

import shutil
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage

from video_app.models import Video
from video_app.services.hls_service import (
    CONVERTING_SUFFIX,
    OLD_SUFFIX,
    convert_to_hls,
    extract_thumbnail,
    probe_video,
)
from video_app.utils import hls_dir


def process_video(video_id):
    """Convert a video, track its status, clean up if it was deleted."""
    video = Video.objects.filter(pk=video_id).first()
    if video is None:
        return
    _update(video, status=Video.Status.PROCESSING, processing_error="")
    try:
        _convert(video)
    except Exception as error:
        if _update(video, status=Video.Status.FAILED,
                   processing_error=str(error)):
            raise
    if not _update(video, status=Video.Status.READY):
        _discard_output(video)


def regenerate_thumbnail(video_id):
    """Recreate the thumbnail of a ready video after it was removed."""
    video = Video.objects.filter(
        pk=video_id, status=Video.Status.READY, thumbnail=""
    ).first()
    if video is None:
        return
    source = video.video_file.path
    if not _create_thumbnail(video, source, video.duration or 0):
        delete_stored_file(video.thumbnail.name)


def delete_video_files(video_file_name, thumbnail_name, video_id):
    """Delete original, thumbnail and HLS folders; safe to run repeatedly."""
    for name in (video_file_name, thumbnail_name):
        delete_stored_file(name)
    folder = hls_dir(video_id)
    for suffix in ("", CONVERTING_SUFFIX, OLD_SUFFIX):
        path = folder.with_name(f"{folder.name}{suffix}")
        shutil.rmtree(path, ignore_errors=True)


def delete_stored_file(name):
    """Delete an uploaded or generated media file; empty names are ignored."""
    if name:
        default_storage.delete(name)


def _convert(video):
    """Probe the source, then create a missing thumbnail and the HLS files."""
    source = video.video_file.path
    video_info = probe_video(source)
    _update(video, duration=video_info.duration)
    if not video.thumbnail:
        _create_thumbnail(video, source, video_info.duration)
    convert_to_hls(source, hls_dir(video.pk), video_info.has_audio)


def _create_thumbnail(video, source, duration):
    """Save a frame at 10 % of the runtime, past black intro frames.

    Returns the number of updated rows; 0 means the video was deleted.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / f"{video.pk}.jpg"
        extract_thumbnail(source, target, at_seconds=duration * 0.1)
        with target.open("rb") as image:
            video.thumbnail.save(target.name, File(image), save=False)
    return _update(video, thumbnail=video.thumbnail.name)


def _discard_output(video):
    """Remove files that a job created for an already deleted video."""
    delete_video_files(video.video_file.name, video.thumbnail.name, video.pk)


def _update(video, **fields):
    """Write fields without ``save()``; return the number of updated rows.

    Using ``update()`` keeps model signals from firing. Zero rows means the
    video was deleted in the meantime.
    """
    updated = Video.objects.filter(pk=video.pk).update(**fields)
    for name, value in fields.items():
        setattr(video, name, value)
    return updated
