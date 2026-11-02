from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from video_app.models import Video
from video_app.tests.helpers import TempMediaMixin, create_video


class VideoAdminTests(TempMediaMixin, TestCase):

    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="x", username="admin"
        )
        self.client.force_login(admin)

    def test_list_and_add_pages_load(self):
        create_video()
        for name in ("admin:video_app_video_changelist",
                     "admin:video_app_video_add"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    @patch("video_app.admin.queue_video_processing")
    def test_reprocess_action_resets_status_and_queues(self, queue):
        video = create_video(Video.Status.FAILED, processing_error="boom")
        self.client.post(reverse("admin:video_app_video_changelist"), {
            "action": "reprocess_videos", "_selected_action": [video.pk],
        })
        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.PENDING)
        self.assertEqual(video.processing_error, "")
        queue.assert_called_once_with(video.pk)
