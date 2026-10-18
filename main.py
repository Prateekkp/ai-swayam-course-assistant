import argparse
from pathlib import Path
import yaml

from swayam.browser import SWAYAMBrowser
from swayam.scraper import discover_all_lessons, discover_local_lessons, Lesson
from swayam.transcriber import save_transcript
from swayam.notes import make_study_notes, save_output


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def process_lesson(lesson: Lesson, lesson_num: int, output_base: Path, config: dict):
    # Use existing lesson_dir if available, otherwise find matching or compute it
    if lesson.lesson_dir and lesson.lesson_dir.exists():
        lesson_dir = lesson.lesson_dir
    else:
        week_dir = output_base / lesson.week_name.replace(" ", "")
        safe_name = lesson.lesson_name.replace(" ", "_").replace("/", "_")
        existing = None
        if week_dir.exists():
            for d in week_dir.iterdir():
                if d.is_dir() and safe_name.lower() in d.name.lower():
                    existing = d
                    break
        if existing:
            lesson_dir = existing
        else:
            num_prefix = f"{lesson_num:02d}"
            lesson_dir = week_dir / f"{num_prefix}_{safe_name}"

    print(f"\n  Processing: {lesson.lesson_name}")

    if not lesson.transcript:
        print("    Skipped (no transcript)")
        return False

    study_path = lesson_dir / "study_notes.md"
    mcqs_path = lesson_dir / "practice_mcqs.md"

    # Only skip if BOTH study notes and MCQs exist and are healthy (> 500 bytes)
    if study_path.exists() and mcqs_path.exists():
        if study_path.stat().st_size > 500 and mcqs_path.stat().st_size > 500:
            print("    Skipped (already processed and verified healthy)")
            return True
        else:
            print("    Re-processing (existing notes/MCQs were empty or incomplete)")

    lesson_dir.mkdir(parents=True, exist_ok=True)

    # Strictly enforce media/ subfolder for transcripts
    media_dir = lesson_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = media_dir / "transcript.txt"
    stray_path = lesson_dir / "transcript.txt"

    # Auto-migrate if transcript was accidentally placed in lesson root
    if stray_path.exists() and not transcript_path.exists():
        stray_path.replace(transcript_path)

    transcript = None
    if transcript_path.exists() and config["output"]["save_transcript"]:
        print("    Reusing local transcript from media/transcript.txt")
        transcript = transcript_path.read_text(encoding="utf-8")
    else:
        transcript = lesson.transcript
        if config["output"]["save_transcript"]:
            save_transcript(transcript, media_dir)

    notes, mcqs = make_study_notes(transcript, config)
    if not notes or len(notes.strip()) < 300 or not mcqs or len(mcqs.strip()) < 300:
        raise ValueError("Generated notes or MCQs are incomplete or invalid.")

    save_output(notes, mcqs, lesson_dir)

    return True


def main():
    parser = argparse.ArgumentParser(description="SWAYAM Course Assistant")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Process lessons using existing local transcripts on disk without opening the browser"
    )
    args = parser.parse_args()

    config = load_config()

    output_base = Path(config["output"]["base_dir"])
    output_base.mkdir(parents=True, exist_ok=True)

    course_name = config["swayam"]["course_name"]

    print("=" * 60)
    print("SWAYAM Course Assistant")
    print(f"Course: {course_name}")
    print("=" * 60)

    if args.local:
        print("\n[Local Mode] Scanning existing transcripts in output folder...")
        lessons = discover_local_lessons(output_base)
        print(f"Found {len(lessons)} lessons with local transcripts on disk.\n")
    else:
        wait_timeout = config["selenium"]["wait_timeout"]
        login_timeout = config["selenium"]["login_timeout"]

        with SWAYAMBrowser(wait_timeout=wait_timeout, login_timeout=login_timeout) as browser:
            transcript_language = config["transcription"].get("language", "English")
            test_cfg = config.get("test", {})
            skip_weeks = test_cfg.get("skip_weeks", 0)
            max_weeks = test_cfg.get("max_weeks")
            max_lessons = test_cfg.get("max_lessons_per_week")
            lessons = discover_all_lessons(
                browser, course_name, transcript_language,
                skip_weeks, max_weeks, max_lessons, output_base
            )

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
