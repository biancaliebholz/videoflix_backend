# Video processing and streaming

## Flow

1. An admin uploads a video in the Django admin (`/admin/video_app/video/add/`).
   The file gets a random name (`videos/<uuid>.<ext>`); the request returns as
   soon as the file is stored.
2. After the database commit, a `post_save` signal queues
   `video_app.tasks.process_video_task` in Django RQ. The video has the status
   `pending` → `processing` → `ready` (or `failed` with the FFmpeg error,
   visible in the admin; the admin action "Convert selected videos again"
   retries).
3. The job probes the file (`ffprobe`), extracts a thumbnail at 10 % of the
   runtime (unless one was uploaded) and converts the video to HLS.
4. `GET /api/video/` lists only `ready` videos. Playlists and segments are
   delivered by authenticated API views; originals and HLS files are not
   reachable under `/media/`, only thumbnails are public.

## FFmpeg settings

- One FFmpeg run decodes the source once and encodes 480p, 720p and 1080p
  (`split` filter). Each rendition fits into 854×480, 1280×720 or 1920×1080
  while keeping the aspect ratio (scope films become e.g. 1920×804).
- H.264 High (`libx264 -preset veryfast -crf 21`) with a bitrate cap per
  rendition (1.4 / 3.0 / 5.5 Mbit/s), AAC stereo 128 kbit/s.
- Keyframes are forced every 4 seconds and `-hls_time 4` cuts the segments
  there, so every segment starts with a keyframe: seeking is exact and the
  player can switch resolutions at every segment border.
- VOD playlists (`#EXT-X-PLAYLIST-TYPE:VOD`, `#EXT-X-ENDLIST`).
- Output is written to `hls/<id>.converting/` and only replaces
  `hls/<id>/` after FFmpeg succeeded, so players never see half-written
  playlists and a failed reconversion keeps the previous version.

## Replacing and deleting videos

- A new video file on an existing video sets it back to `pending`, deletes
  the old original and renditions after the commit and queues a new
  conversion. Changing only title, description or category queues nothing.
- Deleting a video removes original, thumbnail and HLS folders (including the
  temporary `hls/<id>.converting/` and `hls/<id>.old/`) after the commit.
- If a video is deleted while its job is still running, the job notices this
  when it saves the result and removes the files it created afterwards
  (renditions, thumbnail). Errors caused by the deletion do not mark the job
  as failed; errors of existing videos still do. The cleanup can run
  repeatedly without side effects.

## Measured performance (2026-11-02)

Environment: Docker Desktop on macOS, container with 16 CPU cores and 8 GB RAM,
the six demo films from [demo-videos.md](demo-videos.md).

| Film | Source | Runtime | Upload (admin, HTTP) | Conversion job | Speed |
|---|---|---|---|---|---|
| Big Buck Bunny | H.264 1080p, 276 MB | 10:35 | 9.2 s | 4:15 | 2.5× realtime |
| Sprite Fright | VP9 2048×858, 159 MB | 10:30 | 4.8 s | 3:15 | 3.2× |
| Charge | 3840×1608, 223 MB | 4:23 | 7.7 s | 2:30 | 1.8× |
| Wing It! | 1920×1080, 36 MB | 3:58 | 3.5 s | 1:27 | 2.7× |
| Hero | 2048×858, 60 MB | 3:57 | 5.2 s | 1:22 | 2.9× |
| Coffee Run | 1920×804, 29 MB | 3:05 | 2.6 s | 1:03 | 2.9× |

Output size of Big Buck Bunny: 480p 83 MB, 720p 145 MB, 1080p 261 MB
(159 segments each, all exactly 4.0 s except the last).

Playback was tested in headless Chrome through the unchanged school frontend
(login form → video list → hls.js):

- start of playback: 100–500 ms, switch to 1080p: ~100–200 ms
- seeks to arbitrary positions (2 %–95 % of the runtime): 100–400 ms
- 1080p segment request (1.6 MB): ~33 ms, time to first byte ~19 ms
- 0 dropped frames, no player errors
- the whole 1080p stream of Big Buck Bunny decodes without errors via the API

## Gunicorn configuration

The school entrypoint starts Gunicorn with its default single *sync* worker.
`gunicorn.conf.py` in the project root is picked up automatically and
switches to 2 workers × 4 threads with a 300 s timeout. Measured before and
after:

| Situation | sync, 1 worker | gthread, 2 × 4 |
|---|---|---|
| segment request while an admin upload runs | blocked up to 3.9 s | ≤ 0.14 s |
| uploads longer than 30 s | killed by worker timeout | allowed up to 300 s |
| whole 480p film fetched by an HLS client with keep-alive (ffmpeg) | 321 s | 9 s |

## Known limitation

The school entrypoint starts exactly one RQ worker for the `default` queue.
Conversions therefore run one after another. Emails are queued at the front
of the queue, but while a conversion is running they wait until it is done
(at most a few minutes for the demo films). Restarting the `web` container
during a conversion aborts the job; use the admin action to convert the video
again.
