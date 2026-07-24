from pathlib import Path
from yt_dlp import YoutubeDL


def download_audio(url: str, output_dir: Path, filename: str = "audio") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    profile_dir = str(Path(__file__).parent.parent.resolve() / "chrome_profile")

    base_opts = {
        "format": "bestaudio/best[ext=webm]/bestaudio/best",
        "outtmpl": str(output_path),
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        ydl_opts = {**base_opts, "cookiesfrombrowser": ("chrome", profile_dir)}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        ydl_opts = {**base_opts, "nocheckcertificate": True}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    final_path = output_path.with_suffix(".mp3")
    print(f"    Downloaded: {final_path.name}")
    return final_path
