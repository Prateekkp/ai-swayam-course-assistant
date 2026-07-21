import os
import re
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

CHUNK_SIZE = 900  # words per chunk
MAX_RETRIES = 3


def _call_llm(system_prompt: str, user_content: str, max_tokens: int = 4000, config: dict = None) -> str:
    provider = config.get("llm", {}).get("provider", "groq") if config else "groq"

    if provider == "nvidia":
        return _call_nvidia(system_prompt, user_content, max_tokens, config)
    else:
        return _call_groq(system_prompt, user_content, max_tokens, config)


def _call_nvidia(system_prompt: str, user_content: str, max_tokens: int, config: dict) -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    model = config.get("llm", {}).get("nvidia_model", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    stream = True
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream" if stream else "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "model": model,
        "max_tokens": max_tokens,
        "reasoning_budget": 16384,
        "stream": stream,
        "temperature": 0.6,
        "top_p": 0.95,
        "chat_template_kwargs": {"enable_thinking": True},
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                NVIDIA_URL, headers=headers, json=payload, stream=stream, timeout=120
            )
            response.raise_for_status()
            content = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                        try:
                            chunk = json.loads(decoded[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                content += delta["content"]
                        except json.JSONDecodeError:
                            continue
            return content
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"      NVIDIA API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                continue
            raise


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

    return _call_llm(
        system,
        f"Extract key points from this lecture transcript:\n\n{text}",
        max_tokens=2000,
        config=config,
    )


def merge_key_points(chunk_summaries: list[str]) -> str:
    merged = "\n\n".join(
        f"### Chunk {i + 1} Key Points\n{summary}"
        for i, summary in enumerate(chunk_summaries)
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


def make_study_notes(transcript_text: str, config: dict) -> str:
    provider = config.get("llm", {}).get("provider", "groq")
    print(f"    Using LLM provider: {provider}")

    print("    Chunking transcript...")
    chunks = chunk_transcript(transcript_text)
    print(f"    Split into {len(chunks)} chunks")

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"    Extracting key points from chunk {i + 1}/{len(chunks)}...")
        summary = extract_key_points(chunk, config)
        chunk_summaries.append(summary)

    print("    Merging key points...")
    merged = merge_key_points(chunk_summaries)

    print("    Generating study notes...")
    notes = generate_notes(merged, config)

    print("    Generating MCQs...")
    mcqs = generate_mcqs(merged, config)

    return notes, mcqs
