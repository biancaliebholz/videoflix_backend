"""Tests for the video list, the HLS endpoints and media exposure."""

from datetime import timedelta

from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from video_app.models import Video
from video_app.tests.helpers import (
    TempMediaMixin,
    authenticate,
    create_video,
    write_hls_files,
)


class VideoListApiTests(TempMediaMixin, APITestCase):

    url = reverse("video_list")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_lists_only_ready_videos_with_documented_fields(self):
        authenticate(self.client)
        video = create_video()
        create_video(Video.Status.PROCESSING, title="Not yet")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [video.id])
        self.assertEqual(set(response.data[0]), {
            "id", "created_at", "title", "description", "thumbnail_url",
            "category",
        })

    def test_thumbnail_url_is_absolute(self):
        authenticate(self.client)
        create_video(thumbnail=ContentFile(b"jpg", name="cover.jpg"))
        item = self.client.get(self.url).data[0]
        self.assertTrue(item["thumbnail_url"].startswith(
            "http://testserver/media/thumbnails/"
        ))

    def test_newest_videos_come_first(self):
        authenticate(self.client)
        older = create_video(title="Older")
        Video.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        newer = create_video(title="Newer")
        ids = [item["id"] for item in self.client.get(self.url).data]
        self.assertEqual(ids, [newer.id, older.id])


class HLSApiTests(TempMediaMixin, APITestCase):

    def setUp(self):
        authenticate(self.client)
        self.video = create_video()
        self.hls_folder = write_hls_files(self.video.pk, "480p")

    def get(self, path):
        return self.client.get(f"/api/video/{path}")

    def test_playlist_is_served_with_hls_content_type(self):
        response = self.get(f"{self.video.pk}/480p/index.m3u8")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "application/vnd.apple.mpegurl"
        )
        self.assertIn(b"#EXTM3U", b"".join(response.streaming_content))

    def test_segment_is_served_with_and_without_trailing_slash(self):
        for suffix in ("segment_000.ts/", "segment_000.ts"):
            with self.subTest(suffix=suffix):
                response = self.get(f"{self.video.pk}/480p/{suffix}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "video/MP2T")

    def test_documented_segment_url_serves_the_real_file(self):
        expected = (self.hls_folder / "segment_000.ts").read_bytes()
        for segment in ("000.ts/", "segment_000.ts/"):
            with self.subTest(segment=segment):
                response = self.get(f"{self.video.pk}/480p/{segment}")
                self.assertEqual(response.status_code, 200)
                body = b"".join(response.streaming_content)
                self.assertEqual(body, expected)

    def test_missing_or_invalid_files_return_404(self):
        pending = create_video(Video.Status.PROCESSING)
        write_hls_files(pending.pk)
        for path in (
            "999/480p/index.m3u8",
            f"{pending.pk}/480p/index.m3u8",
            f"{self.video.pk}/720p/index.m3u8",
            f"{self.video.pk}/360p/index.m3u8",
            f"{self.video.pk}/480p/segment_999.ts/",
            f"{self.video.pk}/480p/..%2F..%2Fsecret.ts/",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 404)

    def test_hls_requires_authentication(self):
        self.client.cookies.clear()
        response = self.get(f"{self.video.pk}/480p/index.m3u8")
        self.assertEqual(response.status_code, 401)


class MediaExposureTests(TempMediaMixin, APITestCase):

    def test_thumbnails_are_public(self):
        video = create_video(thumbnail=ContentFile(b"jpg", name="cover.jpg"))
        response = self.client.get(video.thumbnail.url)
        self.assertEqual(response.status_code, 200)

    def test_original_videos_and_hls_files_are_not_public(self):
        video = create_video()
        write_hls_files(video.pk)
        for path in (video.video_file.url, f"/media/hls/{video.pk}/480p/"
                     "index.m3u8"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
