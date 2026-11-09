# 03: Detect an Existing Label in videos

**What to build:** Apply the Existing Label rule from 01 to videos (`references/video.md`), using the frames already sampled to choose the corner. See [spec](../spec.md).

**Blocked by:** 01

**Status:** resolved

- [x] While looking at the sampled frames, note any on-screen disclosure of AI involvement. If one is found, report it with the frame times it appears at, and ask before running `video-apply`.
- [x] Never claim the video has no Existing Label: sampling can't establish that, as the `sampling_note` already says.
- [x] Doc test for `video.md`. An eval scenario only if a fixture with an on-screen disclosure is cheap to build; otherwise record in a comment why it was left out.
