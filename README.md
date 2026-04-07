# 📄 Doc2MD

**Convert photos and PDFs to clean, structured Markdown — powered by AI vision.**

Ever tried feeding a photo of a textbook page to an AI and got back a garbled mess? Doc2MD solves this. It turns your document photos and PDFs into faithful Markdown text that AI tools (Claude, ChatGPT, etc.) can work with perfectly.

---

## ✨ What It Does

| Input               | Method           | Output         |
| ------------------- | ---------------- | -------------- |
| 📸 Photos (JPG/PNG) | AI Vision Model  | Clean Markdown |
| 📑 PDFs             | Local Marker OCR | Clean Markdown |

- **Photos** are sent to a vision AI model (Gemini 2.5 Flash via [OpenRouter](https://openrouter.ai)) that _sees_ the page layout — columns, sidebars, definition boxes, tables — and produces structured Markdown
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

### 3. Set up your API key

You need an [OpenRouter](https://openrouter.ai) API key for photo conversion (and optional PDF LLM enhancement).

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

> 💡 Get your key at [openrouter.ai/keys](https://openrouter.ai/keys). Gemini 2.5 Flash is very affordable — typically just a few cents per page.

### 4. Convert!

```bash
# Drop files in input/ and run
uv run doc2md.py

# Or point at a specific file
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
  --use-llm           Enable LLM post-processing for PDFs (via OpenRouter)
  --vision            Force vision mode even for PDFs
  --model MODEL       OpenRouter model (default: google/gemini-2.5-flash)
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
```

## 📋 Requirements

- **[uv](https://docs.astral.sh/uv/)** — Python package manager (installs Python automatically if needed)
- **Python 3.11+**
- **OpenRouter API key** — for photo conversion and optional PDF LLM enhancement
- **~2GB disk space** — for Marker's ML models (only downloaded if you process PDFs)
- Works on **Windows, macOS, and Linux**
- Runs on **CPU** — no GPU required (GPU speeds things up if available)

## 📦 Dependencies

| Package                                                  | Purpose                                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [marker-pdf](https://github.com/datalab-to/marker)       | PDF to Markdown conversion (includes OCR, layout detection, table recognition) |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Load API key from `.env` file                                                  |
| [openai](https://pypi.org/project/openai/)               | OpenRouter API client (installed with marker-pdf)                              |

## 🔑 About OpenRouter

[OpenRouter](https://openrouter.ai) is a unified API gateway that gives you access to many AI models (Google Gemini, Anthropic Claude, OpenAI, etc.) through a single API key. Doc2MD uses it to access Google's Gemini 2.5 Flash vision model for photo conversion.

**Why OpenRouter instead of the Google API directly?** One API key, one billing account, easy model switching. You can change the model with `--model` if you want to try alternatives.

## 🤝 Built With AI

This project was built using [Claude Code](https://claude.ai/code) (Anthropic's CLI coding agent) in a vibe coding session. The entire tool — from concept to working code — was developed through conversational AI pair programming.

## 📄 License

MIT — use it, fork it, make it yours. 🎉
