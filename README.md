# RAG_MANIM

Educational pipeline that indexes textbooks with [PageIndex](https://github.com/VectifyAI/PageIndex), builds a **semantic curriculum layer** (summaries, concept graphs, retrieval metadata), and connects to Manim-style explanation workflows.

## Repository layout

```
RAG_MANIM/
├── PageIndex/          # Vendored fork of [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex) with local RAG pipeline changes
├── VR_Classroom/       # Submodule — frontend classroom demo (optional)
├── scripts/            # Curriculum builders (e.g. Chemistry Class IX)
├── results/            # Generated artifacts (gitignored, regeneratable)
├── logs/               # Runtime logs (gitignored)
└── .env                # Local API keys (gitignored — use .env.example)
```

`PageIndex/` is **vendored in this repository** (full source tree). `VR_Classroom/` is a **git submodule** (see `.gitmodules`).

## Prerequisites

- **macOS / Linux**, Python **3.10+**
- **Git** with submodule support
- **Ollama** (recommended for local PageIndex runs): [https://ollama.com](https://ollama.com)
- Optional cloud keys: OpenAI / Google Gemini (see `.env.example`)

## Quick start

### 1. Clone with submodules

```bash
git clone --recurse-submodules <your-rag-manim-repo-url> RAG_MANIM
cd RAG_MANIM
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Or add submodules manually:

```bash
git submodule add https://github.com/mallanagoudagp/VR_Classroom.git VR_Classroom
```

### 2. Fix “embedded git repository” after `git add .`

If Git warned about `PageIndex` or `VR_Classroom`:

```bash
git rm --cached -r PageIndex VR_Classroom 2>/dev/null || true
git submodule update --init --recursive
git add .gitignore README.md .env.example scripts/
```

Then initialize the VR_Classroom submodule:

```bash
git submodule update --init --recursive
```

### 3. Environment variables

```bash
cp .env.example .env
# Edit .env with your API keys (file is gitignored)
```

### 4. PageIndex virtualenv

```bash
cd PageIndex
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Pull a local model (example used in recent runs):

```bash
ollama pull qwen2.5:3b
```

### 5. Index a PDF (PageIndex CLI)

From the `PageIndex` directory:

```bash
cd PageIndex
PYTHONPATH=. ./venv/bin/python run_pageindex.py \
  --pdf_path examples/documents/Chemistry_9.pdf
```

Artifacts (default when cwd is `PageIndex/`):

```
PageIndex/results/Chemistry_9.pdf/
```

### 6. Build semantic curriculum layer (Chemistry IX)

From the **RAG_MANIM project root**:

```bash
cd /path/to/RAG_MANIM
PageIndex/venv/bin/python scripts/build_chemistry9_semantic_layer.py
```

Output location (this script writes to the **project root**, not `PageIndex/results/`):

```
results/Chemistry_9.pdf/
├── extracted_pages.json      # evidence layer
├── validated_toc.json
├── structure.json            # full semantic tree
├── summaries.json
├── concept_graph.json
├── pedagogical_metadata.json
├── retrieval_metadata.json
└── …
```

Verify:

```bash
ls -la results/Chemistry_9.pdf/
```

Expected success line:

```
Generated 35 nodes, validation passed=True
```

## Results: two paths (important)

| Tool | Working directory | Output folder |
|------|-------------------|---------------|
| `PageIndex/run_pageindex.py` | `PageIndex/` | `PageIndex/results/<pdf_name>/` |
| `scripts/build_chemistry9_semantic_layer.py` | `RAG_MANIM/` | `results/<pdf_name>/` |

`PageIndex/results/chemistry_9/` is **not** used by the chemistry builder. Use `results/Chemistry_9.pdf/` at the repo root after running the script above.

## Regenerating curriculum outputs

```bash
PageIndex/venv/bin/python scripts/build_chemistry9_semantic_layer.py
```

Evidence files (`extracted_pages.json`, `validated_toc.json`, etc.) are refreshed from  
`PageIndex/examples/documents/Chemistry_9.pdf`.

## Optional: VR_Classroom

```bash
cd VR_Classroom
# See VR_Classroom/README.md for frontend setup
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: pageindex` | Run with `PageIndex/venv/bin/python` and ensure `PageIndex/` submodule exists |
| `ModuleNotFoundError: ollama` | Use PageIndex venv: `PageIndex/venv/bin/pip install -r PageIndex/requirements.txt` |
| Empty `PageIndex/results/chemistry_9/` | Wrong path — use `results/Chemistry_9.pdf/` at project root after the semantic script |
| `git add` embedded repo warning | Use submodules + root `.gitignore`; run `git rm --cached -r PageIndex VR_Classroom` |
| PageIndex inference timeouts | Smaller model, `--max-pages N`, or increase timeouts in `PageIndex/config.yaml` |

## Security

- **Never commit** `.env` or API keys.
- If keys were committed previously, rotate them and purge from git history.

## License

PageIndex and VR_Classroom retain their upstream licenses. Scripts and docs in this repo follow the root project license once added.
