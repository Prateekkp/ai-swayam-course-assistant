from pathlib import Path


def save_transcript(text: str, target_dir: Path) -> Path:
    """Save transcript text, strictly enforcing the media/ subfolder."""
    if target_dir.name != "media":
        media_dir = target_dir / "media"
    else:
        media_dir = target_dir

    media_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = media_dir / "transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"    Saved transcript: {transcript_path.name}")
    return transcript_path
