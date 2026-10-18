import os
import re
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

CHUNK_SIZE = 1800  # words per chunk (optimized for 120B context window)
MAX_RETRIES = 5    # Increased to give multiple retries across keys

_nvidia_key_lock = threading.Lock()
_nvidia_key_index = 0

REFUSAL_CHECK_PATTERNS = [
    r"i['’]?m sorry",
    r"as an ai",
    r"cannot (generate|create|provide|produce)",
    r"can['’]?t (generate|create|provide|produce)",
    r"key points .* empty",
    r"please (provide|supply)",
]


def get_nvidia_api_keys() -> list[str]:
    """Retrieve all configured NVIDIA API keys from environment variables."""
    keys = []
    # Primary key
    k1 = os.getenv("NVIDIA_API_KEY")
    if k1 and k1.strip():
        keys.append(k1.strip())

    # Additional keys: NVIDIA_API_KEY_2, NVIDIA_API_KEY_3...
    i = 2
    while True:
        k = os.getenv(f"NVIDIA_API_KEY_{i}")
        if k and k.strip():
            keys.append(k.strip())
            i += 1
        else:
            break

    # Also support comma-separated NVIDIA_API_KEYS
    csv_keys = os.getenv("NVIDIA_API_KEYS")
    if csv_keys:
        for k in csv_keys.split(","):
            cleaned = k.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    return keys


def get_base_nvidia_key_index() -> int:
    """Thread-safe round-robin allocation of the starting key index for a request."""
    global _nvidia_key_index
    keys = get_nvidia_api_keys()
    if not keys:
        raise ValueError("No NVIDIA API key found. Please set NVIDIA_API_KEY in .env")

    with _nvidia_key_lock:
        idx = _nvidia_key_index
        _nvidia_key_index = (_nvidia_key_index + 1) % len(keys)
        return idx


def get_nvidia_key_for_attempt(base_idx: int, attempt: int) -> tuple[str, int, int]:
    """Retrieve key alternating strictly across retries: (base_idx + attempt) % len(keys)."""
    keys = get_nvidia_api_keys()
    idx = (base_idx + attempt) % len(keys)
    return keys[idx], idx + 1, len(keys)


def _call_llm(system_prompt: str, user_content: str, max_tokens: int = 4000, config: dict = None) -> str:
    provider = config.get("llm", {}).get("provider", "groq") if config else "groq"

    if provider == "nvidia":
        return _call_nvidia(system_prompt, user_content, max_tokens, config)
    else:
        return _call_groq(system_prompt, user_content, max_tokens, config)


def _call_nvidia(system_prompt: str, user_content: str, max_tokens: int, config: dict) -> str:
    model = config.get("llm", {}).get("nvidia_model", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    stream = True

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "model": model,
        "max_tokens": max_tokens,
        "stream": stream,
        "temperature": 0.5,
        "top_p": 0.95,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    last_error = None
    base_key_idx = get_base_nvidia_key_index()

    for attempt in range(MAX_RETRIES):
        # Pick key strictly alternating: Attempt 0 -> Key 1, Attempt 1 -> Key 2, Attempt 2 -> Key 1, etc.
        api_key, key_num, total_keys = get_nvidia_key_for_attempt(base_key_idx, attempt)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
        }

        try:
            response = requests.post(
                NVIDIA_URL, headers=headers, json=payload, stream=stream, timeout=120
            )

            # Check HTTP-level errors (429, 401, 500, etc.)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

            content = ""
            stream_error = None

            for line in response.iter_lines():
                if not line:
                    continue

                decoded = line.decode("utf-8")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    try:
                        chunk = json.loads(decoded[6:])

                        # Check for in-stream errors (e.g. ResourceExhausted)
                        if "error" in chunk:
                            err_val = chunk["error"]
                            msg = err_val.get("message", str(err_val)) if isinstance(err_val, dict) else str(err_val)
                            stream_error = f"In-stream error: {msg}"
                            break

                        choices = chunk.get("choices")
                        if choices and len(choices) > 0:
                            delta = choices[0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                content += delta["content"]

                    except json.JSONDecodeError:
                        continue

            if stream_error:
                raise RuntimeError(stream_error)

            if not content.strip():
                raise RuntimeError("NVIDIA API returned empty content (token limit or silent cutoff).")

            return content

        except Exception as e:
            last_error = e
            wait_time = 2 * (attempt + 1)
            print(f"      [Key {key_num}/{total_keys}] NVIDIA call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"      Switching key and waiting {wait_time}s before retry...")
                time.sleep(wait_time)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed across NVIDIA keys. Last error: {last_error}")


def _call_groq(system_prompt: str, user_content: str, max_tokens: int, config: dict) -> str:
    from groq import Groq

    client = Groq()
    model = config.get("llm", {}).get("groq_model", "llama-3.3-70b-versatile")

    for attempt in range(MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.6,
                max_completion_tokens=max_tokens,
                top_p=0.95,
                stream=True,
                stop=None,
            )
            content = ""
            for chunk in completion:
                delta = chunk.choices[0].delta.content or ""
                content += delta
            return content
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"      Groq API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(2 * (attempt + 1))
                continue
            raise


def chunk_transcript(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        sentence_word_count = len(sentence.split())
        if current_word_count + sentence_word_count > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_word_count = 0
        current_chunk.append(sentence)
        current_word_count += sentence_word_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def extract_key_points(text: str, config: dict) -> str:
    system = """You are an expert academic content extractor. Extract key points from this lecture transcript.

Output ONLY a structured summary with these sections:

## Topics Covered
- List all main topics discussed

## Key Definitions
- List all important definitions with brief explanations

## Important Concepts
- List all key concepts with concise explanations

## Comparisons and Differences
- List any comparisons or contrasts mentioned

## Examples Given
- List all real-world examples discussed

## Key Formulas or Frameworks
- List any formulas, frameworks, or models mentioned

RULES:
- Be comprehensive. Do NOT omit any topic, definition, or concept.
- Keep each point concise (1-2 lines max).
- Use bullet points only.
- Do NOT add explanations or commentary.
- Do NOT use emojis."""

    result = _call_llm(
        system,
        f"Extract key points from this lecture transcript:\n\n{text}",
        max_tokens=2000,
        config=config,
    )

    if not result or len(result.strip()) < 50:
        raise ValueError("Key points extraction returned empty or insufficient content.")

    return result


def merge_key_points(chunk_summaries: list[str]) -> str:
    valid_summaries = [s for s in chunk_summaries if s and len(s.strip()) > 30]
    if not valid_summaries:
        raise ValueError("Cannot merge key points: all chunk summaries were empty.")

    merged = "\n\n".join(
        f"### Chunk {i + 1} Key Points\n{summary}"
        for i, summary in enumerate(valid_summaries)
    )
    return merged


def generate_notes(merged_key_points: str, config: dict) -> str:
    system = """You are an expert university professor and instructional designer.

Convert the provided key points into comprehensive Study Notes for a first-time learner.

Requirements:
- Assume the reader has ZERO prior knowledge.
- Explain every important concept in simple language.
- Introduce concepts gradually, starting with basics before advanced frameworks.
- Include short explanations after every important definition.
- Use real-world examples wherever possible.
- Preserve all technical accuracy.
- Do NOT omit important concepts.
- Organize the notes using proper Markdown headings.
- Use tables for comparisons (e.g., project vs. process).
- Retain all real-world examples mentioned.
- Do NOT copy transcript sentences directly.
- Do NOT use emojis.

The output must follow this structure exactly:

# Study Notes

## Lecture Overview
- Topic
- Learning Objectives

## Introduction

## Important Concepts

## Important Definitions

## Examples discussed in the lecture

## Key Terminology

## Characteristics of Projects

## Project vs Process (Comparison Table)

## Importance of Project Management Today

## Common Mistakes / Misconceptions

## Practical Applications

## Summary"""

    result = _call_llm(
        system,
        f"Convert these key points into study notes:\n\n{merged_key_points}",
        max_tokens=4000,
        config=config,
    )

    if not result or len(result.strip()) < 200:
        raise ValueError("Generated study notes are empty or too short.")

    # Check for refusal
    for pat in REFUSAL_CHECK_PATTERNS:
        if re.search(pat, result[:300], re.IGNORECASE):
            raise ValueError(f"LLM refusal detected in study notes: {result[:100]}")

    idx = result.find("# Study Notes")
    return result[idx:] if idx != -1 else result


def generate_mcqs(merged_key_points: str, config: dict) -> str:
    system = """You are an experienced university examiner. Generate 15 multiple-choice questions (MCQs) from the provided key points.

Each MCQ must have:
- A clear question
- 4 options (A, B, C, D)
- The correct answer indicated

Ensure a mix of:
- Recall-based questions (definitions, facts)
- Understanding-based questions (explain concepts)
- Application-based questions (real-world scenarios)

Output format:

# Practice MCQs

1. Question text?
   A) Option one
   B) Option two
   C) Option three
   D) Option four
   **Answer: X**

2. Question text?
   A) Option one
   B) Option two
   C) Option three
   D) Option four
   **Answer: X**

(Continue for all 15 questions)

RULES:
- Do NOT invent concepts not present in the lecture.
- Questions should cover the entire lecture content.
- Avoid repetition.
- Do NOT use emojis."""

    result = _call_llm(
        system,
        f"Generate 15 MCQs from these key points:\n\n{merged_key_points}",
        max_tokens=4000,
        config=config,
    )

    if not result or len(result.strip()) < 200:
        raise ValueError("Generated MCQs are empty or too short.")

    # Check for refusal
    for pat in REFUSAL_CHECK_PATTERNS:
        if re.search(pat, result[:300], re.IGNORECASE):
            raise ValueError(f"LLM refusal detected in MCQs: {result[:100]}")

    idx = result.find("# Practice MCQs")
    return result[idx:] if idx != -1 else result


def save_output(notes: str, mcqs: str, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    notes_path = output_dir / "study_notes.md"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes)
    print(f"    Saved: {notes_path.name}")

    mcqs_path = output_dir / "practice_mcqs.md"
    with open(mcqs_path, "w", encoding="utf-8") as f:
        f.write(mcqs)
    print(f"    Saved: {mcqs_path.name}")

    return notes_path, mcqs_path


def make_study_notes(transcript_text: str, config: dict) -> tuple[str, str]:
    provider = config.get("llm", {}).get("provider", "groq")
    keys = get_nvidia_api_keys() if provider == "nvidia" else ["Groq"]
    print(f"    Using LLM provider: {provider} ({len(keys)} active key(s) configured)")

    print("    Chunking transcript...")
    chunks = chunk_transcript(transcript_text)
    print(f"    Split into {len(chunks)} chunks")

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"    Extracting key points from chunk {i + 1}/{len(chunks)}...")
        summary = extract_key_points(chunk, config)
        chunk_summaries.append(summary)
        time.sleep(1.0)  # Gentle spacing between calls to stay within worker slots

    print("    Merging key points...")
    merged = merge_key_points(chunk_summaries)

    print("    Generating study notes & MCQs in parallel (ThreadPoolExecutor)...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_notes = executor.submit(generate_notes, merged, config)
        future_mcqs = executor.submit(generate_mcqs, merged, config)

        notes = future_notes.result()
        mcqs = future_mcqs.result()

    return notes, mcqs
