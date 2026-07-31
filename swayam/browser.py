import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


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

    def _ensure_default_content(self):
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

    def _wait_for_idle(self):
        try:
            for _ in range(10):
                state = self.driver.execute_script("return document.readyState")
                if state == "complete":
                    return
                time.sleep(1)
        except Exception:
            pass

    def click_lesson(self, lesson_name: str):
        print(f"    Opening lesson: {lesson_name}")
        self._ensure_default_content()
        time.sleep(2)

        found = self.driver.execute_script("""
            const name = arguments[0];
            for (const btn of document.querySelectorAll('button')) {
                const p = btn.querySelector('p');
                if (p && p.textContent.trim() === name) {
                    btn.scrollIntoView({block:'center'});
                    btn.click();
                    return true;
                }
            }
            return false;
        """, lesson_name)

        if not found:
            raise Exception(f"Lesson button not found: {lesson_name}")

        time.sleep(5)

    def select_transcript_language(self, language: str = "English"):
        print(f"    Selecting transcript language: {language}")
        time.sleep(2)

        # Find the dropdown trigger button using Selenium (Radix UI needs real click)
        try:
            trigger = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "#panel-transcript button[data-slot='dropdown-menu-trigger'],"
                     "#panel-transcript button.hidden")
                )
            )
        except TimeoutException:
            print("    Could not find language dropdown trigger")
            return False

        current_text = trigger.text.strip().replace("\n", " ")
        print(f"    Current dropdown text: {current_text}")

        # If already showing the desired language, skip clicking
        if language.lower() in current_text.lower() and "select" not in current_text.lower():
            print(f"    Language already set to {language}")
            return True

        # Real Selenium click on the dropdown trigger
        trigger.click()
        print("    Clicked dropdown trigger, waiting for menu...")
        time.sleep(2)

        # Find the dropdown menu content (Radix UI renders it in a portal)
        try:
            menu_item = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//div[@data-slot='dropdown-menu-content']//div[@role='menuitem'][normalize-space()='{language}']"
                     f" | //div[@role='menu']//div[@role='menuitem'][normalize-space()='{language}']"
                     f" | //*[@data-state='open']//div[@role='menuitem'][normalize-space()='{language}']")
                )
            )
            menu_item.click()
            print(f"    Clicked language: {language}")
            time.sleep(5)
            return True
        except TimeoutException:
            print(f"    Menu item '{language}' not found via XPath, trying JavaScript...")

        # Fallback: use JS to click the language option
        selected = self.driver.execute_script("""
            const lang = arguments[0];
            const items = document.querySelectorAll('[role="menuitem"], [data-slot="dropdown-menu-item"]');
            for (const item of items) {
                if (item.textContent.trim().toLowerCase() === lang.toLowerCase()) {
                    item.click();
                    return true;
                }
            }
            return false;
        """, language)

        if selected:
            print(f"    Selected via JS fallback: {language}")
            time.sleep(5)
            return True

        print(f"    Could not select language: {language}")
        return False

    def scrape_transcript(self, language: str = "English") -> str | None:
        print("    Scraping transcript from page...")
        self._ensure_default_content()
        time.sleep(2)

        # Click the Transcript tab if not already active
        self.driver.execute_script("""
            const tabs = document.querySelectorAll('button, [role="tab"]');
            for (const tab of tabs) {
                if (tab.textContent.trim() === 'Transcript') {
                    tab.click();
                    return true;
                }
            }
            return false;
        """)
        time.sleep(3)

        # Select language
        self.select_transcript_language(language)

        # Wait for transcript content to appear
        time.sleep(3)

        # Extract transcript text from span elements
        result = self.driver.execute_script("""
            const panel = document.getElementById('panel-transcript');
            if (!panel) return {text: null, debug: 'no panel'};

            // Primary: get spans with title="Jump to this part" (transcript segments)
            let spans = panel.querySelectorAll('span[title="Jump to this part"]');
            let method = 'title-attr';
            if (spans.length === 0) {
                // Fallback: spans with role="button" inside a <p> tag
                spans = panel.querySelectorAll('p span[role="button"]');
                method = 'p-span-role';
            }
            if (spans.length === 0) {
                // Fallback: any span with cursor-pointer inside transcript content
                spans = panel.querySelectorAll('span.cursor-pointer');
                method = 'cursor-pointer';
            }

            if (spans.length > 0) {
                const parts = [];
                for (const span of spans) {
                    const text = span.textContent.trim();
                    if (text) parts.push(text);
                }
                return {text: parts.join(' '), debug: method + ':' + spans.length + ' spans'};
            }

            // Last resort: find the <p> with transcript text
            const pTags = panel.querySelectorAll('p');
            for (const p of pTags) {
                const text = p.innerText.trim();
                if (text.length > 50) {  // Transcript paragraphs are long
                    return {text: text, debug: 'p-tag:' + text.length + ' chars'};
                }
            }

            // Final fallback: get all text from bg-white div
            const contentDiv = panel.querySelector('.bg-white');
            if (contentDiv) {
                const text = contentDiv.innerText.trim();
                return {text: text, debug: 'bg-white:' + text.length + ' chars'};
            }

            return {text: null, debug: 'nothing found, panel HTML length=' + panel.innerHTML.length};
        """)

        if result and result.get("text") and len(result["text"].strip()) > 15:
            transcript = result["text"].strip()
            print(f"    Transcript scraped ({len(transcript)} chars) via {result.get('debug', '?')}")
            return transcript

        debug_info = result.get("debug", "unknown") if result else "no result"
        print(f"    No transcript found - debug: {debug_info}")
        return None


