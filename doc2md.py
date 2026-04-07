#!/usr/bin/env python3
"""
Doc2MD – Convert photos and PDFs to structured Markdown.

This CLI tool converts document files (photos, PDFs) into clean Markdown text.
It uses two conversion strategies depending on the input file type:

  - Images (JPG/PNG): Sent to a vision AI model via OpenRouter API. The model
    "sees" the page layout and produces structured Markdown directly. This works
    far better than OCR for complex layouts like textbooks with columns, sidebars,
    definition boxes, and mixed content.

  - PDFs: Processed locally using the Marker library (https://github.com/datalab-to/marker),
    which extracts text structure without needing an API call. Optionally, an LLM
    can post-process the Marker output for better quality (--use-llm flag).

Output is organized into daily folders (output/YYYY-MM-DD/) and processed source
files are moved to a bin/ folder to avoid re-processing.

Usage:
    python doc2md.py                          # Process all files in ./input/
    python doc2md.py photo.jpg                # Single image via vision model
    python doc2md.py document.pdf             # Single PDF via Marker
    python doc2md.py input/ output/ --merge   # Merge all into one .md file

Requirements:
    pip install -r requirements.txt
    Set OPENROUTER_API_KEY in .env file (required for images, optional for PDFs)
"""

import argparse
import base64
import os
import shutil
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# File types the tool can process
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# Image files automatically use vision mode (unless --force-ocr is set)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# System prompt for the vision model. Instructs the AI to faithfully reproduce
# the document content as Markdown without translating or interpreting anything.
VISION_SYSTEM_PROMPT = """You are an expert at converting document pages into structured Markdown.

Rules:
- Reproduce the COMPLETE text of the page, omit nothing
- Use correct Markdown structure: # for main headings, ## for subheadings, etc.
- Tables as Markdown tables
- Lists as Markdown lists
- Definition boxes and info boxes as blockquotes (>) with an appropriate label
- Clearly mark assignments/tasks
- Omit page numbers, headers and footers
- Image references as [Image: brief description]
- Stick exactly to the original text — add nothing, interpret nothing
- Preserve the original language of the document (do NOT translate)
- Reply ONLY with the Markdown, no explanations before or after"""


def collect_files(input_path: Path) -> list[Path]:
    """
    Gather all processable files from the given path.

    If input_path is a single file, validates its extension and returns it.
    If input_path is a directory, collects all supported files sorted alphabetically
    (important for --merge mode to get a consistent page order).

    Returns a list of Path objects. Exits with error if no valid files found.
    """
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [input_path]
        print(f"Error: Unsupported format: {input_path.suffix}", file=sys.stderr)
        sys.exit(1)

    if input_path.is_dir():
        files = sorted(
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not files:
            print(f"Error: No supported files in {input_path}", file=sys.stderr)
            sys.exit(1)
        return files

    print(f"Error: Path not found: {input_path}", file=sys.stderr)
    sys.exit(1)


def convert_vision(filepath: Path, api_key: str, model: str, verbose: bool,
                    base_url: str = "https://openrouter.ai/api/v1") -> str:
    """
    Convert an image file to Markdown using a vision AI model via OpenRouter.

    This is the preferred method for photos of documents (textbook pages, handouts, etc.)
    because the vision model understands layout, columns, boxes, and reading order —
    things that traditional OCR struggles with.

    The image is base64-encoded and sent to the OpenRouter API along with a system
    prompt that instructs the model to output faithful Markdown.

    Args:
        filepath: Path to the image file (JPG or PNG)
        api_key:  OpenRouter API key
        model:    Model ID on OpenRouter (e.g. "google/gemini-2.5-flash")
        verbose:  Whether to print progress info

    Returns:
        The Markdown text produced by the vision model.
    """
    import openai

    if verbose:
        print(f"Vision mode: {filepath.name}")

    # Read the image and encode it as base64 for the API
    image_data = filepath.read_bytes()
    b64 = base64.b64encode(image_data).decode("utf-8")

    # Determine MIME type for the data URL
    suffix = filepath.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"

    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    # Send the image + prompt to the vision model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": "Convert this document page into structured Markdown.",
                    },
                ],
            },
        ],
    )

    return response.choices[0].message.content


def build_converter(force_ocr: bool, langs: str, use_llm: bool, model: str, verbose: bool,
                    api_key: str = "", base_url: str = "https://openrouter.ai/api/v1"):
    """
    Build a Marker PdfConverter for local PDF-to-Markdown conversion.

    Marker (https://github.com/datalab-to/marker) is used as a Python library
    (not as a subprocess). It loads ML models for layout detection, OCR, and
    text recognition.

    If --use-llm is enabled, Marker's OpenAI-compatible service is configured to
    route through OpenRouter for LLM-assisted post-processing (better tables,
    formulas, structure). If the API key is missing or LLM init fails, it falls
    back gracefully to local-only processing.

    Args:
        force_ocr: Force OCR even on digital PDFs (useful for scanned PDFs)
        langs:     Comma-separated OCR languages (e.g. "de,en")
        use_llm:   Whether to enable LLM post-processing
        model:     OpenRouter model ID for LLM mode
        verbose:   Whether to print progress info

    Returns:
        Tuple of (PdfConverter instance, artifact_dict).
        The artifact_dict contains loaded ML models — expensive to create,
        so it's created once and reused.
    """
    # Lazy imports: Marker is heavy (~2GB of models on first run),
    # so we only import it when actually needed (not for vision-only runs)
    from marker.converters.pdf import PdfConverter
    from marker.config.parser import ConfigParser
    from marker.models import create_model_dict

    config = {
        "output_format": "markdown",
        "force_ocr": force_ocr,
        "langs": langs,
    }

    # Configure LLM post-processing via OpenRouter if requested
    if use_llm:
        if not api_key:
            print("Warning: API key not set. Continuing without LLM.", file=sys.stderr)
            use_llm = False
        else:
            config.update({
                "use_llm": True,
                "llm_service": "marker.services.openai.OpenAIService",
                "openai_api_key": api_key,
                "openai_base_url": base_url,
                "openai_model": model,
            })

    config_parser = ConfigParser(config)

    if verbose:
        print("Loading Marker models...")

    # Load ML models (layout, OCR, table recognition, etc.)
    # First run downloads ~2GB of models; subsequent runs use the cache
    artifact_dict = create_model_dict()

    # Build the converter; if LLM setup fails, fall back to local-only
    try:
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=artifact_dict,
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
            llm_service=config_parser.get_llm_service() if use_llm else None,
        )
    except Exception as e:
        if use_llm:
            # Graceful degradation: LLM failed, but local conversion still works
            print(f"Warning: LLM init failed ({e}). Continuing without LLM.", file=sys.stderr)
            config.pop("use_llm", None)
            config.pop("llm_service", None)
            config.pop("openai_api_key", None)
            config.pop("openai_base_url", None)
            config.pop("openai_model", None)
            config_parser = ConfigParser(config)
            converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=artifact_dict,
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )
        else:
            raise

    return converter, artifact_dict


def convert_file(converter, filepath: Path, verbose: bool) -> str:
    """
    Convert a single file to Markdown using the Marker library.

    Used for PDFs (and optionally images when --force-ocr is set).

    Args:
        converter: A configured Marker PdfConverter instance
        filepath:  Path to the file to convert
        verbose:   Whether to print progress info

    Returns:
        The extracted Markdown text.
    """
    from marker.output import text_from_rendered

    if verbose:
        print(f"Marker mode: {filepath.name}")

    rendered = converter(str(filepath))
    # text_from_rendered returns (text, metadata, images) — we only need the text
    text, _, _ = text_from_rendered(rendered)
    return text


def _resolve_ollama_model(base_url: str, preferred: str, verbose: bool) -> str:
    """
    Find the best matching Ollama model name.

    The Ollama OpenAI-compatible endpoint requires the exact model ID
    (e.g. "gemma4:e4b"), not just the short name ("gemma4"). This function
    queries the available models and picks the one that starts with the
    preferred name.
    """
    import urllib.request
    import json

    models_url = base_url.rstrip("/").removesuffix("/v1") + "/api/tags"
    try:
        with urllib.request.urlopen(models_url, timeout=5) as resp:
            data = json.loads(resp.read())
        names = [m["name"] for m in data.get("models", [])]
    except Exception:
        if verbose:
            print(f"Warning: Could not query Ollama models at {models_url}. Using '{preferred}' as-is.")
        return preferred

    # Exact match first, then prefix match
    for name in names:
        if name == preferred:
            return name
    for name in names:
        if name.startswith(preferred + ":") or name.startswith(preferred + "/"):
            if verbose:
                print(f"Resolved Ollama model: {preferred} -> {name}")
            return name

    if verbose:
        print(f"Warning: No Ollama model matching '{preferred}' found. Available: {', '.join(names)}")
    return preferred


def main():
    """
    Main entry point: parse arguments, route files to the right converter,
    write output to daily folders, and move processed files to bin/.
    """

    # ── CLI argument setup ──────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Doc2MD - Convert photos and PDFs to structured Markdown"
    )
    parser.add_argument("input", nargs="?", default="./input/",
                        help="Input file or folder (default: ./input/)")
    parser.add_argument("output", nargs="?", default="./output/",
                        help="Output folder or file (default: ./output/)")
    parser.add_argument("--force-ocr", action="store_true",
                        help="Force Marker OCR for images (instead of vision mode)")
    parser.add_argument("--use-llm", action="store_true",
                        help="Enable LLM post-processing via OpenRouter (Marker mode)")
    parser.add_argument("--vision", action="store_true",
                        help="Force vision mode for PDFs too")
    parser.add_argument("--ollama", action="store_true",
                        help="Use a local Ollama model instead of OpenRouter")
    parser.add_argument("--ollama-url", default="http://localhost:11434/v1",
                        help="Ollama API base URL (default: http://localhost:11434/v1)")
    parser.add_argument("--model", default=None,
                        help="Model name (default: gemma4 for Ollama, google/gemini-2.5-flash for OpenRouter)")
    parser.add_argument("--merge", action="store_true",
                        help="Merge all input files into one Markdown file")
    parser.add_argument("--lang", default="de,en",
                        help="OCR language (default: de,en)")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    # Load .env file for API keys
    load_dotenv()

    # ── Resolve provider settings ───────��────────────────────────���─────
    if args.ollama:
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
        base_url = args.ollama_url
        model = args.model or _resolve_ollama_model(base_url, "gemma4", args.verbose)
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api/v1"
        model = args.model or "google/gemini-2.5-flash"

    # ── Resolve paths and collect input files ───────────────────────────
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    files = collect_files(input_path)

    if args.verbose:
        provider = f"Ollama ({base_url})" if args.ollama else "OpenRouter"
        print(f"Provider: {provider}, Model: {model}")
        print(f"Files found: {len(files)}")

    # ── Route files to vision vs. Marker mode ───────────────────────────
    #
    # Default behavior:
    #   Images (JPG/PNG) -> vision mode (best for photos of documents)
    #   PDFs             -> Marker mode (local, no API needed)
    #
    # Overrides:
    #   --force-ocr : ALL files go through Marker (even images)
    #   --vision    : ALL files go through vision mode (even PDFs)
    #
    vision_files = []
    marker_files = []
    for f in files:
        is_image = f.suffix.lower() in IMAGE_EXTENSIONS
        if args.force_ocr:
            marker_files.append(f)
        elif is_image or args.vision:
            vision_files.append(f)
        else:
            marker_files.append(f)

    # Vision mode requires an API key (unless using Ollama)
    if vision_files and not api_key:
        print("Error: OPENROUTER_API_KEY not set. Required for images.", file=sys.stderr)
        sys.exit(1)

    if vision_files and args.verbose:
        print(f"Vision mode: {len(vision_files)} file(s)")
    if marker_files and args.verbose:
        print(f"Marker mode: {len(marker_files)} file(s)")

    # ── Build Marker converter (only if there are PDFs to process) ──────
    # Skipped entirely for vision-only runs, avoiding the heavy model load
    converter = None
    if marker_files:
        converter, _ = build_converter(
            force_ocr=args.force_ocr, langs=args.lang,
            use_llm=args.use_llm, model=model, verbose=args.verbose,
            api_key=api_key, base_url=base_url,
        )

    # ── Convert all files ───────────────────────────────────────────────
    results = []   # List of (filepath, markdown_text) tuples
    errors = 0
    for filepath in files:
        try:
            if filepath in vision_files:
                text = convert_vision(filepath, api_key, model, args.verbose, base_url)
            else:
                text = convert_file(converter, filepath, args.verbose)
            results.append((filepath, text))
        except Exception as e:
            print(f"Error converting {filepath.name}: {e}", file=sys.stderr)
            errors += 1

    if not results:
        print("Error: No files could be converted.", file=sys.stderr)
        sys.exit(1)

    # ── Write output to daily folder (output/YYYY-MM-DD/) ──────────────
    # Each day gets its own subfolder to keep outputs organized over time.
    today = date.today().isoformat()
    if output_path.suffix == ".md":
        # User specified an explicit .md output path — use its parent dir
        daily_dir = output_path.parent
    else:
        daily_dir = output_path / today
    daily_dir.mkdir(parents=True, exist_ok=True)

    if args.merge:
        # Merge mode: combine all converted files into one Markdown file
        # separated by horizontal rules (---)
        out_file = daily_dir / "merged.md"
        merged = "\n\n---\n\n".join(text for _, text in results)
        out_file.write_text(merged, encoding="utf-8")
        print(f"Merged: {out_file}")
    else:
        # Normal mode: one .md file per input file
        for filepath, text in results:
            out_file = daily_dir / (filepath.stem + ".md")
            out_file.write_text(text, encoding="utf-8")
            if args.verbose:
                print(f"Written: {out_file}")

    # ── Move processed source files to bin/ ─────────────────────────────
    # Successfully converted files are moved to input/bin/ so they won't
    # be processed again on the next run. Failed files stay in place.
    bin_dir = Path(args.input).resolve()
    if bin_dir.is_file():
        bin_dir = bin_dir.parent
    bin_dir = bin_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    for filepath, _ in results:
        dest = bin_dir / filepath.name
        shutil.move(str(filepath), str(dest))
        if args.verbose:
            print(f"Moved: {filepath.name} -> bin/")

    # ── Summary ─────────────────────────────────────────────────────────
    total = len(results)
    print(f"Done: {total} file(s) converted.", end="")
    if errors:
        print(f" {errors} error(s).", end="")
    print()

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
