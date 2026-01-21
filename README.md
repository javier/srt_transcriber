# srt_transcriber

Extract SRT subtitles from video/audio files using faster-whisper.

## Setup

```bash
pip install -r requirements.txt
```

Note: ffmpeg must be installed on your system.

## Usage

```bash
# Basic usage - creates video.srt from video.mp4
python transcribe.py video.mp4

# Specify output file
python transcribe.py video.mp4 -o subtitles.srt

# Use a larger model for better accuracy
python transcribe.py video.mp4 -m medium

# Shorter captions (5 words max per caption, good for shorts)
python transcribe.py video.mp4 -w 5
```

## Options

- `-o, --output` - Output SRT file path
- `-m, --model` - Model size: tiny, base, small (default), medium, large-v2, large-v3
- `-w, --max-words` - Max words per caption (use 4-6 for snappy short-form captions)

Larger models are more accurate but slower. The "small" model is a good balance for most uses.

## Burning subtitles into video

Use ffmpeg to hardcode subtitles directly into the video:

```bash
ffmpeg -i video.mp4 -vf "subtitles=video.srt:force_style='FontSize=16,FontName=Arial Bold,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=3,BorderStyle=1,Alignment=10,MarginV=50'" -c:a copy video_subtitled.mp4
```

Style options:
- `FontSize` - text size (try 16-24 depending on resolution)
- `Outline` - black outline thickness (2-4)
- `Alignment=10` - centered horizontally, middle of screen vertically
- `MarginV` - vertical offset (higher = lower on screen)
