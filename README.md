# 📄 Doc2MD

**Convert photos and PDFs to clean, structured Markdown — powered by AI vision.**

Ever tried feeding a photo of a textbook page to an AI and got back a garbled mess? Doc2MD solves this. It turns your document photos and PDFs into faithful Markdown text that AI tools (Claude, ChatGPT, etc.) can work with perfectly.

---

## ✨ What It Does

| Input               | Method           | Output         |
| ------------------- | ---------------- | -------------- |
| 📸 Photos (JPG/PNG) | AI Vision Model  | Clean Markdown |
| 📑 PDFs             | Local Marker OCR | Clean Markdown |

- **Photos** are sent to a vision AI model that _sees_ the page layout — columns, sidebars, definition boxes, tables — and produces structured Markdown. Works with [OpenRouter](https://openrouter.ai) (cloud) or [Ollama](https://ollama.com) (local, we recommend Gemma 4)
- **PDFs** are processed locally using [Marker](https://github.com/datalab-to/marker), no API call needed
- Routing is **automatic**: drop in your files and Doc2MD picks the right method

## 🧠 Why Vision Instead of OCR for Photos?

Traditional OCR reads text fragments and tries to reassemble them. On complex layouts (textbooks, multi-column pages, pages with sidebars and boxes), this produces **unreadable garbage** — reversed text, mixed-up columns, garbled fragments.

A vision model actually _looks_ at the page like a human would. It understands reading order, layout structure, and context. The difference is night and day. 🌙☀️

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/kowalski-phil/doc2md.git
cd doc2md
```

### 2. Install dependencies

```bash
uv sync
```

> ⚠️ **First run will download ~2GB of ML models** (for Marker's PDF processing). This only happens once — subsequent runs use the cached models. If you only plan to process photos (not PDFs), the models are not downloaded at all.

### 3. Choose your AI provider

Doc2MD supports two AI providers for vision and LLM features. Pick whichever suits you:

#### Option A: OpenRouter (cloud, no setup)

[OpenRouter](https://openrouter.ai) gives you access to powerful cloud models with just an API key. Great if you don't want to run models locally.

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

> 💡 Get your key at [openrouter.ai/keys](https://openrouter.ai/keys). Gemini 2.5 Flash is very affordable — typically just a few cents per page.

Then run normally:

```bash
uv run doc2md.py "path/to/photo.jpg"
```

#### Option B: Ollama (local, private, free)

[Ollama](https://ollama.com) runs AI models directly on your machine — no API key needed, no data leaves your computer, and it's completely free.

1. Install Ollama from [ollama.com](https://ollama.com)

2. Pull a vision-capable model (we recommend **Gemma 4**):

```bash
ollama pull gemma4
```

> 💡 **Why Gemma 4?** It supports vision (reading images), text, and even audio — making it ideal for converting document photos to Markdown. It runs well on machines with 16GB+ RAM.

3. Run with the `--ollama` flag:

```bash
uv run doc2md.py "path/to/photo.jpg" --ollama
```

That's it — no API keys, no cloud, no cost.

> 💡 If your Ollama instance runs on a different machine or port, use `--ollama-url`:
>
> ```bash
> uv run doc2md.py photo.jpg --ollama --ollama-url http://192.168.1.100:11434/v1
> ```

### 4. Convert!

```bash
# Drop files in input/ and run (uses OpenRouter by default)
uv run doc2md.py

# Or use a local Ollama model
uv run doc2md.py --ollama

# Point at a specific file
uv run doc2md.py "path/to/photo.jpg"

# Or a whole folder
uv run doc2md.py input/ output/
```

## 📁 How Output Is Organized

```
output/
├── 2026-04-07/          # Daily folders (ISO date)
│   ├── page1.md
│   └── page2.md
├── 2026-04-08/
│   └── chapter3.md
└── ...

input/
├── bin/                 # Processed files are moved here automatically
│   ├── page1.jpg
│   └── page2.jpg
└── new_file.pdf         # Waiting to be processed
```

- ✅ Output goes into **daily folders** (`output/YYYY-MM-DD/`)
- ✅ Processed source files are **moved to `input/bin/`** so they won't be processed again
- ✅ Failed files **stay in place** for retry

## 🛠️ All Options

```
uv run doc2md.py [INPUT] [OUTPUT] [OPTIONS]

Arguments:
  INPUT               File or folder (default: ./input/)
  OUTPUT              Output folder (default: ./output/)

Options:
  --force-ocr         Use Marker OCR for images instead of vision mode
  --use-llm           Enable LLM post-processing for PDFs
  --vision            Force vision mode even for PDFs
  --ollama            Use local Ollama model instead of OpenRouter
  --ollama-url URL    Ollama API base URL (default: http://localhost:11434/v1)
  --model MODEL       Model name (default: gemma4 for Ollama, google/gemini-2.5-flash for OpenRouter)
  --merge             Merge all files into one Markdown file
  --lang LANG         OCR language (default: de,en)
  --verbose           Show detailed progress
```

### 💡 Examples

```bash
# Process everything in input/ with verbose output
uv run doc2md.py --verbose

# Convert a single photo
uv run doc2md.py "textbook_page.jpg"

# Convert a PDF with LLM enhancement
uv run doc2md.py "document.pdf" --use-llm

# Merge multiple chapter photos into one file
uv run doc2md.py input/chapter3/ output/ --merge

# Force vision mode for a PDF (useful for scanned PDFs)
uv run doc2md.py "scanned.pdf" --vision

# Use a different model
uv run doc2md.py "page.jpg" --model google/gemini-2.5-flash

# Use a local Ollama model (e.g. Gemma 4)
uv run doc2md.py "textbook_page.jpg" --ollama

# Use Ollama with LLM post-processing for PDFs
uv run doc2md.py "document.pdf" --ollama --use-llm
```

## 📋 Requirements

- **[uv](https://docs.astral.sh/uv/)** — Python package manager (installs Python automatically if needed)
- **Python 3.11+**
- **OpenRouter API key** — for photo conversion and optional PDF LLM enhancement (not needed with `--ollama`)
- **~2GB disk space** — for Marker's ML models (only downloaded if you process PDFs)
- Works on **Windows, macOS, and Linux**
- Runs on **CPU** — no GPU required (GPU speeds things up if available)

## 📦 Dependencies

| Package                                                  | Purpose                                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [marker-pdf](https://github.com/datalab-to/marker)       | PDF to Markdown conversion (includes OCR, layout detection, table recognition) |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Load API key from `.env` file                                                  |
| [openai](https://pypi.org/project/openai/)               | OpenRouter API client (installed with marker-pdf)                              |

## 🔑 About the AI Providers

### OpenRouter (cloud)

[OpenRouter](https://openrouter.ai) is a unified API gateway that gives you access to many AI models (Google Gemini, Anthropic Claude, OpenAI, etc.) through a single API key. Doc2MD uses it to access Google's Gemini 2.5 Flash vision model for photo conversion.

**Why OpenRouter instead of the Google API directly?** One API key, one billing account, easy model switching. You can change the model with `--model` if you want to try alternatives.

### Ollama (local)

[Ollama](https://ollama.com) lets you run open-source AI models locally on your own machine. Nothing is sent to the cloud — your documents stay private, and there are no API costs.

We recommend **Gemma 4** (`gemma4`) as the default Ollama model because it supports vision, runs efficiently on consumer hardware (16GB+ RAM), and produces high-quality Markdown from document photos. You can use any other Ollama model with `--model`, but make sure it supports vision if you're converting images.

## 🤝 Built With AI

This project was built using [Claude Code](https://claude.ai/code) (Anthropic's CLI coding agent) in a vibe coding session. The entire tool — from concept to working code — was developed through conversational AI pair programming.

## 📄 License

MIT — use it, fork it, make it yours. 🎉
