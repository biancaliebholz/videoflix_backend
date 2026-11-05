"""Start processing after uploads and remove files of deleted videos."""

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from video_app.models import Video
from video_app.services.processing_service import (
    delete_stored_file,
    delete_video_files,
)
from video_app.tasks import queue_thumbnail_generation, queue_video_processing


@receiver(pre_save, sender=Video)
def remember_previous_files(sender, instance, **kwargs):
    """Keep the old file names so ``post_save`` can detect replacements."""
    previous = sender.objects.filter(pk=instance.pk).values(
        "video_file", "thumbnail"
    )
    instance._previous_files = previous.first() or {} if instance.pk else {}


@receiver(post_save, sender=Video)
def queue_processing_after_upload(sender, instance, created, **kwargs):
    """Queue the conversion once the upload is committed to the database.

    A replaced video file hides the video (status ``pending``) until the
    new file is converted; the old file and renditions are removed.
    """
    previous = getattr(instance, "_previous_files", {}).get("video_file")
    if not created and previous == instance.video_file.name:
        return
    if not created:
        pending = Video.Status.PENDING
        sender.objects.filter(pk=instance.pk).update(status=pending)
    transaction.on_commit(lambda: _restart_processing(instance.pk, previous))


@receiver(post_save, sender=Video)
def replace_changed_thumbnail(sender, instance, created, **kwargs):
    """Delete a replaced or removed thumbnail; recreate a removed one.

    Until the new thumbnail exists, the API returns the default image.
    """
    previous = getattr(instance, "_previous_files", {}).get("thumbnail")
    if created or not previous or previous == instance.thumbnail.name:
        return
    removed = not instance.thumbnail
    transaction.on_commit(
        lambda: _replace_thumbnail(instance.pk, previous, removed)
    )


@receiver(post_delete, sender=Video)
def delete_files_of_deleted_video(sender, instance, **kwargs):
    """Remove original, thumbnail and HLS files once the delete commits."""
    names = (instance.video_file.name, instance.thumbnail.name, instance.pk)
    transaction.on_commit(lambda: delete_video_files(*names))


def _restart_processing(video_id, previous_file):
    """Remove the files of a replaced upload and convert the new one."""
    if previous_file:
        delete_video_files(previous_file, None, video_id)
    queue_video_processing(video_id)


def _replace_thumbnail(video_id, previous_thumbnail, removed):
    """Delete the old thumbnail file; queue a new one if it was removed."""
    delete_stored_file(previous_thumbnail)
    if removed:
        queue_thumbnail_generation(video_id)
