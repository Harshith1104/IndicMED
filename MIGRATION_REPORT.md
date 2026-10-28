# React + FastAPI migration report

IndicMed now uses a React/Vite frontend and a FastAPI wrapper around the original `IndicMedPipeline.ask()`. It supports English, Hindi, Telugu and Tamil; TF-IDF, BM25 and semantic retrieval; and both multilingual strategies within the semantic-only direct retrieval constraint. The original Streamlit UI remains available.

## Exact source file inventory

Modified existing files:

```text
.gitignore
README.md
requirements.txt
```

Created files:

```text
MIGRATION_REPORT.md
backend/__init__.py
backend/main.py
backend/schemas.py
backend/services/__init__.py
backend/services/pipeline.py
frontend/.env.example
frontend/e2e/application.spec.js
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/playwright.config.js
frontend/public/favicon.svg
frontend/src/App.jsx
frontend/src/components/AnswerCard.jsx
frontend/src/components/Header.jsx
frontend/src/components/InformationPanel.jsx
frontend/src/components/Notice.jsx
frontend/src/components/RetrievalSettings.jsx
frontend/src/components/SearchForm.jsx
frontend/src/hooks/useAsk.js
frontend/src/hooks/useTheme.js
frontend/src/main.jsx
frontend/src/pages/HomePage.jsx
frontend/src/services/api.js
frontend/src/styles/global.css
frontend/src/test/AnswerCard.test.jsx
frontend/src/test/App.test.jsx
frontend/src/test/api.test.js
frontend/src/test/fixtures.js
frontend/src/test/setup.js
frontend/vite.config.js
scripts/smoke_api.py
tests/test_api.py
```

Generated, ignored local artifacts include `frontend/node_modules/`, `frontend/dist/`, `frontend/test-results/`, Python bytecode and test caches. They are not source changes or research results. There were no commits, pushes, history rewrites or deployments.

## NLP reuse and research preservation

Every existing file under `src/` is unchanged. The reused components include:

- `src/pipeline/indicmed_pipeline.py`: normalization, language routing, lazy retrievers, query translation, retrieval, answer selection/shortening, answer translation and fallback.
- `src/translation/indictrans.py` and `languages.py`: checkpoint selection, language codes, cached translation models, CUDA selection and CPU support.
- `src/retrieval/`: TF-IDF, Okapi BM25, multilingual MiniLM and normalized NumPy cosine search.
- `src/qa/`: answer selection, conservative shortening and the existing response structure.
- `src/preprocessing/`: Unicode normalization, text cleaning, language detection and the existing transliteration extension point.
- `src/utils/helpers.py`: project-relative path resolution and YAML configuration loading.

`app.py`, `config/config.yaml`, existing tests, dataset/index preparation scripts and evaluation modules/scripts are unchanged. `transformers==4.51.3` and the existing translation dependency pins remain intact. No embeddings, datasets or evaluation results were regenerated. SHA-256 comparisons confirmed all 27 existing files under `outputs/`, `indexes/`, `data/processed/` and `data/test/` were byte-for-byte unchanged after testing. The documented 1,000-query English benchmark and 200-underlying-question multilingual benchmark are preserved; this migration makes no new benchmark claims.

## Checks actually executed

| Check | Result |
|---|---|
| WSL `python -m pytest tests -q` | **66 passed**, including the 23 original tests and 43 API tests; final run 14.11 seconds |
| WSL `python -m compileall -q backend app.py src scripts tests` | Passed |
| WSL `npm test` | **35 passed** across three files; final run 73.30 seconds, with no unhandled worker errors |
| WSL `npm run build` | Passed; final application build 40.74 seconds; JS bundle approximately 245 kB / 77 kB gzip |
| Windows Edge Playwright runner against WSL FastAPI/Vite | **3 passed**: desktop 1280px, tablet 820px, mobile 390px; final run about 3.4 minutes including a cold model load |
| WSL `python scripts/smoke_api.py` against the real API | **9/9 passed**, using real data, saved semantic embeddings and cached model checkpoints |
| WSL `python -m pip check` | No broken requirements |
| npm dependency installation audit | 0 vulnerabilities reported |
| `git diff --check` | Passed; Git may print normal LF/CRLF conversion notices on Windows |
| Research artifact SHA-256 comparison | 27/27 unchanged |

API tests cover lightweight health/options, request validation, all supported languages, auto detection/manual overrides, method/strategy routing, English translation bypass, query translation errors, English answer fallback, sanitized failures, initialization retry, resource reuse, concurrent inference rejection and restricted CORS. Frontend tests cover exact API values, incompatible controls, examples, answers/evidence, safe URLs/inert HTML text, stale request suppression, duplicate prevention, loading/error/empty states, translation warnings, timeout/cancellation and theme persistence.

Browser tests use the actual Telugu question and API response, verify source/document evidence and target-language script, exercise retrieval constraints and persisted themes, and check for horizontal overflow and JavaScript errors. Light/dark desktop and mobile screenshots were visually inspected. Screenshots for all three sizes remain under ignored `frontend/test-results/`.

The in-app browser connector could not initialize because of a tool metadata error. Browser QA therefore used the installed Windows Microsoft Edge through Playwright while both application servers ran inside WSL. Initial npm 10 dependency resolution and Vitest worker-start failures were fixed; the final checks above passed. Vitest reuses a single jsdom worker, with explicit transport mock cleanup, to avoid repeated cold startup deadlines on the Windows-mounted filesystem.

## Real-model multilingual integration

The smoke test used these exact questions:

| Language | Question |
|---|---|
| English | What is asthma? |
| Hindi | मधुमेह के लक्षण क्या हैं? |
| Telugu | మైగ్రేన్‌కు కారణాలు ఏమిటి? |
| Tamil | காசநோய் எவ்வாறு கண்டறியப்படுகிறது? |

All four succeeded with semantic translate-then-retrieve, retaining grounded English answers, document IDs and scores. The three Indic languages also succeeded with direct semantic retrieval, and English succeeded with TF-IDF and BM25. Translated answers contained the expected scripts with no translation fallback warnings. Tests ran with Hugging Face offline mode enabled, using the pre-existing caches. The script prints observations and never writes to the research output folders.

These are functional integration checks, not clinical validation. Direct Telugu/Tamil retrieval returned unrelated FAQs in these examples, consistent with the project's documented limitations. Translate-then-retrieve remains the default. The first semantic request in the initial cold run took about 245 seconds; later requests reused resources. Translation/model loading and machine load affect latency.

## Start the servers

Open two Ubuntu WSL terminals (`wsl -d Ubuntu-22.04` from PowerShell on this machine).

Backend:

```bash
cd /mnt/f/IndicMed
source .venv-wsl/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
export PATH="$HOME/.local/node-v22.23.4/bin:$PATH"
cd /mnt/f/IndicMed/frontend
npm ci
npm run dev
```

The PATH line selects the Linux Node installation added during this migration. It is unnecessary if a compatible Linux Node is already on PATH. The repository requires Node 22.12+; Node 22.23.4 and npm 11 were used here. `npm ci` is needed initially or after lockfile changes. Added Python API packages were installed into the existing `.venv-wsl`, which was not replaced. See the README for fresh-install commands.

- UI: http://localhost:5173
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs

## Remaining limits

- First-request loading can take several minutes, especially with the Python environment on a Windows-mounted drive. The browser allows five minutes; timeouts are surfaced and never replaced with a fabricated answer.
- One Python process serves one inference at a time to protect shared models; another inference receives HTTP 503 with retry guidance. Browser cancellation cannot interrupt model inference already running. Use one Uvicorn worker to avoid duplicating model memory.
- Existing retrieval/translation limitations remain, including weak direct cross-lingual matching, imperfect language detection, potential translation omissions and conservative answer truncation. No medical accuracy claim is inferred from a similarity score.
- CPU fallback remains supported through the unchanged NLP modules; a separate forced-CPU full multilingual run was not performed.
- Browser testing used Edge's desktop/tablet/mobile emulation. Physical devices and other browser engines were not tested.
- This is a local application migration. A later deployment must serve the built frontend and route `/api` to Python, or set the public API base URL and a matching CORS origin. No hosting configuration or external service was introduced.

The test servers were shut down after validation. The commands above start fresh development sessions.
