# Whiteboard Studio for Google Colab

A self-contained Vietnamese whiteboard-video generator. The app and pipeline source in this repository are authored for this project; the notebook does not clone or run the Chalkboard repository.

## Features

- A Colab UI with progress for script generation, per-scene narration, scene drawing, and final assembly.
- Ollama generates a Vietnamese script and a separate visual prompt plus diagram for each scene.
- Piper creates a Vietnamese voice track for every scene.
- Python/Pillow draws matching whiteboard scenes; FFmpeg syncs the voice and joins the scenes into one MP4.
- Download buttons for the finished MP4 and the generated script JSON.

## Run

1. Upload the files in this folder to the root of your public GitHub repository: `chalkboard_colab.ipynb`, `whiteboard_studio.py`, `requirements.txt`, and `README.md`.
2. Open `chalkboard_colab.ipynb` in Google Colab.
3. Run the setup cells from top to bottom, then press **Tạo kịch bản và video** in the UI.
4. Enter a Vietnamese topic. Watch the scene cards and progress update, then click **Tải video MP4**.

The first run downloads the app dependencies, the Qwen2.5 3B model (about 1.9 GB), and the Vietnamese Piper voice into Colab. A fresh Colab runtime needs setup again.

## Dependencies and ownership

The app/pipeline code is in this repository. It uses Ollama, Piper TTS, FFmpeg, Pillow, Requests, and ipywidgets as external open-source tools/libraries, plus their model/voice files. Those are necessary for local language generation, speech, image rendering, and MP4 encoding. The visuals are whiteboard diagrams generated from each scene's prompt; this is not photorealistic text-to-video.

## Colab notebook URL

After uploading to the repository root, open:

`https://colab.research.google.com/github/saigonvet8312-coder/colab-whiteboard/blob/main/chalkboard_colab.ipynb`

