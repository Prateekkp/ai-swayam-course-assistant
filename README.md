# AI SWAYAM Course Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](https://github.com/Prateekkp/ai-swayam-course-assistant/pulls)
[![Made with Love](https://img.shields.io/badge/Made%20with-%E2%9D%A4%EF%B8%8F-red.svg)](https://github.com/Prateekkp/ai-swayam-course-assistant)

An AI-powered tool that scrapes transcripts directly from SWAYAM lectures and generates comprehensive study notes and practice MCQs using LLM models.

---

## Features

- **Transcript scraping** — Fetches transcripts directly from SWAYAM's built-in transcript panel
- **Language selection** — Automatically selects English transcripts
- **Smart chunking** for handling long transcripts (~900 words per chunk)
- **AI-powered study notes** with structured Markdown output
- **Auto-generated MCQs** (15 questions with answers)
- **Dual LLM support** — Choose between Groq or NVIDIA APIs
- **Incremental processing** — Skips already processed lectures
- **Test mode** — Process specific weeks/lessons for testing

---

## Prerequisites

- Python 3.10 or higher
- Google Chrome browser
- ChromeDriver (auto-managed by Selenium)
- API key from [NVIDIA](https://build.nvidia.com) (or [Groq](https://console.groq.com))

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Prateekkp/ai-swayam-course-assistant.git
cd ai-swayam-course-assistant
```

### 2. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.sample .env
```

Edit `.env` and add your API key:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

> You only need the key for the provider you plan to use.

---

## Configuration

Edit `config.yaml` to customize settings:

```yaml
swayam:
  url: "https://swayam.gov.in/"
  course_name: "Project Management for Managers"  # Exact course name

llm:
  provider: "nvidia"  # "groq" or "nvidia"
  groq_model: "llama-3.3-70b-versatile"
  nvidia_model: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

output:
  base_dir: "output"
  save_transcript: true  # Set false to skip saving transcripts

selenium:
  wait_timeout: 20
  login_timeout: 120     # Seconds to wait for manual login

test:
  skip_weeks: 0             # Skip first N weeks (0 = start from first)
  max_weeks: null           # Process N weeks after skipping (null = all)
  max_lessons_per_week: null # Limit lessons per week (null = all)

transcription:
  language: "English"  # Language for video transcript selection on SWAYAM
```

### Test Mode

Limit processing to specific weeks/lessons during development:

```yaml
test:
  skip_weeks: 1             # Skip Week 0 (assignments only)
  max_weeks: 1              # Process only 1 week
  max_lessons_per_week: 1   # Process only 1 lesson per week
```

Set all to `null`/`0` to process all weeks and lessons.

### Switching LLM Providers

| Provider | Set `llm.provider` | Free Tier |
|----------|-------------------|-----------|
| [NVIDIA](https://build.nvidia.com) | `"nvidia"` | Yes (credits) |
| [Groq](https://console.groq.com) | `"groq"` | Yes (rate limited) |

### Provider Comparison

| Aspect | NVIDIA | Groq |
|--------|--------|------|
| Speed | Slower inference | Fast inference |
| Quality | Great (better notes & MCQs) | Good (slight compromise) |
| Best for | High-quality academic content | Quick generation |

> **Recommendation:** Use **NVIDIA** for best quality or **Groq** for speed.

---

## Usage

### 1. Run the assistant

```bash
python main.py
```

### 2. Login to SWAYAM

- A Chrome window will open
- Login to your SWAYAM account manually
- The tool will detect successful login

### 3. Wait for processing

The tool will automatically:
1. Discover all lessons in the course
2. Scrape transcripts from each lesson's transcript panel
3. Skip already-processed lessons (checks for `study_notes.md`)
4. Generate study notes (`study_notes.md`)
5. Generate practice MCQs (`practice_mcqs.md`)

---

## Output Structure

```
output/
└── Week1/
    └── 01_Lecture_Name/
        ├── study_notes.md        # Comprehensive study notes
        ├── practice_mcqs.md      # 15 MCQs with answers
        └── media/
            └── transcript.txt    # Scraped transcript
```

---

## Project Structure

```
ai-swayam-course-assistant/
├── main.py                 # Entry point
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── .env.sample             # Environment variables template
├── .gitignore
└── swayam/
    ├── __init__.py
    ├── browser.py           # Selenium browser automation + transcript scraping
    ├── scraper.py           # Lesson discovery and skip-check logic
    └── notes.py             # AI-powered notes generation
```

---

## How It Works

1. **Browser automation** logs into SWAYAM and navigates to your course
2. **Lesson discovery** expands each week and iterates through lessons
3. **Skip-check** — If `study_notes.md` exists, the lesson is skipped without opening it in the browser
4. **Transcript scraping** — For new lessons, the tool clicks the lesson, selects English from the transcript dropdown, and scrapes the transcript text
5. **Notes generation** — The transcript is chunked and sent to the LLM to generate structured study notes and MCQs

---

## Study Notes Structure

The generated study notes follow this structure:

```
# Study Notes
├── Lecture Overview
├── Introduction
├── Important Concepts
├── Important Definitions
├── Examples discussed in the lecture
├── Key Terminology
├── Characteristics of Projects
├── Project vs Process (Comparison Table)
├── Importance of Project Management Today
├── Common Mistakes / Misconceptions
├── Practical Applications
├── Summary
└── Practice MCQs (15 questions)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ChromeDriver not found | ChromeDriver is auto-managed; ensure Chrome is installed |
| Login timeout | Increase `selenium.login_timeout` in config |
| API rate limit | Switch provider or wait and retry |
| Transcript not found | Ensure the lesson has a transcript available on SWAYAM |
| Already-processed lessons being re-processed | Check that `output/` directory structure matches expected format |

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [NVIDIA](https://nvidia.com) for AI APIs
- [Groq](https://groq.com) for fast LLM inference
- [SWAYAM](https://swayam.gov.in) for open education

---

## Support

If you find this helpful, give it a ⭐ on GitHub!
