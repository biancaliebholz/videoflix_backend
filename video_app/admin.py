"""Admin for uploading videos and watching their processing status."""

from django.contrib import admin, messages

from video_app.models import Video
from video_app.tasks import queue_video_processing


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Upload videos and follow their conversion status."""

    list_display = ("title", "category", "status", "duration", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "category")
    readonly_fields = ("status", "processing_error", "duration", "created_at")
    actions = ["reprocess_videos"]

    @admin.action(description="Convert selected videos again")
    def reprocess_videos(self, request, queryset):
        """Queue a new conversion, e.g. after a failure or worker restart."""
        queryset.update(status=Video.Status.PENDING, processing_error="")
        for video_id in queryset.values_list("pk", flat=True):
            queue_video_processing(video_id)
        self.message_user(
            request, f"{queryset.count()} video(s) queued.", messages.SUCCESS
        )
