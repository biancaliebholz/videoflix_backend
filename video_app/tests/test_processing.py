"""Tests for the processing service, tasks and model signals."""

from pathlib import Path
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from video_app.api.serializers import DEFAULT_THUMBNAIL
from video_app.models import Video
from video_app.services.hls_service import FFmpegError
from video_app.services.processing_service import (
    delete_video_files,
    process_video,
    regenerate_thumbnail,
)
from video_app.tasks import (
    generate_thumbnail_task,
    process_video_task,
    queue_thumbnail_generation,
    queue_video_processing,
)
from video_app.tests.helpers import (
    TempMediaMixin,
    create_video,
    make_test_video,
    write_hls_files,
)
from video_app.utils import hls_dir

QUEUE_PATH = "video_app.signals.queue_video_processing"
CONVERT_PATH = "video_app.services.processing_service.convert_to_hls"
THUMBNAIL_PATH = "video_app.services.processing_service.extract_thumbnail"
GENERATION_PATH = "video_app.signals.queue_thumbnail_generation"


def upload_real_video(media_root):
    source = make_test_video(media_root / "upload.mp4", seconds=5)
    return SimpleUploadedFile("upload.mp4", source.read_bytes())


def media_files(media_root):
    return {path for path in media_root.rglob("*") if path.is_file()}


def write_output(source, output_dir, has_audio):
    """Fake conversion result: renamed output plus a leftover work folder."""
    output_dir = Path(output_dir)
    write_hls_files(int(output_dir.name))
    output_dir.with_name(f"{output_dir.name}.converting").mkdir()


def hls_folders(video_id):
    """Existing output and work folders (``.converting``/``.old``)."""
    folder = hls_dir(video_id)
    names = (folder.name, f"{folder.name}.converting", f"{folder.name}.old")
    paths = [folder.with_name(name) for name in names]
    return [path for path in paths if path.exists()]


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

    def test_video_deleted_during_conversion_leaves_no_files(self):
        video, before = self.pending_video()
        with patch(CONVERT_PATH, side_effect=self.delete_then_write(video)):
            process_video(video.pk)
        self.assert_no_leftovers(video, before)

    def test_video_deleted_before_thumbnail_leaves_no_files(self):
        video, before = self.pending_video()
        extract = self.delete_then_thumbnail(video)
        with (
            patch(THUMBNAIL_PATH, side_effect=extract),
            patch(CONVERT_PATH, side_effect=write_output),
        ):
            process_video(video.pk)
        self.assert_no_leftovers(video, before)

    def test_failed_conversion_of_deleted_video_is_cleaned_silently(self):
        video, before = self.pending_video()
        error = FileNotFoundError("work folder removed by the deletion")
        with patch(CONVERT_PATH,
                   side_effect=self.delete_then_write(video, error)):
            process_video(video.pk)
        self.assert_no_leftovers(video, before)

    def pending_video(self):
        upload = upload_real_video(self.media_root)
        before = media_files(self.media_root)
        return create_video(Video.Status.PENDING, video_file=upload), before

    def assert_no_leftovers(self, video, files_before):
        self.assertFalse(Video.objects.filter(pk=video.pk).exists())
        self.assertEqual(media_files(self.media_root), files_before)
        self.assertEqual(hls_folders(video.pk), [])

    def delete_video(self, video):
        """Delete like the admin, including the on-commit file cleanup."""
        with self.captureOnCommitCallbacks(execute=True):
            Video.objects.filter(pk=video.pk).delete()

    def delete_then_write(self, video, error=None):
        def convert(source, output_dir, has_audio):
            self.delete_video(video)
            write_output(source, output_dir, has_audio)
            if error:
                raise error
        return convert

    def delete_then_thumbnail(self, video):
        def extract(source, target, at_seconds):
            self.delete_video(video)
            Path(target).write_bytes(b"jpeg")
        return extract

    def test_delete_video_files_removes_everything(self):
        video = create_video(thumbnail=ContentFile(b"jpg", name="t.jpg"))
        folder = write_hls_files(video.pk)
        names = (video.video_file.name, video.thumbnail.name)
        delete_video_files(*names, video.pk)
        storage = video.video_file.storage
        self.assertFalse(storage.exists(video.video_file.name))
        self.assertFalse(storage.exists(video.thumbnail.name))
        self.assertFalse(folder.exists())

    def test_deleting_video_without_thumbnail_keeps_default_image(self):
        video = create_video()
        default_image = Path(finders.find(DEFAULT_THUMBNAIL))
        size = default_image.stat().st_size
        delete_video_files(video.video_file.name, video.thumbnail.name,
                           video.pk)
        self.assertEqual(default_image.stat().st_size, size)

    def test_delete_video_files_removes_work_folders_repeatedly(self):
        write_hls_files(999)
        for suffix in (".converting", ".old"):
            hls_dir(999).with_name(f"999{suffix}").mkdir()
        delete_video_files(None, None, 999)
        delete_video_files(None, None, 999)
        self.assertEqual(hls_folders(999), [])


class VideoTaskTests(TestCase):

    @patch("video_app.tasks.process_video")
    def test_task_delegates_to_service(self, process):
        process_video_task(3)
        process.assert_called_once_with(3)

    @patch("video_app.tasks.regenerate_thumbnail")
    def test_thumbnail_task_delegates_to_service(self, regenerate):
        generate_thumbnail_task(3)
        regenerate.assert_called_once_with(3)

    @patch("video_app.tasks.django_rq.enqueue")
    def test_thumbnail_generation_is_queued(self, enqueue):
        queue_thumbnail_generation(3)
        enqueue.assert_called_once_with(generate_thumbnail_task, 3)

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


@patch(QUEUE_PATH)
@patch(GENERATION_PATH)
class ThumbnailSignalTests(TempMediaMixin, TestCase):

    def test_removed_thumbnail_is_deleted_and_regenerated(self, generate,
                                                          queue):
        video = create_video(thumbnail=ContentFile(b"jpg", name="own.jpg"))
        old_name = video.thumbnail.name
        self.save_with(video, thumbnail=None)
        self.assertFalse(video.thumbnail.storage.exists(old_name))
        generate.assert_called_once_with(video.pk)
        queue.assert_not_called()

    def test_replaced_thumbnail_deletes_only_the_old_file(self, generate,
                                                          queue):
        video = create_video(thumbnail=ContentFile(b"jpg", name="own.jpg"))
        old_name = video.thumbnail.name
        self.save_with(video, thumbnail=ContentFile(b"new", name="new.jpg"))
        storage = video.thumbnail.storage
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(video.thumbnail.name))
        generate.assert_not_called()

    def test_unchanged_or_first_thumbnail_triggers_nothing(self, generate,
                                                           queue):
        with_thumbnail = create_video(
            thumbnail=ContentFile(b"jpg", name="own.jpg"))
        self.save_with(with_thumbnail, title="New title")
        without_thumbnail = create_video()
        self.save_with(without_thumbnail,
                       thumbnail=ContentFile(b"jpg", name="first.jpg"))
        storage = with_thumbnail.thumbnail.storage
        self.assertTrue(storage.exists(with_thumbnail.thumbnail.name))
        generate.assert_not_called()

    def save_with(self, video, **fields):
        """Save changed fields like the admin, running on-commit hooks."""
        with self.captureOnCommitCallbacks(execute=True):
            for name, value in fields.items():
                setattr(video, name, value)
            video.save()


class RegenerateThumbnailTests(TempMediaMixin, TestCase):

    def test_ready_video_gets_a_new_thumbnail_from_ffmpeg(self):
        video = create_video(video_file=upload_real_video(self.media_root),
                             duration=5)
        regenerate_thumbnail(video.pk)
        video.refresh_from_db()
        self.assertTrue(video.thumbnail.name.startswith("thumbnails/"))
        self.assertTrue(video.thumbnail.storage.exists(video.thumbnail.name))

    @patch(THUMBNAIL_PATH)
    def test_skips_videos_with_thumbnail_or_not_ready(self, extract):
        pending = create_video(Video.Status.PENDING)
        ready = create_video(thumbnail=ContentFile(b"jpg", name="own.jpg"))
        for video in (pending, ready):
            regenerate_thumbnail(video.pk)
        extract.assert_not_called()

    def test_thumbnail_of_video_deleted_meanwhile_is_removed(self):
        video = create_video(duration=5)
        before = media_files(self.media_root)

        def extract_then_delete(source, target, at_seconds):
            Path(target).write_bytes(b"jpeg")
            Video.objects.filter(pk=video.pk).delete()

        with patch(THUMBNAIL_PATH, side_effect=extract_then_delete):
            regenerate_thumbnail(video.pk)
        self.assertEqual(media_files(self.media_root), before)
