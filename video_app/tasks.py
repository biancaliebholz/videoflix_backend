"""Django RQ jobs for converting uploaded videos in the background."""

import django_rq
from django.conf import settings

from video_app.services.processing_service import process_video


def process_video_task(video_id):
    """RQ entry point; the job fails when the conversion raises."""
    process_video(video_id)


def queue_video_processing(video_id):
    """Queue a conversion; full films need the long job timeout."""
    django_rq.enqueue(
        process_video_task,
        video_id,
        job_timeout=settings.VIDEO_PROCESSING_TIMEOUT,
    )
