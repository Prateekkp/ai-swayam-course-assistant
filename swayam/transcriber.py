from pathlib import Path


def save_transcript(text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / "transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"    Saved: {transcript_path.name}")
    return transcript_path
