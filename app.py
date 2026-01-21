#!/usr/bin/env python3
"""
Web app for video transcription with SRT editing and caption burning.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, render_template, request

# Try to import tkinter for native file dialogs (optional)
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

from faster_whisper import WhisperModel
from transcribe import format_srt_time

app = Flask(__name__)


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/select-video')
def select_video():
    """Open native file dialog and return selected path."""
    if not HAS_TKINTER:
        return {"error": "File dialog not available (tkinter not installed). Please enter the path manually."}, 501

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askopenfilename(
        title="Select Video",
        filetypes=[("Video files", "*.mp4 *.webm *.mkv *.avi *.mov"), ("All files", "*.*")]
    )
    root.destroy()
    return {"path": path}


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Start transcription and return SSE stream."""
    data = request.get_json()
    video_path = data.get('video_path')
    model_size = data.get('model', 'medium')
    max_words = data.get('max_words')

    if max_words is not None:
        max_words = int(max_words)

    video_path = Path(video_path)
    if not video_path.exists():
        return {"error": f"File not found: {video_path}"}, 404

    srt_path = video_path.with_suffix('.srt')

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Loading model: {model_size}'})}\n\n"

        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        yield f"data: {json.dumps({'type': 'status', 'message': 'Starting transcription...'})}\n\n"

        use_word_timestamps = max_words is not None
        segments, info = model.transcribe(str(video_path), word_timestamps=use_word_timestamps)

        yield f"data: {json.dumps({'type': 'status', 'message': f'Detected language: {info.language} (probability {info.language_probability:.2f})'})}\n\n"

        with open(srt_path, 'w', encoding='utf-8') as f:
            caption_num = 1

            for segment in segments:
                if max_words and segment.words:
                    words = segment.words
                    for i in range(0, len(words), max_words):
                        chunk = words[i:i + max_words]
                        start = chunk[0].start
                        end = chunk[-1].end
                        text = "".join(w.word for w in chunk).strip()

                        f.write(f"{caption_num}\n")
                        f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
                        f.write(f"{text}\n\n")

                        yield f"data: {json.dumps({'type': 'segment', 'time': format_srt_time(end), 'text': text})}\n\n"
                        caption_num += 1
                else:
                    f.write(f"{caption_num}\n")
                    f.write(f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n")
                    f.write(f"{segment.text.strip()}\n\n")

                    yield f"data: {json.dumps({'type': 'segment', 'time': format_srt_time(segment.end), 'text': segment.text.strip()})}\n\n"
                    caption_num += 1

        yield f"data: {json.dumps({'type': 'complete', 'srt_path': str(srt_path)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/srt', methods=['GET'])
def get_srt():
    """Load SRT file content."""
    path = request.args.get('path')
    if not path:
        return {"error": "No path provided"}, 400

    path = Path(path)
    if not path.exists():
        return {"error": f"File not found: {path}"}, 404

    content = path.read_text(encoding='utf-8')
    return {"content": content, "path": str(path)}


@app.route('/srt', methods=['POST'])
def save_srt():
    """Save SRT file content."""
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')

    if not path or content is None:
        return {"error": "Path and content required"}, 400

    path = Path(path)
    path.write_text(content, encoding='utf-8')
    return {"success": True, "path": str(path)}


@app.route('/burn', methods=['POST'])
def burn():
    """Burn captions into video and return SSE stream."""
    data = request.get_json()
    video_path = data.get('video_path')
    srt_path = data.get('srt_path')

    # Style options with defaults
    font_size = data.get('font_size', 16)
    font_name = data.get('font_name', 'Arial Bold')
    text_color = data.get('text_color', 'FFFFFF')
    outline_color = data.get('outline_color', '000000')
    outline = data.get('outline', 3)
    alignment = data.get('alignment', 10)
    margin_v = data.get('margin_v', 50)

    video_path = Path(video_path)
    srt_path = Path(srt_path)

    if not video_path.exists():
        return {"error": f"Video not found: {video_path}"}, 404
    if not srt_path.exists():
        return {"error": f"SRT not found: {srt_path}"}, 404

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    output_path = video_path.parent / f"{video_path.stem}_captions_{timestamp}{video_path.suffix}"

    # Build ffmpeg force_style string
    # Convert hex colors to ASS format (&HBBGGRR)
    def hex_to_ass(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H{b}{g}{r}"

    force_style = (
        f"FontSize={font_size},"
        f"FontName={font_name},"
        f"PrimaryColour={hex_to_ass(text_color)},"
        f"OutlineColour={hex_to_ass(outline_color)},"
        f"Outline={outline},"
        f"BorderStyle=1,"
        f"Alignment={alignment},"
        f"MarginV={margin_v}"
    )

    # Escape the SRT path for ffmpeg filter (need to escape : and \)
    srt_path_escaped = str(srt_path).replace('\\', '/').replace(':', '\\:')

    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-vf', f"subtitles={srt_path_escaped}:force_style='{force_style}'",
        '-c:a', 'copy',
        str(output_path)
    ]

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Starting ffmpeg...'})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': f'Output: {output_path}'})}\n\n"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # FFmpeg outputs progress to stderr
        for line in process.stderr:
            line = line.strip()
            if line:
                yield f"data: {json.dumps({'type': 'progress', 'message': line})}\n\n"

        process.wait()

        if process.returncode == 0:
            yield f"data: {json.dumps({'type': 'complete', 'output_path': str(output_path)})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'message': f'FFmpeg exited with code {process.returncode}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=False)
