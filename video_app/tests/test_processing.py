"""Tests for the processing service, tasks and model signals."""

from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from video_app.models import Video
from video_app.services.hls_service import FFmpegError
from video_app.services.processing_service import (
    delete_video_files,
    process_video,
)
from video_app.tasks import process_video_task, queue_video_processing
from video_app.tests.helpers import (
    TempMediaMixin,
    create_video,
    make_test_video,
    write_hls_files,
)
from video_app.utils import hls_dir

QUEUE_PATH = "video_app.signals.queue_video_processing"


def upload_real_video(media_root):
    source = make_test_video(media_root / "upload.mp4", seconds=5)
    return SimpleUploadedFile("upload.mp4", source.read_bytes())


class ProcessVideoTests(TempMediaMixin, TestCase):

    def test_successful_processing_creates_renditions_and_thumbnail(self):
        video = create_video(Video.Status.PENDING,
                             video_file=upload_real_video(self.media_root))
        process_video(video.pk)
        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.READY)
        self.assertAlmostEqual(video.duration, 5, delta=0.2)
        self.assertTrue(video.thumbnail.name.startswith("thumbnails/"))
        self.assertTrue(video.thumbnail.storage.exists(video.thumbnail.name))
        self.assertTrue((hls_dir(video.pk) / "1080p" / "index.m3u8").exists())

    def test_uploaded_thumbnail_is_kept(self):
        video = create_video(
            Video.Status.PENDING,
            video_file=upload_real_video(self.media_root),
            thumbnail=SimpleUploadedFile("cover.jpg", b"jpeg"),
        )
        original = video.thumbnail.name
        process_video(video.pk)
        video.refresh_from_db()
        self.assertEqual(video.thumbnail.name, original)

    def test_failure_is_stored_and_reraised(self):
        video = create_video(Video.Status.PENDING)
        with self.assertRaises(FFmpegError):
            process_video(video.pk)
        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.FAILED)
        self.assertTrue(video.processing_error)

    def test_deleted_video_is_skipped(self):
        self.assertIsNone(process_video(999999))

    def test_delete_video_files_removes_everything(self):
        video = create_video(thumbnail=ContentFile(b"jpg", name="t.jpg"))
        folder = write_hls_files(video.pk)
        names = (video.video_file.name, video.thumbnail.name)
        delete_video_files(*names, video.pk)
        storage = video.video_file.storage
        self.assertFalse(storage.exists(video.video_file.name))
        self.assertFalse(storage.exists(video.thumbnail.name))
        self.assertFalse(folder.exists())


class VideoTaskTests(TestCase):

    @patch("video_app.tasks.process_video")
    def test_task_delegates_to_service(self, process):
        process_video_task(3)
        process.assert_called_once_with(3)

    @override_settings(VIDEO_PROCESSING_TIMEOUT=1234)
    @patch("video_app.tasks.django_rq.enqueue")
    def test_job_gets_long_timeout(self, enqueue):
        queue_video_processing(3)
        args, kwargs = enqueue.call_args
        self.assertEqual(args, (process_video_task, 3))
        self.assertEqual(kwargs["job_timeout"], 1234)


@patch(QUEUE_PATH)
class VideoSignalTests(TempMediaMixin, TestCase):

    def test_new_upload_is_queued_after_commit(self, queue):
        with self.captureOnCommitCallbacks(execute=True):
            video = create_video(Video.Status.PENDING)
        queue.assert_called_once_with(video.pk)

    def test_metadata_change_does_not_requeue(self, queue):
        video = create_video()
        with self.captureOnCommitCallbacks(execute=True):
            video.title = "New title"
            video.save()
        queue.assert_not_called()

    def test_replaced_file_hides_video_and_requeues(self, queue):
        video = create_video()
        old_name = video.video_file.name
        with self.captureOnCommitCallbacks(execute=True):
            video.video_file = SimpleUploadedFile("new.mp4", b"new")
            video.save()
        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.PENDING)
        self.assertFalse(video.video_file.storage.exists(old_name))
        queue.assert_called_once_with(video.pk)

    def test_deleting_video_removes_files(self, queue):
        video = create_video()
        folder = write_hls_files(video.pk)
        name = video.video_file.name
        with self.captureOnCommitCallbacks(execute=True):
            video.delete()
        self.assertFalse(folder.exists())
        self.assertFalse(Video.video_file.field.storage.exists(name))
