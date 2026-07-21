import yaml
from pathlib import Path

from swayam.browser import SWAYAMBrowser
from swayam.scraper import discover_all_lessons, Lesson
from swayam.downloader import download_audio
from swayam.transcriber import transcribe_large_audio, save_transcript
from swayam.notes import make_study_notes, save_output


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def process_lesson(lesson: Lesson, lesson_num: int, output_base: Path, config: dict):
    week_dir = output_base / lesson.week_name.replace(" ", "")
    num_prefix = f"{lesson_num:02d}"
    lesson_dir = week_dir / f"{num_prefix}_{lesson.lesson_name.replace(' ', '_').replace('/', '_')}"

    print(f"\n  Processing: {lesson.lesson_name}")

    if not lesson.youtube_url:
        print("    Skipped (no YouTube link)")
        return False

    study_path = lesson_dir / "study_notes.md"

    if study_path.exists():
        print("    Skipped (already processed)")
        return True

    lesson_dir.mkdir(parents=True, exist_ok=True)

    media_dir = lesson_dir / "media"
    audio_path = media_dir / "audio.mp3"
    transcript_path = media_dir / "transcript.txt"
    transcript = None

    # Step 1: Get audio (reuse if exists)
    if audio_path.exists():
        print("    Audio exists, reusing")
    else:
        if config["output"]["save_audio"]:
            audio_path = download_audio(lesson.youtube_url, media_dir)
        else:
            temp_dir = Path("_temp")
            temp_dir.mkdir(exist_ok=True)
            audio_path = download_audio(lesson.youtube_url, temp_dir, filename="audio")

    # Step 2: Get transcript (reuse if exists)
    if transcript_path.exists() and config["output"]["save_transcript"]:
        print("    Transcript exists, reusing")
        transcript = transcript_path.read_text(encoding="utf-8")
    else:
        chunk_ms = config["transcription"]["chunk_length_ms"]
        transcript = transcribe_large_audio(audio_path, chunk_length_ms=chunk_ms)
        if config["output"]["save_transcript"]:
            save_transcript(transcript, media_dir)

    # Step 3: Generate study notes and MCQs
    notes, mcqs = make_study_notes(transcript, config)
    save_output(notes, mcqs, lesson_dir)

    # Cleanup temp audio if not saving
    if not config["output"]["save_audio"] and not config["output"].get("keep_temp"):
        if audio_path.exists() and "_temp" in str(audio_path):
            audio_path.unlink(missing_ok=True)

    return True


def main():
    config = load_config()

    output_base = Path(config["output"]["base_dir"])
    output_base.mkdir(parents=True, exist_ok=True)

    course_name = config["swayam"]["course_name"]
    wait_timeout = config["selenium"]["wait_timeout"]
    login_timeout = config["selenium"]["login_timeout"]

    print("=" * 60)
    print("SWAYAM Course Assistant")
    print(f"Course: {course_name}")
    print("=" * 60)

    with SWAYAMBrowser(wait_timeout=wait_timeout, login_timeout=login_timeout) as browser:
        lessons = discover_all_lessons(browser, course_name)

    if not lessons:
        print("\nNo lessons found. Exiting.")
        return

    print(f"\n{'=' * 60}")
    print(f"Processing {len(lessons)} lessons...")
    print("=" * 60)

    succeeded = 0
    failed = 0

    for i, lesson in enumerate(lessons, start=1):
        try:
            success = process_lesson(lesson, i, output_base, config)
            if success:
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            print(f"    [ERROR] {lesson.lesson_name}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Done! {succeeded} succeeded, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
