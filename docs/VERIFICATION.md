# Verification record

Verified locally on 14 October 2026 in the existing PyCharm workspace, using macOS 15.6 on Apple Silicon and Python 3.14.0. No sub-agents, external search in the application, deployment, public repository or force push were used.

## Actual data and persistence

- Inspected all three original PDFs with PyMuPDF; compared model names, page counts, language boundaries, extraction quality and example procedure text. No OCR required.
- Original SHA-256 values match `documents.json`; originals were not modified.
- Real MiniLM 384-dimensional embeddings and persistent Chroma: 346 unique chunks across 134 indexed text pages (137/140/69 chunks per appliance).
- Ran ingestion, repeated ingestion (same collection/count, `unchanged`), and an actual `--rebuild` (new collection, same 346 chunks and content fingerprint). Reopened storage from independent Python processes.
- Real semantic retrieval for all six manifest questions found the documented supporting physical pages; all returned pages belonged to the selected appliance. The absent weather question still retrieves neighbors, illustrating why distance cannot prove answerability.
- Actual retrieval-only CLI produced source JSON; actual answer CLI without credentials exited with a clear `LLM_API_KEY is missing` error.

## Automated checks

- `python -m pytest -q`: **31 passed**, 3 integration checks deselected. Synthetic PDF fixtures make these tests independent of redistribution-restricted manuals and model downloads. Chroma is real; fast-test embeddings are deterministic fixtures; LLM HTTP is mocked.
- `HF_HUB_OFFLINE=1 python -m pytest -m integration -q`: **3 passed** using the supplied manuals, cached real model and active persistent index. These do not call an LLM.
- Covered physical page/filename/model/chunk metadata, overlapping page-local chunks, idempotency, changed-document detection, explicit rebuild, failed-build preservation, writer locking, missing/unreadable/text-empty PDFs, changed embedding model, manifest path validation, selected-appliance filtering and missing indexes.
- Covered valid/invalid citations, invented source quotes, whitespace-only evidence, uncited paragraphs/numbered steps, one successful regeneration and one exhausted regeneration, transient retry/recovery, HTTP authorization/rate/server errors, timeouts, missing credentials, exact insufficient-information fallback and source text treated as untrusted reference data.
- The complete CLI and FastAPI query path was exercised with real synthetic-PDF extraction/Chroma retrieval and a mocked OpenAI Responses transport, including supported and absent questions.
- Backend web checks covered English HTML/assets, request validation, appliance clarification, source PDF content disposition, registered routes and traversal rejection, security headers and useful setup errors.
- `python -m pip check`: no broken requirements.
- `python -m compileall -q app scripts tests`: passed.
- Dependency deprecation warnings from PyMuPDF SWIG types, Starlette/AnyIO and Chroma's Python coroutine inspection are present; they did not fail checks.

## Browser and visual checks

Executed `python -m scripts.verify_browser` against the actual local Uvicorn server with Chromium. Successful answer responses were explicitly mocked; no live LLM call was made.

- Desktop 1440×1000; tablet 768×1024; mobile 390×844 and 320×740: no horizontal document overflow.
- Visually inspected saved desktop, mobile and mocked chat screenshots; corrected capture timing to finish the mobile drawer transition before screenshots.
- Exercised actual missing-key error, Enter/Shift+Enter, disabled duplicate submissions while loading, source expansion, valid citation links with physical-page fragments, untrusted HTML rendered as literal text, exact fallback, network error, appliance changes and New chat.
- Mobile drawer opens/closes on selection, with keyboard support and hidden-navigation focus prevention.
- No browser JavaScript errors in the tested flows.
- Screenshots are local ignored artifacts in `data/screenshots/`, including `desktop.png`, `mobile-390.png`, `mobile-320.png`, `mobile-768.png` and `chat-mocked.png`.

This was Chromium automation plus visual review; Safari, VoiceOver and a formal accessibility audit were not performed.

## Manual answer-support review

[ANSWER_EVALUATION.md](ANSWER_EVALUATION.md) connects each example's proposed content with actual procedures, warnings and diagram limitations. This goes beyond checking whether a page number exists. It is not a review of live model output, since a local LLM key was unavailable.

## Git and remaining external steps

Five milestone commits are saved locally. Every commit was preceded by staged-file review, whitespace checks and a credential-pattern scan. PDFs, extracted text, generated stores/cache, environment files and IDE settings were excluded; the pre-existing exercise was preserved locally.

GitHub profile lookup succeeded for `02ionova`, but no local GitHub token/helper credential or `gh` executable was available. The connected GitHub tool set offered no repository-creation operation. Therefore no private repository URL exists and no push was performed. The exact terminal authentication and private-repository creation commands are in the README.

Live generation and redistribution-authorized sample PDF inclusion remain unverified/unresolved respectively. These are the external steps needed before asserting all university completion criteria are met.

## Readable filename update

Renamed all three local source PDFs to descriptive Bosch appliance/model filenames; contents and recorded hashes are unchanged. Updated manifest, citations, documentation and fixtures; official download URLs retain original manufacturer document numbers. Rebuilt the index with 346 chunks and verified the new metadata. The library displays shorter appliance-manual labels. Browser checks now mock all chat requests, including setup errors, so configured local credentials are never used by browser automation. The 31 fast checks, 3 real-manual integration checks and browser checks were repeated for this update.
