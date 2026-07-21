# AI SWAYAM Course Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](https://github.com/Prateekkp/ai-swayam-course-assistant/pulls)
[![Made with Love](https://img.shields.io/badge/Made%20with-%E2%9D%A4%EF%B8%8F-red.svg)](https://github.com/Prateekkp/ai-swayam-course-assistant)

An AI-powered tool that automatically downloads SWAYAM lectures, transcribes them, and generates comprehensive study notes and practice MCQs using LLM models.

---

## Features

- **Auto-download** lectures from SWAYAM platform via YouTube
- **Audio transcription** using OpenAI Whisper
- **Smart chunking** for handling long transcripts (>3000 words)
- **AI-powered study notes** with structured Markdown output
- **Auto-generated MCQs** (15 questions with answers)
- **Dual LLM support** — Choose between Groq or NVIDIA APIs
- **Incremental processing** — Skips already processed lectures

---

## Prerequisites

- Python 3.10 or higher
- Google Chrome browser
- ChromeDriver (auto-managed by Selenium)
- API key from [Groq](https://console.groq.com) or [NVIDIA](https://build.nvidia.com)

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
GROQ_API_KEY=your_groq_api_key_here
NVIDIA_API_KEY=your_nvidia_api_key_here
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
  save_audio: true       # Set false to skip saving audio files
  save_transcript: true  # Set false to skip saving transcripts

selenium:
  wait_timeout: 20
  login_timeout: 120     # Seconds to wait for manual login

transcription:
  chunk_length_ms: 600000  # 10 minutes per chunk
```

### Switching LLM Providers

| Provider | Set `llm.provider` | Free Tier |
|----------|-------------------|-----------|
| [Groq](https://console.groq.com) | `"groq"` | Yes (rate limited) |
| [NVIDIA](https://build.nvidia.com) | `"nvidia"` | Yes (credits) |

### Provider Comparison

| Aspect | Groq | NVIDIA |
|--------|------|--------|
| Speed | Fast inference | Slower inference |
| Quality | Good (slight compromise) | Great (better notes & MCQs) |
| Best for | Quick generation, large transcripts | High-quality academic content |

> **Recommendation:** Use **Groq** for speed or **NVIDIA** for best quality. Both work well — choose based on your priority.

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
2. Download audio from YouTube
3. Transcribe audio to text
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
            ├── audio.mp3         # Downloaded audio
            └── transcript.txt    # Raw transcript
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
    ├── browser.py           # Selenium browser automation
    ├── scraper.py           # Lesson discovery
    ├── downloader.py        # YouTube audio download
    ├── transcriber.py       # Whisper transcription
    └── notes.py             # AI-powered notes generation
```

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
| Transcript too long | Tool auto-chunks transcripts into ~900 word segments |

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

- [Groq](https://groq.com) for fast LLM inference
- [NVIDIA](https://nvidia.com) for AI APIs
- [OpenAI Whisper](https://github.com/openai/whisper) for transcription
- [SWAYAM](https://swayam.gov.in) for open education

---

## Support

If you find this helpful, give it a ⭐ on GitHub!
