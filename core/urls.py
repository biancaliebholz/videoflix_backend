"""Root URL configuration of the Videoflix backend."""

from django.contrib import admin
from django.urls import include, path, re_path

from video_app.api.views import thumbnail_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("auth_app.api.urls")),
    path("api/", include("video_app.api.urls")),
    # Only thumbnails are public; originals and HLS files are served by
    # authenticated API views.
    re_path(r"^media/thumbnails/(?P<path>.+)$", thumbnail_view),
]
