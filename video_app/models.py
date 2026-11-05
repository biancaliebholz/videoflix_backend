"""Videos uploaded via the admin and converted to HLS in the background."""

from django.core.validators import FileExtensionValidator
from django.db import models

from video_app.utils import thumbnail_upload_path, video_upload_path

VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "webm", "avi", "m4v"]
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


class Video(models.Model):
    """Uploaded video with the state of its background conversion.

    Only ``ready`` videos are listed and streamed; the default ordering
    (newest first) is the order of the video list API.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class Category(models.TextChoices):
        """Genres; value and label match, the frontend groups by the value."""

        ACTION = "Action", "Action"
        ADVENTURE = "Adventure", "Adventure"
        ANIMATION = "Animation", "Animation"
        COMEDY = "Comedy", "Comedy"
        DOCUMENTARY = "Documentary", "Documentary"
        DRAMA = "Drama", "Drama"
        FANTASY = "Fantasy", "Fantasy"
        HORROR = "Horror", "Horror"
        ROMANCE = "Romance", "Romance"
        SCI_FI = "Sci-Fi", "Sci-Fi"
        THRILLER = "Thriller", "Thriller"

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=Category.choices)
    video_file = models.FileField(
        upload_to=video_upload_path,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
    )
    thumbnail = models.FileField(
        upload_to=thumbnail_upload_path,
        blank=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text="Generated from the video if left empty.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        editable=False,
    )
    processing_error = models.TextField(blank=True, editable=False)
    duration = models.FloatField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
