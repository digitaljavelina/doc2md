---
name: doc2md
description: Convert photos (JPG/PNG) and PDFs in any folder to Markdown using doc2md. Supports OpenRouter and Ollama. Use when asked to "convert to markdown", "doc2md", "process documents", or "extract text from images/PDFs".
---

# Doc2MD — Document to Markdown Converter

Converts all supported files (JPG, PNG, PDF) in a folder to Markdown, outputting `.md` files alongside the originals with matching filenames.

## CRITICAL: API Key Security

**NEVER read, cat, print, or inspect the contents of `.doc2md.env` files.** The API key must stay local and never enter the conversation context. Only reference the file path in `source` commands.

## Step 1: Get the target folder

Use `AskUserQuestion`:

```
Question: "Which folder contains the files to convert?"
Options:
1. Current directory
2. Custom path — user specifies a folder
```

Resolve the folder to an absolute path. Verify it exists and contains supported files (`.jpg`, `.jpeg`, `.png`, `.pdf`).

List the files found and confirm with the user before proceeding.

## Step 2: Check for existing config

Check if `.doc2md.env` exists in the target folder:

```bash
test -f /path/to/folder/.doc2md.env && echo "CONFIG_EXISTS" || echo "NO_CONFIG"
```

**Do NOT read the file contents.** Only check existence.

- If config exists → skip to Step 4.
- If no config → continue to Step 3.

## Step 3: Set up credentials (first time only)

### 3a: Ask which provider

Use `AskUserQuestion`:

```
Question: "Which LLM provider do you want to use?"
Options:
1. OpenRouter (cloud — needs API key, default model: google/gemini-2.5-flash)
2. Ollama (local — optional API key, default model: gemma4)
```

### 3b: Securely store the API key

Tell the user to run the setup script with the `!` prefix so the key stays out of this conversation:

```
Please run this command to set up your API key (your key will NOT be visible to me):

! bash /Users/michaelhenry/Documents/Projects/Python/doc2md/doc2md_setup.sh /path/to/folder
```

Replace `/path/to/folder` with the actual target folder path.

**Wait for the user to confirm they've run the setup before proceeding.**

After they confirm, verify the config was created:

```bash
test -f /path/to/folder/.doc2md.env && echo "CONFIG_READY" || echo "CONFIG_MISSING"
```

If still missing, ask them to try again.

## Step 4: Run the conversion

The doc2md repo is at `/Users/michaelhenry/Documents/Projects/Python/doc2md`.

### 4a: Determine flags from config

Read ONLY the provider and model lines (not the API key):

```bash
grep -E '^(DOC2MD_PROVIDER|DOC2MD_MODEL)=' /path/to/folder/.doc2md.env
```

This is safe — it only extracts the provider name and model, not the key.

### 4b: Build and run the command

Use a temp output directory. Source the env file so doc2md picks up the key from the environment, but the key never appears in output:

```bash
TMPOUT=$(mktemp -d) && \
source /path/to/folder/.doc2md.env && \
export OPENROUTER_API_KEY OLLAMA_API_KEY 2>/dev/null; \
cd /Users/michaelhenry/Documents/Projects/Python/doc2md && \
uv run doc2md.py /path/to/folder "$TMPOUT" \
  [FLAGS] \
  --verbose && \
echo "TMPOUT=$TMPOUT"
```

**Flag logic based on provider:**

- **OpenRouter**: `--use-llm --model $DOC2MD_MODEL`
- **Ollama**: `--ollama --use-llm --model $DOC2MD_MODEL`

**IMPORTANT — `--use-llm` is ALWAYS required.** It enables the API connection that powers
both vision mode (images) and LLM post-processing (PDFs). Without it, images have no
model to call and PDFs get no enhancement.

**NEVER pass `--force-ocr` for images (JPG/PNG).** That flag forces files through Marker's
local OCR pipeline, which is designed for PDFs and produces poor results on photos.
Only use `--force-ocr` when the folder contains scanned PDFs that need OCR treatment.

### 4c: Move output files to source folder

After conversion, move the `.md` files from the temp output back to the source folder:

```bash
# Find the daily subfolder in temp output
MD_DIR=$(find "$TMPOUT" -name "*.md" -exec dirname {} \; | head -1)
# Copy .md files to source folder
cp "$MD_DIR"/*.md /path/to/folder/
# Restore originals from bin/ (doc2md moves them there after conversion)
if [ -d "/path/to/folder/bin" ]; then
  mv /path/to/folder/bin/* /path/to/folder/ 2>/dev/null
  rmdir /path/to/folder/bin 2>/dev/null
fi
# Clean up temp
rm -rf "$TMPOUT"
```

## Step 5: Report results

Tell the user:

- How many files were converted
- List the generated `.md` files
- Remind them that `.doc2md.env` contains their API key and should not be committed to git

## Error handling

- If doc2md.py fails, show the error output to the user
- If the env file is missing mid-run, guide them back to Step 3
- If no supported files are found in the folder, tell the user which formats are supported (JPG, PNG, PDF)

## Notes

- The `.doc2md.env` file persists in the folder so subsequent runs skip setup
- To change provider or key, the user re-runs the setup script: `! bash .../doc2md_setup.sh /path/to/folder`
- Output `.md` files use the same base name as the input (e.g., `photo.jpg` → `photo.md`)
- The `.doc2md.env` file should be added to `.gitignore` if the folder is in a repo
