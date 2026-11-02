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
    serializer_class = VideoListSerializer
    queryset = Video.objects.filter(status=Video.Status.READY)


class HLSPlaylistView(APIView):

    def get(self, request, movie_id, resolution):
        path = playlist_path(movie_id, resolution)
        return hls_file_response(movie_id, path, PLAYLIST_CONTENT_TYPE)


class HLSSegmentView(APIView):

    def get(self, request, movie_id, resolution, segment):
        path = segment_path(movie_id, resolution, segment)
        return hls_file_response(movie_id, path, SEGMENT_CONTENT_TYPE)


def hls_file_response(movie_id, path, content_type):
    """Stream an HLS file of a ready video or raise ``Http404``."""
    is_ready = Video.objects.filter(
        pk=movie_id, status=Video.Status.READY
    ).exists()
    if not is_ready or path is None or not path.is_file():
        raise Http404("Video or manifest not found.")
    response = FileResponse(path.open("rb"), content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


def thumbnail_view(request, path):
    """Serve thumbnails publicly; ``serve`` rejects paths outside the root."""
    document_root = Path(settings.MEDIA_ROOT) / "thumbnails"
    return serve(request, path, document_root=document_root)
