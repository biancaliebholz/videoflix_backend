from django.test import SimpleTestCase, override_settings

from video_app.utils import (
    hls_dir,
    playlist_path,
    segment_path,
    thumbnail_upload_path,
    video_upload_path,
)


class UploadPathTests(SimpleTestCase):

    def test_uploads_get_random_names_with_lowercase_extension(self):
        first = video_upload_path(None, "../../Mein Film.MP4")
        second = video_upload_path(None, "../../Mein Film.MP4")
        self.assertRegex(first, r"^videos/[0-9a-f]{32}\.mp4$")
        self.assertNotEqual(first, second)

    def test_thumbnails_are_stored_separately(self):
        path = thumbnail_upload_path(None, "cover.JPG")
        self.assertRegex(path, r"^thumbnails/[0-9a-f]{32}\.jpg$")


@override_settings(MEDIA_ROOT="/media-root")
class HlsPathTests(SimpleTestCase):

    def test_playlist_path_for_known_resolution(self):
        self.assertEqual(
            str(playlist_path(5, "720p")), "/media-root/hls/5/720p/index.m3u8"
        )

    def test_unknown_resolution_is_rejected(self):
        for resolution in ("360p", "..", "720p/../../etc", ""):
            with self.subTest(resolution=resolution):
                self.assertIsNone(playlist_path(5, resolution))
                segment = segment_path(5, resolution, "segment_000.ts")
                self.assertIsNone(segment)

    def test_only_generated_segment_names_are_accepted(self):
        self.assertEqual(
            str(segment_path(5, "480p", "segment_012.ts")),
            "/media-root/hls/5/480p/segment_012.ts",
        )
        for name in ("../secret.ts", "segment_1.ts", "index.m3u8",
                     "segment_000.ts/../../x.ts", "segment_000.mp4",
                     "1.ts", "000.ts\n", "segment_000.ts\n", "x000.ts"):
            with self.subTest(name=name):
                self.assertIsNone(segment_path(5, "480p", name))

    def test_documented_short_name_maps_to_generated_file(self):
        """The school docs use ``000.ts``; files are ``segment_000.ts``."""
        self.assertEqual(
            segment_path(5, "480p", "000.ts"),
            segment_path(5, "480p", "segment_000.ts"),
        )

    def test_hls_dir_only_accepts_numeric_ids(self):
        self.assertEqual(str(hls_dir("7")), "/media-root/hls/7")
        with self.assertRaises(ValueError):
            hls_dir("../7")
