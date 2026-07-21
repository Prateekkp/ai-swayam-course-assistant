from dataclasses import dataclass
from swayam.browser import SWAYAMBrowser

SKIP_KEYWORDS = ["quiz", "practice", "assignment", "subjective", "programming"]


@dataclass
class Lesson:
    week_name: str
    lesson_name: str
    youtube_url: str | None


def _should_skip(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in SKIP_KEYWORDS)


def discover_all_lessons(browser: SWAYAMBrowser, course_name: str) -> list[Lesson]:
    browser.navigate("https://swayam.gov.in/")
    if not browser.ensure_logged_in():
        print("Exiting: login failed")
        return []
    if not browser.open_my_courses():
        return []
    if not browser.go_to_course(course_name):
        return []

    weeks = browser.get_week_names()
    all_lessons: list[Lesson] = []

    for week_name in weeks:
        try:
            browser.expand_week(week_name)
            lesson_names = browser.get_lesson_names(week_name)

            for lesson_name in lesson_names:
                if _should_skip(lesson_name):
                    print(f"    [SKIP] {lesson_name}")
                    continue

                try:
                    browser.click_lesson(lesson_name)
                    youtube_url = browser.get_youtube_link()
                    all_lessons.append(Lesson(
                        week_name=week_name,
                        lesson_name=lesson_name,
                        youtube_url=youtube_url,
                    ))
                    status = "found" if youtube_url else "no YouTube link"
                    print(f"    [{status}] {lesson_name}")
                except Exception as e:
                    print(f"    [ERROR] {lesson_name}: {e}")
                    all_lessons.append(Lesson(
                        week_name=week_name,
                        lesson_name=lesson_name,
                        youtube_url=None,
                    ))
        except Exception as e:
            print(f"  [ERROR] {week_name}: {e}")

    return all_lessons
