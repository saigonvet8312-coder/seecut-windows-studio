from __future__ import annotations

import html
import json
import math
import os
import subprocess
import time
from pathlib import Path

import requests

W, H, FPS = 1280, 720, 24
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
VOICE = os.environ.get("PIPER_MODEL", "/content/piper-voices/vi_VN-vais1000-medium.onnx")
OUT = Path("/content/whiteboard-results")


def generate_script(topic: str, scene_count: int) -> dict:
    prompt = f"""
Hãy viết kịch bản video giải thích bằng tiếng Việt về chủ đề: {topic}
Chia chính xác thành {scene_count} cảnh. Mỗi cảnh gồm lời thuyết minh 2-4 câu và một sơ đồ bảng trắng khớp nội dung.
Chỉ trả JSON theo dạng:
{{
  "title": "Tiêu đề",
  "scenes": [
    {{
      "title": "Tên cảnh",
      "narration": "Lời thoại tiếng Việt",
      "visual_prompt": "Mô tả hình vẽ của cảnh",
      "nodes": [{{"label":"Ý A","x":0.2}},{{"label":"Ý B","x":0.5}},{{"label":"Ý C","x":0.8}}],
      "links": [[0,1],[1,2]]
    }}
  ]
}}
Yêu cầu: 2-4 nodes mỗi cảnh, label ngắn tối đa 4 từ, x là số 0..1, liên kết đúng quan hệ. Không markdown.
"""
    response = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": MODEL, "prompt": prompt, "format": "json", "stream": False,
              "options": {"temperature": 0.45, "num_ctx": 8192}},
        timeout=900,
    )
    response.raise_for_status()
    story = json.loads(response.json()["response"])
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 2:
        raise ValueError("Model không trả đủ cảnh. Hãy thử lại với chủ đề rõ hơn.")
    story["scenes"] = scenes[:scene_count]
    for i, scene in enumerate(story["scenes"]):
        scene["title"] = str(scene.get("title") or f"Cảnh {i + 1}")
        scene["narration"] = str(scene.get("narration") or "").strip()
        scene["visual_prompt"] = str(scene.get("visual_prompt") or scene["title"])
        nodes = scene.get("nodes") or []
        clean = []
        for j, node in enumerate(nodes[:4]):
            try:
                x = min(0.88, max(0.12, float(node.get("x", 0.2 + j * 0.3))))
            except (TypeError, ValueError):
                x = 0.2 + j * 0.3
            clean.append({"label": str(node.get("label") or "Ý chính")[:38], "x": x})
        if len(clean) < 2:
            words = [w.strip(".,!?;:") for w in scene["title"].split() if len(w) > 2]
            words = (words + ["Ý chính", "Kết quả"])[:3]
            clean = [{"label": word, "x": 0.2 + j * 0.3} for j, word in enumerate(words)]
        scene["nodes"] = clean
        links = scene.get("links") or []
        scene["links"] = [
            [int(link[0]), int(link[1])] for link in links
            if isinstance(link, list) and len(link) >= 2
            and all(str(v).isdigit() and 0 <= int(v) < len(clean) for v in link[:2])
        ] or [[j, j + 1] for j in range(len(clean) - 1)]
        if not scene["narration"]:
            raise ValueError(f"Cảnh {i + 1} không có lời thuyết minh.")
    story["title"] = str(story.get("title") or topic)
    return story


def run_cmd(command, *, text_input=None):
    result = subprocess.run(command, input=text_input, text=text_input is not None, capture_output=True)
    if result.returncode:
        err = result.stderr.decode("utf-8", "replace") if isinstance(result.stderr, bytes) else result.stderr
        raise RuntimeError(f"Lệnh lỗi: {' '.join(map(str, command))}\n{err[-3500:]}")
    return result


def synthesize(text: str, wav_path: Path):
    if not Path(VOICE).exists():
        raise FileNotFoundError(f"Không thấy giọng Piper: {VOICE}. Chạy cell tải giọng Việt trước.")
    result = subprocess.run(
        ["piper", "--model", VOICE, "--output_file", str(wav_path)],
        input=text + "\n", text=True, capture_output=True,
    )
    if result.returncode:
        raise RuntimeError("Piper lỗi: " + result.stderr[-3000:])


def audio_length(path: Path) -> float:
    result = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(result.stdout.decode().strip())


def font(size, bold=False):
    from PIL import ImageFont
    path = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(path, size) if Path(path).exists() else ImageFont.load_default()


def wrap_lines(draw, text, face, width):
    words, lines, line = text.split(), [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if line and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_frame(scene, scene_number, scene_count, frame, frame_count):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (W, H), "#fffdf6")
    d = ImageDraw.Draw(image)
    title_face, node_face, body_face = font(34, True), font(23, True), font(17)
    for x in range(24, W, 34):
        for y in range(22, H, 34):
            d.ellipse((x, y, x + 2, y + 2), fill="#e7e4da")

    d.rounded_rectangle((42, 28, 1238, 92), 20, fill="#202a23")
    d.rounded_rectangle((60, 42, 98, 80), 12, fill="#c9f36b")
    d.text((70, 45), "✦", font=font(23, True), fill="#202a23")
    d.text((116, 45), "WHITEBOARD STUDIO", font=font(21, True), fill="white")
    d.text((1078, 51), f"CẢNH {scene_number}/{scene_count}", font=font(17, True), fill="#d8f4aa")

    d.text((70, 119), scene["title"], font=title_face, fill="#202a23")
    desc = "MINH HỌA: " + " ".join(wrap_lines(d, scene["visual_prompt"], body_face, 1080)[:1])
    d.rounded_rectangle((70, 171, 1210, 218), 13, fill="#e9f1db")
    d.text((88, 185), desc[:135], font=body_face, fill="#45583b")

    nodes = scene["nodes"]
    centers = [(int(130 + n["x"] * 1020), 390) for n in nodes]
    reveal = int(math.ceil((frame + 1) / max(1, frame_count) * (len(nodes) + len(scene["links"]))))
    item = 0
    for a, b in scene["links"]:
        if item < reveal and a < len(centers) and b < len(centers):
            p1, p2 = centers[a], centers[b]
            d.line((p1, p2), fill="#5e704f", width=5)
            angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            tip = (p2[0] - 110, p2[1])
            d.polygon([tip, (tip[0] - 15, tip[1] - 10), (tip[0] - 15, tip[1] + 10)], fill="#5e704f")
        item += 1
    for j, node in enumerate(nodes):
        if item >= reveal:
            break
        x, y = centers[j]
        label = node["label"]
        box_w = min(320, max(185, d.textbbox((0, 0), label, font=node_face)[2] + 48))
        rect = (x - box_w // 2, y - 44, x + box_w // 2, y + 44)
        d.rounded_rectangle(rect, 20, fill="#fff", outline="#29342c", width=4)
        d.rounded_rectangle((rect[0] + 4, rect[1] + 3, rect[2] - 3, rect[3] - 2), 18, outline="#899583", width=1)
        bounds = d.textbbox((0, 0), label, font=node_face)
        d.text((x - (bounds[2] - bounds[0]) // 2, y - 16), label, font=node_face, fill="#242c26")
        item += 1

    d.rounded_rectangle((64, 570, 1216, 674), 20, fill="#202a23")
    narration_lines = wrap_lines(d, scene["narration"], body_face, 1085)
    for j, line in enumerate(narration_lines[:3]):
        d.text((88, 589 + j * 25), line, font=body_face, fill="#fff")
    progress = (frame + 1) / max(1, frame_count)
    d.rounded_rectangle((64, 691, 1216, 703), 6, fill="#e3e0d6")
    d.rounded_rectangle((64, 691, 64 + int(1152 * progress), 703), 6, fill="#c9f36b")
    d.ellipse((int(70 + progress * 1130) - 8, 548, int(70 + progress * 1130) + 8, 564), fill="#e66b4e")
    return image



def render_silent_scene(scene, index, total, duration, output: Path):
    frame_count = max(FPS, int(math.ceil(duration * FPS)))
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
        "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in range(frame_count):
            process.stdin.write(draw_frame(scene, index + 1, total, frame, frame_count).tobytes())
        process.stdin.close()
        error = process.stderr.read().decode("utf-8", errors="replace")
        code = process.wait()
        if code:
            raise RuntimeError(f"FFmpeg dựng cảnh {index + 1} lỗi:\n{error[-3000:]}")
    except Exception:
        if process.poll() is None:
            process.kill()
        raise


def run_pipeline(topic: str, scene_count: int, callback=None) -> dict:
    topic = topic.strip()
    if len(topic) < 8:
        raise ValueError("Chủ đề quá ngắn. Hãy nhập một câu mô tả rõ ràng.")

    run_dir = OUT / time.strftime("%Y%m%d-%H%M%S")
    audio_dir, raw_dir, scene_dir = run_dir / "audio", run_dir / "raw-scenes", run_dir / "scenes"
    for folder in (audio_dir, raw_dir, scene_dir):
        folder.mkdir(parents=True, exist_ok=True)

    def report(percent, message, story=None, states=None):
        if callback:
            callback(percent, message, story, states)

    report(3, "Đang viết kịch bản và tạo prompt minh họa từng cảnh…")
    story = generate_script(topic, scene_count)
    script_path = run_dir / "script.json"
    script_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    states = ["Chờ tạo"] * len(story["scenes"])
    report(20, "Đã chia kịch bản thành cảnh, mỗi cảnh có prompt minh họa riêng.", story, states)

    audio_paths = []
    total = len(story["scenes"])
    for i, scene in enumerate(story["scenes"]):
        states[i] = "Đang tạo giọng đọc"
        report(22 + int(20 * i / total), f"Đang tạo âm thanh cảnh {i + 1}/{total}…", story, states)
        audio_path = audio_dir / f"scene-{i + 1:02d}.wav"
        synthesize(scene["narration"], audio_path)
        audio_paths.append(audio_path)
        states[i] = "Đã có âm thanh"
        report(25 + int(20 * (i + 1) / total), f"Đã tạo âm thanh cảnh {i + 1}/{total}.", story, states)

    final_scenes = []
    for i, (scene, audio_path) in enumerate(zip(story["scenes"], audio_paths)):
        states[i] = "Đang dựng hình"
        report(48 + int(36 * i / total), f"Đang vẽ hoạt họa cảnh {i + 1}/{total} theo prompt…", story, states)
        raw_video = raw_dir / f"scene-{i + 1:02d}.mp4"
        render_silent_scene(scene, i, total, audio_length(audio_path), raw_video)
        final_video = scene_dir / f"scene-{i + 1:02d}.mp4"
        run_cmd([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw_video), "-i", str(audio_path), "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
            str(final_video),
        ])
        final_scenes.append(final_video)
        states[i] = "Cảnh hoàn tất"
        report(50 + int(36 * (i + 1) / total), f"Đã ghép hình và giọng đọc cảnh {i + 1}/{total}.", story, states)

    report(90, "Đang nối các cảnh thành video hoàn chỉnh…", story, states)
    concat_path = run_dir / "scenes.txt"
    concat_path.write_text(
        "".join("file '" + path.as_posix() + "'\n" for path in final_scenes),
        encoding="utf-8",
    )
    final_path = run_dir / "video-hoan-chinh.mp4"
    run_cmd([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-c", "copy", "-movflags", "+faststart", str(final_path),
    ])
    report(100, "Hoàn tất! Video MP4 và kịch bản đã sẵn sàng.", story, ["Hoàn tất"] * total)
    return {"video": final_path, "script": script_path, "folder": run_dir, "story": story}


def _cards(story, states=None):
    states = states or ["Chờ tạo"] * len(story["scenes"])
    cards = []
    for i, scene in enumerate(story["scenes"]):
        state = states[i] if i < len(states) else "Chờ tạo"
        cards.append(
            "<article class='scene'><div class='scene-meta'><b>CẢNH "
            + f"{i + 1:02d}</b><span>{html.escape(state)}</span></div>"
            + f"<h3>{html.escape(scene['title'])}</h3>"
            + f"<p>{html.escape(scene['narration'])}</p>"
            + "<div class='scene-prompt'><strong>PROMPT MINH HỌA</strong><br>"
            + html.escape(scene["visual_prompt"]) + "</div></article>"
        )
    return "<div class='scene-grid'>" + "".join(cards) + "</div>"


def launch():
    import ipywidgets as widgets
    from IPython.display import HTML, display

    header = widgets.HTML(value="""
    <style>
      .studio{font-family:Inter,Arial,sans-serif;color:#1d2920;background:linear-gradient(135deg,#f5f9ef,#edf4e7);border:1px solid #dae6d1;border-radius:24px;padding:22px;margin:8px 0 14px}
      .studio h1{font-size:28px;margin:0 0 5px;letter-spacing:-.7px}.studio p{margin:0;color:#64725e}
      .tag{display:inline-block;background:#dff0c9;color:#3b532b;border-radius:999px;padding:6px 11px;margin-top:12px;font-size:11px;font-weight:800;letter-spacing:.5px}
      .status{background:#202b23;color:#eef7e5;padding:12px 15px;border-radius:12px;font-weight:650}
      .scene-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:10px;margin:12px 0}
      .scene{background:white;border:1px solid #e0e7db;border-radius:16px;padding:14px;box-shadow:0 5px 18px #273d1b0a}
      .scene-meta{display:flex;justify-content:space-between;color:#6d7b62;font-size:11px;letter-spacing:.4px}
      .scene h3{font-size:16px;margin:10px 0 6px;color:#202a22}.scene p{font-size:13px;line-height:1.5;color:#4b5847;margin:0 0 10px}
      .scene-prompt{font-size:12px;line-height:1.45;background:#f1f7e9;color:#43563b;padding:10px;border-radius:10px}
      .scene-prompt strong{font-size:10px;color:#78866d;letter-spacing:.5px}
    </style>
    <div class="studio"><h1>Vẽ Ý Tưởng</h1>
      <p>Tạo video bảng trắng tiếng Việt. Xem kịch bản, prompt, âm thanh và tiến độ của từng cảnh.</p>
      <span class="tag">SOURCE RIÊNG · KHÔNG CLONE CHALKBOARD</span></div>
    """)

    topic = widgets.Textarea(
        value="Giải thích vòng tuần hoàn của nước cho học sinh tiểu học",
        description="Chủ đề",
        placeholder="Nhập chủ đề hoặc mô tả video…",
        layout=widgets.Layout(width="100%", height="82px"),
    )
    count = widgets.IntSlider(
        value=4, min=3, max=6, step=1, description="Số cảnh",
        style={"description_width": "70px"}, layout=widgets.Layout(width="100%"),
    )
    button = widgets.Button(
        description="Tạo kịch bản và video", icon="magic", button_style="success",
        layout=widgets.Layout(width="100%", height="44px"),
    )
    progress = widgets.FloatProgress(
        value=0, min=0, max=100, description="Tiến độ",
        style={"description_width": "70px"}, layout=widgets.Layout(width="100%"),
    )
    status = widgets.HTML(value="<div class='status'>Sẵn sàng.</div>")
    scenes = widgets.HTML(value="")
    downloads = widgets.HBox()
    output = widgets.Output()
    form = widgets.VBox([
        topic, count, button, progress, status,
        widgets.HTML("<b style='color:#66745f'>TIẾN ĐỘ TỪNG CẢNH</b>"),
        scenes, downloads,
    ], layout=widgets.Layout(gap="9px"))

    def on_click(_):
        button.disabled = True
        progress.value = 0
        scenes.value = ""
        downloads.children = ()
        output.clear_output()

        def on_progress(percent, message, story, states):
            progress.value = percent
            status.value = "<div class='status'>" + html.escape(message) + "</div>"
            if story:
                scenes.value = _cards(story, states)

        try:
            result = run_pipeline(topic.value, count.value, on_progress)
            with output:
                display(HTML("<p><b>Đã tạo:</b> " + html.escape(result["video"].name) + "</p>"))
                display(HTML(_cards(result["story"], ["Đã ghép vào MP4"] * len(result["story"]["scenes"]))))

            def download(path):
                from google.colab import files
                files.download(str(path))

            video_button = widgets.Button(description="Tải video MP4", icon="download", button_style="success")
            script_button = widgets.Button(description="Tải kịch bản JSON", icon="file-code")
            video_button.on_click(lambda _: download(result["video"]))
            script_button.on_click(lambda _: download(result["script"]))
            downloads.children = (video_button, script_button)
        except Exception as exc:
            status.value = "<div class='status'>Có lỗi: " + html.escape(str(exc)) + "</div>"
            with output:
                print(repr(exc))
        finally:
            button.disabled = False

    button.on_click(on_click)
    display(header, form, output)


