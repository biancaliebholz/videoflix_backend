from django.urls import path, re_path

from video_app.api.views import (
    HLSPlaylistView,
    HLSSegmentView,
    VideoListView,
)

urlpatterns = [
    path("video/", VideoListView.as_view(), name="video_list"),
    path(
        "video/<int:movie_id>/<str:resolution>/index.m3u8",
        HLSPlaylistView.as_view(),
        name="hls_playlist",
    ),
    # Players resolve segment URIs relative to the playlist, i.e. without a
    # trailing slash; the documented form ends with one. Both are accepted.
    re_path(
        r"^video/(?P<movie_id>\d+)/(?P<resolution>\w+)/"
        r"(?P<segment>[\w.-]+\.ts)/?$",
        HLSSegmentView.as_view(),
        name="hls_segment",
    ),
]
