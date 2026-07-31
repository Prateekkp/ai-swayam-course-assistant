from dataclasses import dataclass
from pathlib import Path
import time
from swayam.browser import SWAYAMBrowser

SKIP_KEYWORDS = ["quiz", "practice", "assignment", "subjective", "programming"]


@dataclass
class Lesson:
    week_name: str
    lesson_name: str
    transcript: str | None = None


def _should_skip(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in SKIP_KEYWORDS)


def _is_already_processed(lesson_name: str, week_name: str, output_base: Path) -> bool:
    """Check if study_notes.md already exists for this lesson."""
    week_dir = output_base / week_name.replace(" ", "")
    if not week_dir.exists():
        return False
    # Match by lesson name in directory names (dirs start with NN_ prefix)
    safe_name = lesson_name.replace(" ", "_").replace("/", "_")
    for d in week_dir.iterdir():
        if d.is_dir() and safe_name.lower() in d.name.lower():
            if (d / "study_notes.md").exists():
                return True
    return False


def discover_all_lessons(browser: SWAYAMBrowser, course_name: str, transcript_language: str = "English", skip_weeks: int = 0, max_weeks: int | None = None, max_lessons_per_week: int | None = None, output_base: Path | None = None) -> list[Lesson]:
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

                # Skip already-processed lessons (no browser click needed)
                if output_base and _is_already_processed(lesson_name, week_name, output_base):
                    print(f"    [DONE] {lesson_name}")
                    skipped_count += 1
                    continue

                youtube_url = None
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

    return all_lessons
