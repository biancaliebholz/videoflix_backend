"""Serializers of the video API."""

from django.conf import settings
from rest_framework import serializers

from video_app.models import Video

# Shared static image, never stored in a video's thumbnail field, so
# deleting a video can never delete it.
DEFAULT_THUMBNAIL = "video_app/default_thumbnail.jpg"


class VideoListSerializer(serializers.ModelSerializer):
    """Field names exactly as in the school API documentation."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id", "created_at", "title", "description", "thumbnail_url",
            "category",
        ]

    def get_thumbnail_url(self, video):
        """Absolute URL of the thumbnail, or of the default image.

        The frontend puts the value straight into ``<img src>``, so it must
        never be ``null``; a missing file also gets the default image.
        """
        thumbnail = video.thumbnail
        if thumbnail and thumbnail.storage.exists(thumbnail.name):
            url = thumbnail.url
        else:
            url = f"{settings.STATIC_URL}{DEFAULT_THUMBNAIL}"
        return self.context["request"].build_absolute_uri(url)
