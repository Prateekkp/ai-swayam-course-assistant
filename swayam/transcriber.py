import math
import os
from pathlib import Path
from pydub import AudioSegment
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def split_audio(file_path: Path, chunk_length_ms: int = 600000) -> list[Path]:
    audio = AudioSegment.from_file(file_path)
    chunks = []
    total_chunks = math.ceil(len(audio) / chunk_length_ms)

    for i in range(total_chunks):
        start = i * chunk_length_ms
        end = min((i + 1) * chunk_length_ms, len(audio))
        chunk = audio[start:end]
        chunk_name = file_path.parent / f"{file_path.stem}_chunk_{i}.mp3"
        chunk.export(chunk_name, format="mp3")
        chunks.append(chunk_name)

    return chunks


def transcribe_chunk(chunk_file: Path) -> str:
    client = _get_client()
    with open(chunk_file, "rb") as f:
        return client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3",
            response_format="text",
        )


def transcribe_large_audio(file_path: Path, chunk_length_ms: int = 600000) -> str:
    chunks = split_audio(file_path, chunk_length_ms)
    full_transcript = ""

    for chunk in chunks:
        text = transcribe_chunk(chunk)
        full_transcript += text + "\n"
        chunk.unlink(missing_ok=True)

    return full_transcript


def save_transcript(text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / "transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"    Saved: {transcript_path.name}")
    return transcript_path
