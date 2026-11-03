"""Video list and authenticated HLS delivery for the frontend player."""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.static import serve
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from video_app.api.serializers import VideoListSerializer
from video_app.models import Video
from video_app.utils import playlist_path, segment_path

PLAYLIST_CONTENT_TYPE = "application/vnd.apple.mpegurl"
SEGMENT_CONTENT_TYPE = "video/MP2T"


class VideoListView(ListAPIView):
    """Plain JSON array of ready videos, newest first (JWT cookie)."""

    serializer_class = VideoListSerializer
    queryset = Video.objects.filter(status=Video.Status.READY)


class HLSFileView(APIView):
    """Base view that streams an HLS file of a ready video (JWT cookie)."""

    content_type = None

    def file_response(self, movie_id, path):
        """Return the file as ``FileResponse`` or raise ``Http404``."""
        is_ready = Video.objects.filter(
            pk=movie_id, status=Video.Status.READY
        ).exists()
        if not is_ready or path is None or not path.is_file():
            raise Http404("Video or manifest not found.")
        response = FileResponse(
            path.open("rb"), content_type=self.content_type
        )
        response["Cache-Control"] = "private, max-age=3600"
        return response


class HLSPlaylistView(HLSFileView):
    """HLS playlist of one resolution."""

    content_type = PLAYLIST_CONTENT_TYPE

    def get(self, request, movie_id, resolution):
        path = playlist_path(movie_id, resolution)
        return self.file_response(movie_id, path)


class HLSSegmentView(HLSFileView):
    """MPEG-TS segment; accepts ``000.ts`` and ``segment_000.ts``."""

    content_type = SEGMENT_CONTENT_TYPE

    def get(self, request, movie_id, resolution, segment):
        path = segment_path(movie_id, resolution, segment)
        return self.file_response(movie_id, path)


def thumbnail_view(request, path):
    """Serve thumbnails publicly; ``serve`` rejects paths outside the root."""
    document_root = Path(settings.MEDIA_ROOT) / "thumbnails"
    return serve(request, path, document_root=document_root)
