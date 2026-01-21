# SRT Transcriber

Video/audio transcription tool using faster-whisper with both CLI and web interfaces.

## Project Structure

```
transcribe.py      # CLI tool - standalone, no web dependencies
app.py             # Flask web server with SSE streaming
templates/
  index.html       # Single-page web UI
requirements.txt   # faster-whisper, flask
venv/              # Python 3.9 virtualenv with tkinter support
```

## Architecture

- `transcribe.py` is the original CLI tool and works independently
- `app.py` imports `format_srt_time` from `transcribe.py` to avoid duplication
- Web app uses SSE (Server-Sent Events) for real-time streaming of transcription progress and ffmpeg output
- Native file picker uses tkinter (requires `brew install python-tk@3.9` on macOS)

## Key Implementation Details

- Transcription uses faster-whisper with word-level timestamps for `max_words` chunking
- SRT files are saved alongside the source video with `.srt` extension
- Burned videos use format: `{stem}_captions_{ISO-timestamp}.mp4`
- FFmpeg subtitle filter uses ASS styling (`force_style` parameter)
- Color conversion: hex (#FFFFFF) → ASS format (&HBBGGRR)

## Running

```bash
# CLI
python transcribe.py video.mp4 -m medium -w 5

# Web (use venv for tkinter support)
./venv/bin/python app.py
# Open http://127.0.0.1:5000
```

## Gotchas

- Flask must run with `debug=False` on macOS or tkinter dialogs crash the server
- `threaded=False` also required for tkinter compatibility
