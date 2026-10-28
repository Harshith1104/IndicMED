# Medical validation, retrieval comparison and UI upgrade

The existing React/FastAPI application now checks medical intent and retrieval evidence, supports a dedicated strategy comparison, and uses a larger, responsive type scale. No model was rebuilt or retrained and no original evaluation output was regenerated.

## Files changed in this upgrade

Created:

```text
UPGRADE_REPORT.md
backend/services/cache.py
backend/services/validation.py
config/validation_policy.json
frontend/src/components/ComparisonView.jsx
frontend/src/components/ValidationCard.jsx
scripts/calibrate_validation.py
scripts/check_application.py
tests/test_validation.py
validation/cases.json
validation/initial_calibration_report.json
validation/calibration_report.json
validation/application_report.json
validation/probe_report.json
```

Modified:

```text
README.md
backend/main.py
backend/schemas.py
backend/services/pipeline.py
src/pipeline/indicmed_pipeline.py
frontend/package.json
frontend/package-lock.json
frontend/vite.config.js
frontend/playwright.config.js
frontend/src/components/AnswerCard.jsx
frontend/src/components/SearchForm.jsx
frontend/src/hooks/useAsk.js
frontend/src/pages/HomePage.jsx
frontend/src/services/api.js
frontend/src/styles/global.css
frontend/src/test/AnswerCard.test.jsx
frontend/src/test/App.test.jsx
frontend/src/test/api.test.js
frontend/src/test/setup.js
frontend/e2e/application.spec.js
scripts/smoke_api.py
tests/test_api.py
```

Generated dependency/build/test caches and browser screenshots remain ignored under `frontend/node_modules/`, `frontend/dist/`, `frontend/test-results/` and Python cache directories. `MIGRATION_REPORT.md` is the historical report from the earlier migration and was not rewritten. The existing Git history was not changed.

## Medical intent and evidence validation

The API owns one lazy pipeline, validator, translation cache and embedding cache. All inference is protected by the same nonblocking lock. Out-of-scope requests cannot return ordinary medical answer fields.

Intent validation uses three sources of evidence:

1. Explainable medical/non-medical context rules, including Hindi, Telugu and Tamil scripts. A person name is not itself a rejection rule: a question about someone's disease is medical. Clearly unrelated actor, movie, political and sports questions are rejected. Acronyms are interpreted in context; AL amyloidosis, ALS, HIV and COPD remain medical while AL baseball standings, TB storage questions and the ALS recommendation algorithm do not become diseases.
2. Rare terminology extracted from existing MedQuAD FAQ titles, with query n-gram lookup instead of an exhaustive keyword list limited to common conditions.
3. Contrastive medical versus non-medical anchor similarities using the existing multilingual MiniLM model. The final real-model probe “When I get out of bed, everything around me spins.” used this path and was recognized as medical without an explicit disease/symptom keyword. The question was subsequently withheld for weak retrieval evidence. An unseen origami question produced clarification rather than an unrelated medical answer; see `validation/probe_report.json`.

For Indic input, the existing IndicTrans2 translator creates a canonical English query for validation. Direct retrieval still receives the original native-language question. The canonicalization is shared with translate-then-retrieve and cached. If translation or model-based validation cannot be completed, the service abstains explicitly; it never silently approves or rejects the question's medical domain.

The pipeline has one small, opt-in extension: a keyword-only `retrieval_guard` callback after retrieval and before answer selection/translation. Research callers omit it and retain their original behavior. The API guard can withhold the original top result; it never reranks, changes numerical retrieval scores or generates an answer. It checks query topic coverage, requested facets such as symptoms/causes/diagnosis, and query-to-FAQ-title cosine similarity. Lexical/facet checks use the same conservatively shortened English excerpt that will be displayed.

`config/validation_policy.json` records separately fitted policies for 15 method/strategy/language routes, with dataset/model fingerprints. There is no universal raw TF-IDF/BM25/semantic similarity cutoff. The cutoff search jointly considers topic/facet support and uses an explicit conservative error cost: a false topic accept costs three supported-topic withholds. Missing policies, incompatible fingerprints or unsupported evidence result in abstention.

Successful `/api/ask` responses keep their existing fields and add `status`, `retrieved_question`, `retrieval_query` and validation diagnostics. Validly formed requests can return HTTP 200 with `success`, `out_of_scope`, `insufficient_evidence` or `clarification_needed`. Abstentions omit both medical answer fields. HTTP 422 remains the invalid-input response; unavailable resources/concurrent inference use appropriate safe HTTP 503 responses.

## Comparison

`POST /api/compare` accepts only the shared `query`, `language` and `top_k`. Both branches use Semantic, the same English dataset/index, and the same result count. Ask settings are preserved. Both branches run sequentially under one lock, sharing loaded models and bounded caches. English comparison performs one retrieval and reuses its response.

Each card displays its actual query representation, FAQ title, answer and source evidence when approved. A failed/withheld branch remains visible alongside a successful branch. Rejected candidate metadata—question, source URL, raw score and document ID—can be inspected, but rejected answer text is withheld. Answer translation failures retain a clearly labeled grounded English fallback.

The default Translate strategy is highlighted without declaring a live-query winner. Similarity scores are explicitly described as representation-dependent and unrelated to clinical accuracy/confidence. The optional historical Recall@1 table reproduces the recorded values: Hindi 11.5%/39.5%, Telugu 1.5%/38.0%, Tamil 0.5%/32.0% (Direct/Translate). These are evaluation-set metrics, not live-query performance.

## UI changes

| Element | Actual CSS size |
|---|---|
| Main heading | 36px desktop, 32px tablet, 30px mobile |
| Section headings | 22–26px |
| Result/comparison card headings | 21–22px |
| Main body and examples | 16–18px |
| Medical answer and question input | 18px, including mobile |
| Buttons | 16px, minimum 48px height |
| Form labels | 15–16px |
| Supporting text/metadata | 13–14px |

The layout has a 1440px maximum content width, a wider desktop information panel, less decoration, and stacked comparison cards below 900px. The side panel is hidden below 1100px to prioritize questions and answers. Both themes retain navy/teal styling, visible keyboard focus, locally bundled Indic fonts and generous script line heights. Scores are labeled exactly **RETRIEVAL SIMILARITY SCORE** throughout. No numerical score calculation was changed.

## Checks executed and results

| Check | Actual result |
|---|---|
| WSL `python -m pytest tests -q` | **118 passed**, including the original NLP tests, API tests and 52 validation/comparison tests |
| WSL `python -m compileall -q backend src scripts tests` | Passed |
| WSL `npm test` | **40 passed**, three test files; final run 59.78 seconds |
| WSL `npm run build` | Passed; final run 33.64 seconds, JS approximately 257 kB / 80 kB gzip |
| Windows Edge Playwright tests against real WSL FastAPI/Vite | **4 passed** at widths 1366, 1920, 768 and 375; final run 15.5 seconds with warm models |
| `python scripts/check_application.py` against real models/API | **78/78 domain/regression checks and 4/4 language comparisons passed** |
| Updated `python scripts/smoke_api.py` | **9/9 passed**; weak direct Telugu/Tamil results were explicitly withheld |
| Full calibration run | Observations collected for 78 authored cases and all 15 routes using saved embeddings/checkpoints |
| `python scripts/calibrate_validation.py --reuse-observations` | Passed; reused measured cosine scores/translations, refitted/reported rules and refreshed lexical evidence with matching fingerprints |
| Additional actual API probes | Medical paraphrase recognized through contrastive embeddings; unfamiliar non-medical question abstained; neither displayed unrelated answer text |
| `python -m pip check` | No broken requirements |
| npm install audit | 0 vulnerabilities reported |
| `git diff --check` | Passed (normal Windows LF/CRLF notices may print) |
| Existing artifact SHA-256 comparison | **27/27 unchanged** under `outputs/`, `indexes/`, `data/processed/`, `data/test/` |

The final 78 examples comprise 41 medical, 34 out-of-scope and 3 ambiguous questions. Observed false **domain** accepts: **0**; false **domain** rejects: **0**; medical-domain abstentions: **0**. The evidence gate withheld **13 medical answers**. These are separate outcomes: recognizing a medical question does not prove MedQuAD provides a sufficiently supported answer.

The 48 calibration and 30 initially held-out examples were inspected while fixing errors; they are development/regression examples, not an untouched statistical test set. The retained initial report records the earlier TB-storage false domain accept. Do not infer general classifier accuracy or clinical reliability from the final counts. Per-route topic-support false accepts/withholds and the actual query/documents are retained in the reports for inspection.

Real multilingual comparison results were: English and Hindi successful in both paths; Telugu and Tamil successful in Translate with weak Direct answers withheld. The exact requested English/Hindi/Telugu/Tamil pipeline questions were exercised. Models were reused from the existing cache; no embeddings were rebuilt, no new NLP model was downloaded and `transformers==4.51.3` was preserved.

Browser checks covered native Telugu answers, correct request parameters, strategy constraints, partial comparison results, candidate source links, source/document evidence, dark/light persistence, typography (answer/input at least 17px), no horizontal overflow, and no JavaScript page errors. Desktop/mobile light/dark and comparison screenshots were visually inspected. The in-app browser connector failed to initialize, so browser verification used the installed Windows Edge through Playwright.

Development issues fixed included shared Windows/WSL native dependency conflicts, a locked Windows esbuild process, slow cold jsdom worker startup (jsdom 26 is used), and a stale unrestricted Uvicorn reloader scanning the entire mounted repository. The final documented startup command restricts reload directories.

## Start the application

Run in two Ubuntu WSL terminals:

```bash
cd /mnt/f/IndicMed
source .venv-wsl/bin/activate
uvicorn backend.main:app --reload --reload-dir backend --reload-dir src --host 127.0.0.1 --port 8000
```

```bash
export PATH="$HOME/.local/node-v22.23.4/bin:$PATH"
cd /mnt/f/IndicMed/frontend
npm ci --include=optional
npm run dev
```

UI: http://localhost:5173 · API docs: http://localhost:8000/docs

Use npm consistently inside WSL; stop a Windows Vite/esbuild instance using the same checkout before replacing shared dependencies. Test servers were stopped after verification.

## Remaining limitations

- Validation is a conservative heuristic supported by a small authored calibration set, not a trained medical classifier or clinical correctness test. Some routes have very few positive calibration candidates. Expert-reviewed, broader unseen cases are needed before making general performance claims.
- The guard can withhold useful information, including some paraphrased headache questions. The 13 medical withholds are reported rather than counted as successful answers.
- Direct mode sends native text to retrieval, but English canonicalization for application validation still depends on IndicTrans2. A translation outage can therefore cause Direct mode to abstain too.
- Weak direct Telugu/Tamil retrieval remains an underlying model limitation. It is now surfaced instead of displaying unrelated answers. Paracetamol side-effect questions are recognized as medical but withheld when the corpus match is inadequate.
- Cold loading from the mounted Python environment can still take several minutes. Ask/Compare timeouts are five/ten minutes respectively. One inference operation runs at a time; another receives HTTP 503 with retry guidance.
- CPU support remains in the unchanged model modules; a separate forced-CPU multilingual run and tests on physical mobile devices/other browser engines were not performed.
- Existing retrieval evaluation scripts, models, data preparation and saved research results remain intact. No new Recall@K/MRR experiment or medical confidence claim was introduced.
