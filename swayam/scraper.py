from dataclasses import dataclass
from pathlib import Path
import re
import time
from swayam.browser import SWAYAMBrowser

SKIP_KEYWORDS = ["quiz", "practice", "assignment", "subjective", "programming", "solution"]


@dataclass
class Lesson:
    week_name: str
    lesson_name: str
    transcript: str | None = None
    lesson_dir: Path | None = None


def _should_skip(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in SKIP_KEYWORDS)


def _find_lesson_dir(lesson_name: str, week_name: str, output_base: Path) -> Path | None:
    """Find the existing directory for a lesson if it exists."""
    week_dir = output_base / week_name.replace(" ", "")
    if not week_dir.exists():
        return None
    safe_name = lesson_name.replace(" ", "_").replace("/", "_")
    for d in week_dir.iterdir():
        if d.is_dir() and safe_name.lower() in d.name.lower():
            return d
    return None


def _is_already_processed(lesson_name: str, week_name: str, output_base: Path) -> bool:
    """Check if both study_notes.md and practice_mcqs.md are healthy."""
    lesson_dir = _find_lesson_dir(lesson_name, week_name, output_base)
    if not lesson_dir:
        return False

    study_file = lesson_dir / "study_notes.md"
    mcq_file = lesson_dir / "practice_mcqs.md"

    if study_file.exists() and mcq_file.exists():
        if study_file.stat().st_size > 500 and mcq_file.stat().st_size > 500:
            return True

    return False


def _get_local_transcript(lesson_name: str, week_name: str, output_base: Path) -> tuple[str | None, Path | None]:
    """Check if a saved transcript already exists on disk."""
    lesson_dir = _find_lesson_dir(lesson_name, week_name, output_base)
    if not lesson_dir:
        return None, None

    transcript_path = lesson_dir / "media" / "transcript.txt"
    if transcript_path.exists() and transcript_path.stat().st_size > 50:
        try:
            return transcript_path.read_text(encoding="utf-8"), lesson_dir
        except Exception:
            pass

    return None, lesson_dir


def discover_local_lessons(output_base: Path) -> list[Lesson]:
    """Discover all lessons that already have transcripts saved locally on disk."""
    if not output_base.exists():
        return []

    def week_sort_key(p: Path):
        nums = re.findall(r"\d+", p.name)
        return int(nums[0]) if nums else 999

    week_dirs = sorted(
        [d for d in output_base.iterdir() if d.is_dir() and d.name.lower().startswith("week")],
        key=week_sort_key
    )

    local_lessons: list[Lesson] = []

    for week_dir in week_dirs:
        week_name = week_dir.name
        lesson_dirs = sorted([d for d in week_dir.iterdir() if d.is_dir()])

        for l_dir in lesson_dirs:
            transcript_file = l_dir / "media" / "transcript.txt"
            if transcript_file.exists() and transcript_file.stat().st_size > 50:
                clean_name = re.sub(r"^\d+_", "", l_dir.name).replace("_", " ")
                transcript_text = transcript_file.read_text(encoding="utf-8")
                local_lessons.append(Lesson(
                    week_name=week_name,
                    lesson_name=clean_name,
                    transcript=transcript_text,
                    lesson_dir=l_dir,
                ))

    return local_lessons


def discover_all_lessons(
    browser: SWAYAMBrowser,
    course_name: str,
    transcript_language: str = "English",
    skip_weeks: int = 0,
    max_weeks: int | None = None,
    max_lessons_per_week: int | None = None,
    output_base: Path | None = None
) -> list[Lesson]:
    browser.navigate("https://swayam.gov.in/")
    if not browser.ensure_logged_in():
        print("Exiting: login failed")
        return []
    if not browser.open_my_courses():
        return []
    if not browser.go_to_course(course_name):
        return []

    weeks = browser.get_week_names()
    if skip_weeks:
        weeks = weeks[skip_weeks:]
    if max_weeks:
        weeks = weeks[:max_weeks]
    all_lessons: list[Lesson] = []
    skipped_count = 0
    local_reused_count = 0

    for week_name in weeks:
        try:
            browser.expand_week(week_name)
            lesson_names = browser.get_lesson_names(week_name)
            if max_lessons_per_week:
                lesson_names = lesson_names[:max_lessons_per_week]

            for lesson_name in lesson_names:
                if _should_skip(lesson_name):
                    print(f"    [SKIP] {lesson_name}")
                    continue

                # 1. Skip if already processed and healthy
                if output_base and _is_already_processed(lesson_name, week_name, output_base):
                    print(f"    [DONE] {lesson_name}")
                    skipped_count += 1
                    continue

                # 2. Check if local transcript already exists on disk (avoid slow browser scraping)
                if output_base:
                    local_text, existing_dir = _get_local_transcript(lesson_name, week_name, output_base)
                    if local_text:
                        print(f"    [reusing local transcript] {lesson_name}")
                        local_reused_count += 1
                        all_lessons.append(Lesson(
                            week_name=week_name,
                            lesson_name=lesson_name,
                            transcript=local_text,
                            lesson_dir=existing_dir,
                        ))
                        continue

                # 3. Only click and scrape if no local transcript exists
                transcript = None
                for attempt in range(3):
                    try:
                        browser.click_lesson(lesson_name)
                        transcript = browser.scrape_transcript(transcript_language)
                        break
                    except Exception as e:
                        print(f"    [RETRY {attempt+1}/3] {lesson_name}: {e}")
                        browser._ensure_default_content()
                        if attempt < 2:
                            time.sleep(5)
                            try:
                                browser.navigate("https://swayam.gov.in/")
                                time.sleep(3)
                            except Exception:
                                pass

                all_lessons.append(Lesson(
                    week_name=week_name,
                    lesson_name=lesson_name,
                    transcript=transcript,
                ))
                transcript_status = "with transcript" if transcript else "no transcript"
                print(f"    [{transcript_status}] {lesson_name}")
        except Exception as e:
            print(f"  [ERROR] {week_name}: {e}")

    if skipped_count:
        print(f"\n  Skipped {skipped_count} already-processed lessons")
    if local_reused_count:
        print(f"  Reused {local_reused_count} local transcripts without web scraping")

    return all_lessons
