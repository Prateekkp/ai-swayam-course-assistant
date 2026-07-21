import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class SWAYAMBrowser:

    def __init__(self, wait_timeout: int = 20, login_timeout: int = 120):
        self.wait_timeout = wait_timeout
        self.login_timeout = login_timeout
        self.driver = None
        self.wait = None

    def __enter__(self):
        options = Options()

        profile_dir = Path(__file__).parent.parent.resolve() / "chrome_profile"
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, self.wait_timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
        return False

    def navigate(self, url: str):
        self.driver.get(url)

    def is_logged_in(self) -> bool:
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "user-avatar"))
            )
            return True
        except TimeoutException:
            return False

    def login_google(self):
        print("Opening login page...")

        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Login/Sign up"))
        ).click()

        print(f"Waiting for you to log in manually ({self.login_timeout}s timeout)...")
        timeout = self.login_timeout
        interval = 3
        elapsed = 0

        while elapsed < timeout:
            time.sleep(interval)
            elapsed += interval

            try:
                self.driver.find_element(By.CLASS_NAME, "user-avatar")
                print("Login successful")
                self.driver.get("https://swayam.gov.in/")
                time.sleep(2)
                return True
            except Exception:
                pass

            remaining = timeout - elapsed
            if remaining > 0 and remaining % 30 == 0:
                print(f"  Still waiting... {remaining}s remaining")

        print("Login timed out. Closing browser.")
        return False

    def ensure_logged_in(self):
        if self.is_logged_in():
            print("Already logged in")
            return True
        return self.login_google()

    def open_my_courses(self) -> bool:
        try:
            self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "user-avatar"))
            ).click()

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@href,'mycourses')]")
                )
            ).click()

            print("Opened My Courses")
            return True
        except TimeoutException:
            print("  Could not open My Courses (profile menu not found)")
            return False

    def go_to_course(self, course_name: str) -> bool:
        print(f"Opening course: {course_name}")

        try:
            course_card = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     f"//div[contains(@class, 'course-card')]"
                     f"[.//p[contains(@class, 'course-title') and "
                     f"normalize-space()='{course_name}']]")
                )
            )
        except TimeoutException:
            print(f"  Course not found: '{course_name}'")
            print("  Check the course name in config.yaml (exact spelling and casing)")
            return False

        go_button = course_card.find_element(
            By.XPATH, ".//a[contains(text(), 'Go To Course')]"
        )
        self.wait.until(EC.element_to_be_clickable(go_button))
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", go_button
        )
        go_button.click()
        print("Course opened successfully")
        return True

    def get_week_names(self) -> list[str]:
        week_buttons = self.wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button[.//h3[starts-with(normalize-space(), 'Week')]]")
            )
        )
        names = []
        for btn in week_buttons:
            h3 = btn.find_element(By.XPATH, ".//h3")
            names.append(h3.text.strip())
        print(f"Found {len(names)} weeks")
        return names

    def expand_week(self, week_name: str):
        print(f"  Opening {week_name}")

        week_button = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//button[.//h3[normalize-space()='{week_name}']]")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", week_button
        )

        if week_button.get_attribute("aria-expanded") == "false":
            week_button.click()
            self.wait.until(
                lambda d: week_button.get_attribute("aria-expanded") == "true"
            )

    def get_lesson_names(self, week_name: str) -> list[str]:
        time.sleep(2)

        items = self.driver.execute_script("""
            const weekName = arguments[0];
            const buttons = document.querySelectorAll(
                'button[aria-expanded="true"][aria-controls^="unit-"][aria-controls$="-list"]'
            );
            let containerId = null;
            for (const btn of buttons) {
                const h3 = btn.querySelector('h3');
                if (h3 && h3.textContent.trim() === weekName) {
                    containerId = btn.getAttribute('aria-controls');
                    break;
                }
            }
            if (!containerId) return [];
            const container = document.getElementById(containerId);
            if (!container) return [];
            const lessonButtons = container.querySelectorAll('button');
            return Array.from(lessonButtons)
                .map(btn => {
                    const p = btn.querySelector('p');
                    return p ? p.textContent.trim() : btn.textContent.trim();
                })
                .filter(t => t.length > 0);
        """, week_name)

        print(f"  Found {len(items)} lessons")
        return items

    def click_lesson(self, lesson_name: str):
        print(f"    Opening lesson: {lesson_name}")

        item = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 f"//button[.//p[normalize-space()='{lesson_name}']]")
            )
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", item
        )
        item.click()

    def get_youtube_link(self) -> str | None:
        try:
            iframe = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            self.driver.switch_to.frame(iframe)

            youtube = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'youtube.com/watch')]")
                )
            )
            href = youtube.get_attribute("href")

            self.driver.switch_to.default_content()
            return href
        except TimeoutException:
            self.driver.switch_to.default_content()
            return None
