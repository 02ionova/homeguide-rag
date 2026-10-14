# HomeGuide

A calm, English-language chat application for owners of three Bosch household appliances. Ask about operation, maintenance or troubleshooting; HomeGuide retrieves the selected manual's pages and asks an LLM to answer with clickable citations such as `[Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 34]`. Both a FastAPI web interface and a Python CLI are included. No frontend build tools are needed.

## Supported documents

The original files in the workspace were inspected before implementation. All page numbers below are **1-based physical PDF page numbers**, including covers; numbers printed inside a manual may differ.

| Appliance | Supported model/family from the actual PDF | Filename | Total pages | Indexed physical pages | Chunks |
|---|---|---|---:|---|---:|
| Washing machine | Bosch WAV28EH3GB | `Bosch-WAV28EH3GB-Washing-Machine.pdf` | 60 | 1–57, 60 | 137 |
| Dishwasher | Bosch SMS8ZDI86M | `Bosch-SMS8ZDI86M-Dishwasher.pdf` | 56 | 1–52, 56 | 140 |
| Coffee machine | Bosch TIS 3.3. family | `Bosch-TIS-3.3-Coffee-Machine.pdf` | 176 | 1, 5–26 | 69 |

The washing and dishwasher manuals are English. The coffee manual also contains French, Dutch, Polish, Czech, Russian and German; only English and the shared cover are embedded. Shared coffee diagram pages 2–4 remain available in the original PDF but contain no meaningful extractable text. Blank/manufacturer backmatter pages outside the selected ranges are excluded. No OCR was needed. The coffee cover identifies a family, not a more precise model; the app does not assume one.

`documents.json` records page ranges, safety pages, model names, original SHA-256 hashes and example questions. It is the allowlist for ingestion and PDF serving. Original PDFs are never modified.

## Setup on Mac / PyCharm

Use **Python 3.14**, Apple Silicon, and macOS 14 or newer for the pinned native embedding stack. This workspace was verified with Python 3.14.0. Other Python/platform combinations are not verified; install suitable native wheels if adapting it.

From the project root:

```bash
python3.14 -m venv .homeguide-venv
source .homeguide-venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` locally and set `LLM_API_KEY` to your own OpenAI API key. Never paste a key into browser code, source files, Git or chat. The existing unrelated `main.py` exercise and existing `.venv` are preserved; neither is part of HomeGuide. Use the separate interpreter above.

The concrete default provider is **OpenAI**, using its **Responses API** with structured JSON output and `store: false`, with default model `gpt-4.1-mini`. An API account with access to that model is required. Only the question and selected retrieved excerpts are sent to the configured provider; embeddings run locally. LLM API usage may incur costs. `store: false` disables response storage but does not override provider data policies.

Initial embedding-model setup downloads `sentence-transformers/all-MiniLM-L6-v2` from Hugging Face. The app defaults its model cache to ignored `data/models/`; set `HF_HOME` before launch to use a different cache. After one successful download, `HF_HUB_OFFLINE=1` can be used for ingestion/retrieval without model network checks. Generation still requires network access to the LLM.

## Configuration

Environment variables override `.env`. Paths are resolved relative to the project root, so PyCharm does not need Python-path edits.

| Variable | Default | Meaning |
|---|---|---|
| `LLM_API_KEY` | empty | Required for answers; server-side only |
| `LLM_MODEL` | `gpt-4.1-mini` | OpenAI model with structured Responses output |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API base URL; custom endpoints must implement Responses and strict JSON Schema |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-attempt timeout, 1–120 seconds |
| `LLM_RETRIES` | `2` | Additional retries for transport failures, HTTP 408/409/429/5xx; 0–3 |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Same model for documents/questions; changing it requires reindexing |
| `CHROMA_DIR` | `data/chroma` | Persistent local vector database |
| `TOP_K` | `6` | Number of semantic chunk matches, 1–15, before page/context expansion |

Restart the server after changing configuration. The default MiniLM model produces normalized 384-dimensional embeddings on CPU, including on Apple Silicon. There is no CUDA/Metal configuration requirement.

## Ingest, ask and run

The three supplied manuals already exist locally. On a fresh checkout, obtain them from the official links below and save them in `pdfs/` under the readable filenames in the supported-documents table. Bosch's original download filenames differ; the PDF contents must remain unchanged.

```bash
# Ingest all registered PDFs from pdfs/; repeat runs are idempotent.
python -m scripts.ingest

# Explicit rebuild: publishes a new complete generation.
python -m scripts.ingest --rebuild

# Ask an appliance-specific question (requires LLM_API_KEY).
python -m scripts.query --appliance washing-machine "How do I activate the washing machine’s child lock?"
python -m scripts.query --appliance dishwasher "How do I clean the dishwasher filter?"
python -m scripts.query --appliance coffee-machine "How do I start the coffee machine’s cleaning programme?"
python -m scripts.query --appliance coffee-machine --json "What should I check if coffee flows slowly?"

# Retrieval diagnostics: real embeddings, no LLM key/API cost.
python -m scripts.query --appliance dishwasher --sources-only "How do I clean the dishwasher filter?"

# Local web application.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Select an appliance; switching appliances or choosing New chat resets the visible conversation. Enter sends; Shift+Enter adds a line break. Every question is standalone: repeat relevant details in follow-ups. Sources shows semantic pages, adjacent procedure context and safety context; a citation opens the registered PDF at `#page=N` where the browser PDF viewer supports it. Browser preferences may cause downloads instead.

In PyCharm, select **Settings → Project → Python Interpreter → Add Local Interpreter → Existing**, and choose `.homeguide-venv/bin/python`. Create Python run configurations using **Module name**, with this project as working directory:

- `scripts.ingest`, optional parameters `--rebuild`.
- `scripts.query`, parameters `--appliance dishwasher "How do I clean the dishwasher filter?"`.
- `uvicorn`, parameters `app.main:app --host 127.0.0.1 --port 8000`.

`.env` is loaded by the backend; no EnvFile plugin or manual `PYTHONPATH` setting is required.

## Verified example questions and citations

These questions were checked against actual extracted text and real semantic retrieval. **Live LLM answers were not verified because no local API key was available.** Expected citations list the supporting physical pages; a complete answer may also cite relevant supplied safety pages.

| Question | Expected supporting citations | Support checked |
|---|---|---|
| How do I activate the washing machine’s child lock? | `[Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 34]` | Hold the two labelled Child Lock buttons for approximately 3 seconds; lock persists after switch-off |
| How should I clean the washing machine drum? | `[Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 40]` | Drum clean without laundry, all-purpose washing powder; ventilation/temperature conditions |
| How do I clean the dishwasher filter? | `[Bosch-SMS8ZDI86M-Dishwasher.pdf, p. 40]`, `[Bosch-SMS8ZDI86M-Dishwasher.pdf, p. 41]` | Check residue, remove/disassemble, rinse, reassemble and align; original diagrams required for orientation |
| How often should I run Machine Care? | `[Bosch-SMS8ZDI86M-Dishwasher.pdf, p. 39]` | On reminder; every 2 months for appliances without a reminder, without tableware |
| How do I start the coffee machine’s cleaning programme? | `[Bosch-TIS-3.3-Coffee-Machine.pdf, p. 21]`, `[Bosch-TIS-3.3-Coffee-Machine.pdf, p. 22]` | Calc’nClean start and complete procedure, approximately 40 minutes, cleaning/descaling precautions |
| What should I check if coffee flows slowly? | `[Bosch-TIS-3.3-Coffee-Machine.pdf, p. 23]`, `[Bosch-TIS-3.3-Coffee-Machine.pdf, p. 15]` | Possible fine grind, limescale or air in filter; grinding adjustment only while grinder runs; never reach into grinder |

A question absent from all three manuals is **“What is tomorrow’s weather in Prague?”** Expected answer:

> I don’t know based on the provided documents.

The fallback is enforced when the model reports insufficient evidence. Automated tests mock that response; a live model's answerability judgment has not been measured. Similarity scores do not establish that the manual contains an answer.

**Illustrative invocation/output — manually checked against page 34, not a live API result:**

```text
$ python -m scripts.query --appliance washing-machine "How do I activate the washing machine’s child lock?"
Press and hold the two buttons labelled “Child Lock push 3 sec.” for approximately
3 seconds. The controls lock, and the childproof lock remains active even after
the machine is switched off. [Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 34]
```

**Actual local ingestion result:** 346 chunks (137 washing machine, 140 dishwasher, 69 coffee machine) across 134 text-bearing pages. Repeating ingestion returned `status: unchanged`, the same collection, and the same chunk count. See [manual-support evaluation](docs/ANSWER_EVALUATION.md) and [verification record](docs/VERIFICATION.md) for the practical limits of these checks.

## How the RAG pipeline works

```text
Registered PDFs → PyMuPDF text per physical page → conservative cleanup
→ 140-word chunks with 30-word overlap → normalized MiniLM embeddings
→ persistent Chroma (cosine search; filename/page/appliance/model/chunk ID)

Selected appliance + question → same MiniLM embedder → top-k filtered chunks
→ complete matching pages + adjacent pages + selected manual safety pages
→ labelled untrusted reference data + question → OpenAI Responses API
→ citation allowlist + exact evidence quote checks → web/CLI answer and sources
```

Cleanup removes standalone page numbers/`en`, soft hyphens and line-wrapped word breaks, while retaining useful headings, warnings, units and conditions. Repeated headers are conservatively retained instead of risking deletion of procedure context. Chunks stay on one physical page. Chunk IDs are deterministic SHA-256 values of filename, page, ordinal and text.

A content fingerprint covers actual PDF hashes, manifest, model and chunk settings. Matching ingestion runs reuse the existing index without duplication. Changed manuals, manifest or embedding model trigger a new generation. An ingestion lock prevents concurrent writers. The active pointer is replaced only after every document is validated and embedded; a failed rebuild leaves the old index intact. Old generations are retained for in-flight readers and may consume disk space. To reclaim space, stop the server and delete the configured **generated** Chroma directory, then ingest again; preserve `pdfs/`.

Retrieval filters by appliance before vector search. Matching pages are reconstructed from overlapping chunks in order, supplemented with neighboring indexed pages to preserve procedure continuations, plus registered safety pages. There is no arbitrary similarity cutoff for answerability. Missing or stale indexes fail with an ingestion command instead of silently using mismatched embeddings.

The LLM is instructed to treat PDF text as reference data, retain conditions/warnings, state possible causes cautiously, acknowledge missing diagrams/icons, and decline unsupported questions. Structured output contains an answerability flag and exact evidence quotes. Code verifies the `[filename, p. N]` syntax, page allowlist, citations on each paragraph/numbered step, and quote presence on every cited page. Invalid output is regenerated once, then rejected with a useful error. Transport failures use bounded retries with short backoff; provider response bodies and secret values are never displayed. Unknown appliances require clarification; source PDFs can only be accessed by registered ID.

## Checks

```bash
# Fast automated checks: generated synthetic PDFs, real Chroma, deterministic test
# embeddings and mocked LLM HTTP responses. No PDFs/model download/API key needed.
python -m pytest -q

# Actual supplied manuals + real MiniLM + persisted Chroma. Ingest first.
HF_HUB_OFFLINE=1 python -m pytest -m integration -q

# Browser checks against the running server (all chat requests are mocked).
python -m playwright install chromium
python -m scripts.verify_browser

# Dependency consistency and staged-file/credential-pattern inspection.
python -m pip check
python -m scripts.check_staged
```

Default pytest discovers only `tests/`, preserving the unrelated root exercise. Integration tests are explicitly opt-in. Browser checks mock all chat requests, including the missing-key response, so they work safely with a configured API key and never make paid LLM requests; screenshots are saved in ignored `data/screenshots/`. Backend tests separately exercise the real missing-key path. Browser automation covers desktop/mobile widths, message keyboard handling, loading, duplicate submissions, citations/source excerpts, unsafe HTML displayed as text, reset behavior, exact fallback and connection errors.

## Limitations

- **No live LLM verification:** no local API key was configured. Real PDF ingestion, embeddings, storage, semantic retrieval, web/CLI error handling, mocked generation and browser interaction were verified. Add a key and evaluate generated answers before relying on them.
- **Grounding is probabilistic:** valid metadata and verbatim quotes cannot prove that every claim follows from the text. A model can cite real pages while misinterpreting them. Review cited originals, particularly safety procedures. Prompt injection defenses are instructions and validation, not a guarantee of semantic correctness.
- **Text-only extraction:** tables may flatten; control icons may disappear; a diagram may carry essential orientation information. No OCR, image understanding, or diagram reconstruction is provided. The model is instructed to call out these dependencies and link the original manual. Multilingual diagram-only pages are accessible but not embedded.
- **Context completeness:** top-k search and neighboring/safety pages improve coverage but cannot guarantee every distant prerequisite or warning is retrieved. Long individual sentences can be split; chunks preserve page context, not a full semantic document structure.
- **Scope:** only registered models/manuals, English output, no accounts, repair diagnosis, web search, conversational memory or deployment. Chats live in browser memory and reset on reload. Run locally on loopback; this is not a public multi-user service.
- **PDF numbering:** citations use original physical pages, never inferred printed numbering. `#page` behavior depends on the browser.
- **Redistribution unresolved:** no sample PDFs are committed. The university requirement to include 3–5 sample PDFs remains outstanding until permission is established.

## Official manual sources and ownership

The provided manuals are Bosch/BSH manufacturer documents; HomeGuide does not claim ownership or a license to redistribute them. Official download links were checked:

- [WAV28EH3GB — Bosch-WAV28EH3GB-Washing-Machine.pdf](https://media3.bosch-home.com/Documents/9001599859_B.pdf)
- [SMS8ZDI86M — Bosch-SMS8ZDI86M-Dishwasher.pdf](https://media3.bosch-home.com/Documents/9001722657_D.pdf)
- [TIS 3.3. family — Bosch-TIS-3.3-Coffee-Machine.pdf](https://media3.bosch-home.com/Documents/8001036206_B.pdf)

Downloads being publicly accessible does **not** establish redistribution permission. PDFs, extracted text, caches, embeddings and indexes are ignored by Git. Keep the originals local; see [pdfs/README.md](pdfs/README.md). To add another manual, obtain permission/authorized access, inspect it, and add a manifest entry with its model, language, physical page ranges, safety pages and verified questions.

## GitHub repository

Private repository: [02ionova/homeguide-rag](https://github.com/02ionova/homeguide-rag). Sign in to the authorized GitHub account to view it.

The five original implementation milestones were committed locally while GitHub authentication was unavailable. The existing history was preserved, including the later readable-filename update. After GitHub CLI authentication, the private repository was created and the commits were pushed using a normal push. No deployment, public visibility or force push was used.

For future changes, from the project root:

```bash
git status
git add <changed-project-files>
python -m scripts.check_staged
git diff --cached --check
git commit -m "Describe your change"
git push origin main
```

The local `.env` and its API key, PDFs without redistribution permission, generated vector stores/cache, virtual environments and IDE settings are excluded. All committed file versions were scanned for credential patterns and the configured local API key before the initial push. Automated scanning is an aid, not exhaustive proof; always inspect staged changes before committing.
