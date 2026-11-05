"""FFmpeg based probing, thumbnail extraction and HLS conversion.

All renditions are encoded in a single FFmpeg run: the source is decoded
once and split into 480p, 720p and 1080p. Keyframes are forced every
``SEGMENT_SECONDS`` so every segment starts with a keyframe, which keeps
seeking exact and lets players switch resolutions at segment borders.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from video_app.utils import PLAYLIST_NAME, RESOLUTIONS

SEGMENT_SECONDS = 4
CONVERTING_SUFFIX = ".converting"
OLD_SUFFIX = ".old"
MAX_BITRATES = {"480p": "1400k", "720p": "3000k", "1080p": "5500k"}


class FFmpegError(RuntimeError):
    """Raised when ffmpeg or ffprobe exits with an error."""


@dataclass(frozen=True)
class VideoInfo:
    """Facts about a source file that the conversion needs."""

    duration: float
    has_audio: bool


def probe_video(source):
    """Return duration and audio flag; ``FFmpegError`` if there is no video."""
    output = _run_command([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(source),
    ])
    data = json.loads(output)
    stream_types = {stream["codec_type"] for stream in data["streams"]}
    if "video" not in stream_types:
        raise FFmpegError("The uploaded file contains no video stream.")
    duration = float(data["format"].get("duration", 0))
    return VideoInfo(duration=duration, has_audio="audio" in stream_types)


def extract_thumbnail(source, target, at_seconds):
    """Save the frame at ``at_seconds`` as a 640 px wide JPEG to ``target``."""
    _run_command([
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-ss", f"{at_seconds:.2f}", "-i", str(source),
        "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "3", str(target),
    ])


def convert_to_hls(source, output_dir, has_audio):
    """Write all renditions to ``output_dir/<resolution>/`` atomically."""
    output_dir = Path(output_dir)
    work_dir = output_dir.with_name(f"{output_dir.name}{CONVERTING_SUFFIX}")
    shutil.rmtree(work_dir, ignore_errors=True)
    _create_rendition_dirs(work_dir)
    try:
        _run_command(build_hls_command(source, work_dir, has_audio))
    except FFmpegError:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    _replace_dir(work_dir, output_dir)


def build_hls_command(source, output_dir, has_audio):
    """Return the single-pass FFmpeg command for all renditions."""
    names = list(RESOLUTIONS)
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(source),
        "-filter_complex", _scale_filter(names),
    ]
    for index, name in enumerate(names):
        command += _stream_args(index, name, has_audio)
    return command + _hls_args(output_dir, names, has_audio)


def _scale_filter(names):
    """Split the decoded video once and fit each copy into its box."""
    split = f"[0:v]split={len(names)}" + "".join(f"[s{n}]" for n in names)
    scales = [
        f"[s{name}]scale=w={width}:h={height}:"
        f"force_original_aspect_ratio=decrease:force_divisible_by=2[v{name}]"
        for name, (width, height) in RESOLUTIONS.items()
    ]
    return ";".join([split, *scales])


def _stream_args(index, name, has_audio):
    """Map one scaled video (and the audio) with its bitrate cap."""
    max_bitrate = MAX_BITRATES[name]
    args = ["-map", f"[v{name}]"]
    if has_audio:
        args += ["-map", "0:a:0"]
    return args + [
        f"-maxrate:v:{index}", max_bitrate,
        f"-bufsize:v:{index}", f"{int(max_bitrate[:-1]) * 2}k",
    ]


def _hls_args(output_dir, names, has_audio):
    """Encoder settings and HLS muxer options shared by all renditions."""
    return [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-force_key_frames", f"expr:gte(t,n_forced*{SEGMENT_SECONDS})",
        "-sc_threshold", "0", *_audio_args(has_audio),
        "-f", "hls", "-hls_time", str(SEGMENT_SECONDS),
        "-hls_playlist_type", "vod", "-hls_flags", "independent_segments",
        "-hls_segment_filename",
        str(Path(output_dir) / "%v" / "segment_%03d.ts"),
        "-var_stream_map", _var_stream_map(names, has_audio),
        str(Path(output_dir) / "%v" / PLAYLIST_NAME),
    ]


def _audio_args(has_audio):
    """AAC stereo settings, or nothing for videos without sound."""
    return ["-c:a", "aac", "-b:a", "128k", "-ac", "2"] if has_audio else []


def _var_stream_map(names, has_audio):
    """Tell FFmpeg which streams form a rendition and name its folder."""
    return " ".join(
        f"v:{index},a:{index},name:{name}" if has_audio
        else f"v:{index},name:{name}"
        for index, name in enumerate(names)
    )


def _create_rendition_dirs(base_dir):
    """FFmpeg does not create the per-resolution folders itself."""
    for name in RESOLUTIONS:
        (base_dir / name).mkdir(parents=True, exist_ok=True)


def _replace_dir(new_dir, target_dir):
    """Swap in finished output; players never see half written playlists.

    A failed conversion never reaches this point and keeps the old files.
    """
    old_dir = target_dir.with_name(f"{target_dir.name}{OLD_SUFFIX}")
    shutil.rmtree(old_dir, ignore_errors=True)
    if target_dir.exists():
        target_dir.rename(old_dir)
    new_dir.rename(target_dir)
    shutil.rmtree(old_dir, ignore_errors=True)


def _run_command(command):
    """Run a command; raise ``FFmpegError`` with the end of its stderr."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(result.stderr.strip()[-2000:] or "ffmpeg failed")
    return result.stdout
