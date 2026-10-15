# SeeCut Windows Studio

A lightweight browser-based video editor inspired by the SeeCut workflow. It is designed to run on Windows in Microsoft Edge or Google Chrome without installing a video-editing toolchain.

## Run

Open `index.html` in Edge or Chrome. Choose one or more video clips, optionally add a narration audio file and background music, preview the clip sequence, then export one combined WebM video.

## Features

- Combine selected video clips into one WebM output.
- Preview the selected clip sequence before export.
- Set an in and out point for every clip and scrub across the combined project timeline.
- Add a narration audio file and preview it with the clips.
- Choose where narration starts in its source file and where it starts on the project timeline. Short narration ends while video continues; audio beyond the video duration is not included.
- Mute the original video audio, adjust narration/music/original levels.
- Add a title and timed text cards.
- Optionally detect and skip long quiet sections.
- Process media locally in the browser; files are not uploaded by this page.

## Notes

- Use a current version of Edge or Chrome.
- Export runs in real time, so long videos take about as long as their playback duration.
- The output is WebM. This is a simplified browser editor, not a port of the original SeeCut AI agent pipeline.
- Silence detection is approximate. Review the preview and exported video before publishing.
- The original SeeCut repository uses the PolyForm Noncommercial 1.0.0 license. This standalone browser project is independently written and does not include the original repository's source files.
