# Labelling a video

Videos get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon incorporated into the picture of a new video file, the **Labelled Copy**. The original file is never changed. Only local files are labelled: a URL to download or a live stream is out of scope, and so is audio on its own.

This version checks the tools and inspects the video, but **cannot produce a Labelled Copy yet**: no rendering path is validated. Say so plainly; don't promise a result.

## Tools

Video work needs FFmpeg's `ffmpeg` and `ffprobe`, installed on the user's machine. The plugin never installs or downloads them, and images, documents and sites never need them.

## Steps

1. **Check the tools.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-tools
   ```

   It prints `ready`, each tool's `status` (`available`, `missing`, or `unusable`: found, but it doesn't run) and, when `ready` is false, `install`: the `steps` for the user's `platform` and what to do `after`. Give the user those steps as written, ask them to install the tools, and wait. When they say they are done, run `video-tools` again. Never run an install command yourself. Done when `ready` is true.

   When `ready` is true it also lists `capabilities`: the decoders, encoders, filters, pixel formats and muxers this FFmpeg build has. A capability is not a validated labelling path: never tell the user a video can be labelled because its codec is listed.
2. **Inspect the video.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-inspect <video>
   ```

   It only reads the file, and prints its `container`, `video` (codec, dimensions as stored and as displayed, `rotation`, frame rate and whether it is constant, `pix_fmt`, `bit_depth` and `colour`, with its `dynamic_range`: `sdr`, `hdr10`, `hlg`, or another HDR profile), its `audio`, `subtitles` and `other_streams`, and `labelling`: whether it can be labelled (`supported`) and the `issues` in the way. Done when the command exits 0. On an error, act on `error.code`:
   - `video_tools_missing`: go back to step 1.
   - `unreadable_video`: the file isn't a video ffprobe can read: tell the user what `error.message` says and stop.
   - `not_found`: find the file the user meant and run again.
3. **Report.** Tell the user what the inspection found and that labelling a video is not available in this version: `video-apply` refuses with `video_not_supported_yet`.
