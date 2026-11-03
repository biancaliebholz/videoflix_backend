# Demo videos: sources and licenses

The demo uses six short films from the Blender Foundation / Blender Studio.
All of them are published under a Creative Commons Attribution license,
which allows copying, streaming and converting them as long as the creator
is credited. The credit is part of each video description, so it is shown
in the frontend next to the film.

The video files are **not** part of this repository (they are 30–280 MB
each). Download them from the sources below and upload them via the Django
admin (`/admin/video_app/video/add/`).

| Title | Year | Runtime | Category | License | Required credit |
|---|---|---|---|---|---|
| Big Buck Bunny | 2008 | 10:34.6 | Animation | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | (c) copyright 2008, Blender Foundation / www.bigbuckbunny.org |
| Sprite Fright | 2021 | 10:29.9 | Comedy | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blender Studio |
| Charge | 2022 | 4:22.7 | Action | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blender Studio |
| Wing It! | 2023 | 3:57.9 | Comedy | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blender Studio |
| Hero | 2018 | 3:56.7 | Action | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blender Foundation |
| Coffee Run | 2020 | 3:04.6 | Drama | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blender Foundation |

Runtimes are the values measured with `ffprobe` on the downloaded files; the
same values are stored as `duration` after processing.

## Full or trimmed, resolutions

All six films were uploaded **complete** (including credits), without any
trimming or re-encoding before the upload. The Big Buck Bunny file is the 2013
"sunflower" 1080p/30 fps render of the 2008 film published by the Blender
Foundation; content and license are the same.

| Title | Source file | Created HLS renditions (480p / 720p / 1080p) |
|---|---|---|
| Big Buck Bunny | H.264, 1920×1080, 30 fps | 854×480 / 1280×720 / 1920×1080 |
| Sprite Fright | VP9, 2048×858, 24 fps | 854×358 / 1280×536 / 1920×804 |
| Charge | VP9, 3840×1608, 24 fps | 854×358 / 1280×536 / 1920×804 |
| Wing It! | VP9, 1920×1080, 24 fps | 854×480 / 1280×720 / 1920×1080 |
| Hero | VP9, 2048×858, 23.976 fps | 854×358 / 1280×536 / 1920×804 |
| Coffee Run | VP9, 1920×804, 24 fps | 854×358 / 1280×536 / 1920×804 |

Wide films keep their aspect ratio inside the 16:9 box of each rendition.

## Local storage

- Downloaded originals: a folder next to the repository (`../demo_videos/`),
  never inside the Git repository.
- After the upload, inside the Docker volume `videoflix_media`
  (mounted at `/app/media`):
  - original upload: `media/videos/<random-name>.<ext>`
  - HLS output: `media/hls/<video id>/<480p|720p|1080p>/index.m3u8` and `segment_000.ts` …
  - thumbnail: `media/thumbnails/<random-name>.jpg`

## Adding the films

1. Download the films from the sources below.
2. Open **http://127.0.0.1:8000/admin/** → *Videos* → *Add video*. Enter the
   title, the description from [below](#descriptions-used-in-the-demo) (it
   contains the credit) and the category from the table above, choose the
   file and save. A thumbnail is optional; without one, it is generated.
3. Reload the video list in the admin: the status changes from `pending` to
   `processing` to `ready`. Only `ready` videos appear in the frontend.
   Conversions run one after another (one RQ worker).

## Download sources

| Title | File | Source |
|---|---|---|
| Big Buck Bunny | `bbb_sunflower_1080p_30fps_normal.mp4` (276 MB, inside a zip) | https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip — license: https://peach.blender.org/about/ |
| Sprite Fright | `Sprite_Fright_-_Blender_Open_Movie-full_movie.webm` (159 MB) | https://commons.wikimedia.org/wiki/File:Sprite_Fright_-_Blender_Open_Movie-full_movie.webm |
| Charge | `Charge_-_Blender_Open_Movie-full_movie.webm` (223 MB) | https://commons.wikimedia.org/wiki/File:Charge_-_Blender_Open_Movie-full_movie.webm |
| Wing It! | `WING_IT!_-_Blender_Open_Movie-full_movie.webm` (36 MB) | https://commons.wikimedia.org/wiki/File:WING_IT!_-_Blender_Open_Movie-full_movie.webm |
| Hero | `HERO_-_Blender_Open_Movie-full_movie.webm` (60 MB) | https://commons.wikimedia.org/wiki/File:HERO_-_Blender_Open_Movie-full_movie.webm |
| Coffee Run | `Coffee_Run_-_Blender_Open_Movie-full_movie.webm` (29 MB) | https://commons.wikimedia.org/wiki/File:Coffee_Run_-_Blender_Open_Movie-full_movie.webm |

License, author and runtime of the Wikimedia Commons files were taken from
the Commons file pages (metadata as of 2026-11-02). Big Buck Bunny's license
is stated on the official project page linked above.

## Descriptions used in the demo

- **Big Buck Bunny:** A giant, good-natured rabbit takes revenge on three bullying rodents. Blender Foundation, 2008 (CC BY 3.0).
- **Sprite Fright:** A group of rowdy teenagers on a nature trip meets a mushroom-like forest people with a dark side. Blender Studio, 2021 (CC BY 4.0).
- **Charge:** In a dystopian future, an old energy thief breaks into a heavily guarded facility and faces a deadly robot. Blender Studio, 2022 (CC BY 4.0).
- **Wing It!:** A cat and a frog try to fly a rickety homemade rocket ship out of their barn. Blender Studio, 2023 (CC BY 4.0).
- **Hero:** A Grease Pencil showcase: a young woman fights her way through an ancient arena. Blender Foundation, 2018 (CC BY 4.0).
- **Coffee Run:** Fueled by caffeine, a young woman runs through the bittersweet memories of her past relationship. Blender Foundation, 2020 (CC BY 4.0).
