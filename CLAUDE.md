# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Doc2MD is a local Python CLI tool that converts photos (JPG/PNG) and PDFs into structured Markdown. It serves as a preprocessing step so AI tools (Claude Code, Claude API) receive faithful text rather than freely-interpreted image/PDF content.

## Development Commands

```bash
# Setup
uv sync

# Run — single file
uv run doc2md.py input/seite1.jpg

# Run — folder
uv run doc2md.py input/ output/

# Run with OCR forced (recommended for photos)
uv run doc2md.py input/ output/ --force-ocr

# Run with LLM enhancement via OpenRouter
uv run doc2md.py input/ output/ --use-llm

# Merge multiple pages into one markdown file
uv run doc2md.py input/kapitel3/ output/kapitel3.md --merge
```

No test framework is configured yet.

## Architecture

Single-file CLI (`doc2md.py`) using **Marker** (`marker-pdf`) as the conversion engine, invoked as a Python library (not subprocess). No GUI — CLI only.

**Flow:** Input file/folder → Marker conversion (with optional OCR + LLM post-processing) → Markdown output

### Critical Design Constraints

- **LLM access via OpenRouter or Ollama** — use `marker.services.openai.OpenAIService` with a configurable base URL. **Never use `marker.services.gemini` or `GOOGLE_API_KEY` directly.**
- Two providers: OpenRouter (default, cloud) and Ollama (`--ollama`, local)
- OpenRouter: API key from env var `OPENROUTER_API_KEY`, default model `google/gemini-2.5-flash`
- Ollama: optional API key from `OLLAMA_API_KEY`, default model `gemma4`, base URL `http://localhost:11434/v1`
- Images (JPG/PNG) always get `force_ocr=True`; PDFs only when `--force-ocr` flag is set
- LLM errors degrade gracefully — warn and continue without LLM
- `--merge` combines files alphabetically with `---` separators
- Output dir created automatically; output filenames mirror input with `.md` extension
- Exit code 0 on success, 1 on errors

### Marker LLM Configuration (when `--use-llm`)

Both providers use the same OpenAI-compatible service — only the base URL and model change:

```python
llm_service = "marker.services.openai.OpenAIService"
openai_base_url = base_url    # OpenRouter or Ollama URL
openai_api_key = api_key      # from env var
openai_model = model           # provider-specific default
```

## CLI Options

```
uv run doc2md.py [INPUT] [OUTPUT] [OPTIONS]

INPUT               File or folder (default: ./input/)
OUTPUT              Output folder or file (default: ./output/)

--force-ocr         Force OCR (recommended for photos)
--use-llm           Enable LLM post-processing (via OpenRouter or Ollama)
--ollama            Use local Ollama model instead of OpenRouter
--ollama-url URL    Ollama API base URL (default: http://localhost:11434/v1)
--model MODEL       Model name (default: gemma4 for Ollama, google/gemini-2.5-flash for OpenRouter)
--merge             Merge all input files into one markdown file
--lang LANG         OCR language (default: de,en)
--verbose           Verbose output
```

## Dependencies

Managed via `uv` — see `pyproject.toml` for the dependency list and `uv.lock` for the lockfile.

## User Context

The user (Kowi) is a low-code expert (KNIME), not a programmer. The tool must be simple to install (`uv sync`) and run. Runs locally on Windows or Linux, CPU-only compatible.

## Typical Use Cases

1. **BWR textbook** — photograph pages → Markdown → Claude creates lessons from exact book content
2. **KNIME training** — PDF materials → Markdown for RAG or AI-assisted course prep
3. **Bytes & Budgets** — technical literature as Markdown knowledge base for content creation
4. **Siemens LCS** — structured capture of customer documents for workflow analysis
