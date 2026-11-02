"""Tests for the FFmpeg command and real conversions of small videos."""

import subprocess

from django.test import SimpleTestCase

from video_app.services.hls_service import (
    FFmpegError,
    build_hls_command,
    convert_to_hls,
    extract_thumbnail,
    probe_video,
)
from video_app.tests.helpers import TempMediaMixin, make_test_video


def first_frame_is_keyframe(segment):
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-read_intervals", "%+#1", "-show_entries", "frame=key_frame",
         "-of", "csv=p=0", str(segment)],
        capture_output=True, text=True, check=True,
    ).stdout
    return output.strip().split(",")[0] == "1"


def video_height(path):
    return subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.split()[0]


class BuildCommandTests(SimpleTestCase):

    def command(self, has_audio=True):
        return " ".join(build_hls_command("in.mp4", "/out", has_audio))

    def test_one_run_creates_three_renditions(self):
        command = self.command()
        self.assertIn("split=3", command)
        self.assertIn(
            "v:0,a:0,name:480p v:1,a:1,name:720p v:2,a:2,name:1080p", command
        )

    def test_keyframes_align_with_four_second_vod_segments(self):
        command = self.command()
        self.assertIn("-force_key_frames expr:gte(t,n_forced*4)", command)
        self.assertIn("-sc_threshold 0", command)
        self.assertIn("-hls_time 4", command)
        self.assertIn("-hls_playlist_type vod", command)
        self.assertIn("/out/%v/segment_%03d.ts", command)

    def test_bitrate_caps_per_rendition(self):
        command = self.command()
        self.assertIn("-maxrate:v:0 1400k -bufsize:v:0 2800k", command)
        self.assertIn("-maxrate:v:2 5500k -bufsize:v:2 11000k", command)

    def test_videos_without_audio_map_no_audio(self):
        command = self.command(has_audio=False)
        self.assertNotIn("0:a:0", command)
        self.assertNotIn("-c:a", command)
        self.assertIn("v:0,name:480p v:1,name:720p", command)


class FFmpegIntegrationTests(TempMediaMixin, SimpleTestCase):
    """Runs the real ffmpeg binary of the container on generated videos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = make_test_video(cls.media_root / "source.mp4", seconds=9)
        cls.output = cls.media_root / "hls" / "1"
        convert_to_hls(cls.source, cls.output, has_audio=True)

    def test_probe_reports_duration_and_audio(self):
        info = probe_video(self.source)
        self.assertAlmostEqual(info.duration, 9, delta=0.2)
        self.assertTrue(info.has_audio)

    def test_probe_rejects_files_without_video(self):
        text_file = self.media_root / "notes.mp4"
        text_file.write_text("no video here")
        with self.assertRaises(FFmpegError):
            probe_video(text_file)

    def test_probe_rejects_audio_only_files(self):
        audio_only = self.media_root / "audio.m4a"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi",
             "-i", "sine=duration=1", str(audio_only)],
            check=True,
        )
        with self.assertRaisesMessage(FFmpegError, "no video stream"):
            probe_video(audio_only)

    def test_vod_playlists_are_written_for_all_resolutions(self):
        for resolution in ("480p", "720p", "1080p"):
            with self.subTest(resolution=resolution):
                playlist_file = self.output / resolution / "index.m3u8"
                playlist = playlist_file.read_text()
                self.assertIn("#EXT-X-PLAYLIST-TYPE:VOD", playlist)
                self.assertIn("#EXT-X-TARGETDURATION:4", playlist)
                self.assertIn("#EXT-X-ENDLIST", playlist)
                self.assertEqual(playlist.count("segment_"), 3)

    def test_renditions_have_target_heights(self):
        for resolution in ("480p", "720p", "1080p"):
            segment = self.output / resolution / "segment_001.ts"
            self.assertEqual(video_height(segment), resolution[:-1])

    def test_every_segment_starts_with_keyframe(self):
        segments = sorted(self.output.glob("*/segment_*.ts"))
        self.assertEqual(len(segments), 9)
        for segment in segments:
            with self.subTest(segment=segment.name):
                self.assertTrue(first_frame_is_keyframe(segment))

    def test_no_temporary_folder_is_left(self):
        self.assertFalse((self.media_root / "hls" / "1.converting").exists())

    def test_failed_conversion_keeps_previous_output(self):
        broken = self.media_root / "broken.mp4"
        broken.write_bytes(b"garbage")
        with self.assertRaises(FFmpegError):
            convert_to_hls(broken, self.output, has_audio=False)
        self.assertTrue((self.output / "480p" / "index.m3u8").exists())
        self.assertFalse((self.media_root / "hls" / "1.converting").exists())

    def test_reconversion_replaces_previous_output(self):
        output = self.media_root / "hls" / "2"
        convert_to_hls(self.source, output, has_audio=True)
        stale_file = output / "480p" / "segment_999.ts"
        stale_file.write_bytes(b"old")
        convert_to_hls(self.source, output, has_audio=True)
        self.assertFalse(stale_file.exists())
        self.assertTrue((output / "1080p" / "index.m3u8").exists())
        self.assertFalse((self.media_root / "hls" / "2.old").exists())

    def test_thumbnail_is_extracted(self):
        target = self.media_root / "thumb.jpg"
        extract_thumbnail(self.source, target, at_seconds=1)
        self.assertGreater(target.stat().st_size, 1000)
