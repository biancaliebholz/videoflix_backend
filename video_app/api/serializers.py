from rest_framework import serializers

from video_app.models import Video


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
        """Absolute URL, because the frontend runs on another origin."""
        if not video.thumbnail:
            return None
        return self.context["request"].build_absolute_uri(video.thumbnail.url)
