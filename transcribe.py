#!/usr/bin/env python3
"""
Transcribe video/audio files to SRT subtitles using faster-whisper.
"""

import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def format_srt_time(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def transcribe_to_srt(input_path, output_path, model_size="small", max_words=None):
    """Transcribe a video/audio file to SRT format."""
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    # Use word timestamps if we want shorter segments
    use_word_timestamps = max_words is not None
    segments, info = model.transcribe(input_path, word_timestamps=use_word_timestamps)

    print(f"Detected language: {info.language} (probability {info.language_probability:.2f})")

    with open(output_path, "w", encoding="utf-8") as f:
        caption_num = 1

        for segment in segments:
            if max_words and segment.words:
                # Split into chunks of max_words
                words = segment.words
                for i in range(0, len(words), max_words):
                    chunk = words[i:i + max_words]
                    start = chunk[0].start
                    end = chunk[-1].end
                    text = "".join(w.word for w in chunk).strip()

                    f.write(f"{caption_num}\n")
                    f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
                    f.write(f"{text}\n\n")
                    print(f"[{format_srt_time(end)}] {text}")
                    caption_num += 1
            else:
                f.write(f"{caption_num}\n")
                f.write(f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n")
                f.write(f"{segment.text.strip()}\n\n")
                print(f"[{format_srt_time(segment.end)}] {segment.text.strip()}")
                caption_num += 1

    print(f"\nSaved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe video/audio to SRT subtitles")
    parser.add_argument("input", help="Input video/audio file (mp4, webm, mp3, etc.)")
    parser.add_argument("-o", "--output", help="Output SRT file (default: input name with .srt extension)")
    parser.add_argument("-m", "--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                        help="Whisper model size (default: small)")
    parser.add_argument("-w", "--max-words", type=int,
                        help="Max words per caption (shorter = snappier captions)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = args.output if args.output else input_path.with_suffix(".srt")

    transcribe_to_srt(str(input_path), str(output_path), model_size=args.model, max_words=args.max_words)


if __name__ == "__main__":
    main()
