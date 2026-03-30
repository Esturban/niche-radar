# niche-radar

`niche-radar` is a free-first niche discovery CLI. It does not claim to validate demand. It helps a solo operator or small SMB explore:

- 1 to 5 active niches that match a user's background
- adjacent search terms and recurring question clusters
- public evidence pages and snippets that support each niche
- possible wedges connected to a user's background

The default design goal is `free first`:

- Google Trends is treated as best-effort relative momentum
- Google Suggest and YouTube are discovery sources
- public web evidence is fetched with a free search fallback
- You.com Search is an optional premium evidence backend
- Search Console and Keyword Planner are optional local enrichments, not prerequisites
- if providers are unavailable, the run degrades honestly and explains why

## First run

Create a virtualenv, install the base package, and run one profile through the CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

niche-radar discover \
  --resume /path/to/resume.md \
  --focus "small business operations"
```

The CLI writes a timestamped folder under `runs/`. For a first pass, open `report.md` first and ignore the rest until you need to inspect how the run was assembled.

## Environment file

If you want to use optional providers or local exports, start from the example file:

```bash
cp .env.example .env
```

Fill in only the variables you actually need, then load them into your shell before running the CLI:

```bash
set -a
source .env
set +a
```

`niche-radar` reads environment variables directly. It does not auto-load `.env`, so sourcing the file is the step that makes those values available to the process.

## Recommended setup path

- `base`: `pip install -e .[dev]`
  Best if you just want to see the workflow end to end without configuring any external services.
- `better signal`: `pip install -e .[dev,trends]`
  Adds `pytrends` support for Google Trends collection. This can improve relative momentum data, but it is still best-effort.
- `optional expansion`: `pip install -e .[dev,llm]`
  Adds OpenAI-backed term expansion. This is optional and only matters if you want extra idea generation beyond the default heuristic expansion.

## Usage

Resume-based profile input:

```bash
niche-radar discover \
  --resume /path/to/resume.md \
  --focus "small business operations"
```

Website-based profile input:

```bash
niche-radar discover \
  --site https://example.com \
  --top-niches 5
```

Merged profile input plus optional enrichments:

```bash
niche-radar discover \
  --resume /path/to/resume.pdf \
  --site https://example.com \
  --focus "creator education" \
  --evidence-pages 3 \
  --with-search-console \
  --with-keyword-planner
```

Compatibility notes:

- `--topic` is still accepted as a deprecated alias for `--focus`
- `--max-clusters` is still accepted as a deprecated alias for `--top-niches`
- at least one of `--resume` or `--site` is required

## Optional providers and enrichments

`niche-radar` is designed to run without paid services. Most keys and exports are optional.

Setup times below are rough first-pass estimates. In most cases they assume you already have the underlying account and just need to enable access or point the CLI at an export.

| Provider | What it improves | Required? | Typical setup time | How to get started | Notes |
|---|---|---|---|---|---|
| Google Suggest | baseline related-query discovery | No | `0 min` | no setup in this repo | This is the default fallback when no Bing key is present. |
| YouTube suggest / YouTube Data API | question-like discovery from YouTube | No | `0 min` for suggest fallback, `10-20 min` for API key setup | set `YOUTUBE_API_KEY` for the official API, or let the CLI fall back to YouTube suggest | The API path is more explicit; the suggest fallback is lighter-weight and best-effort. |
| DuckDuckGo HTML / You.com Search | supporting evidence pages and snippets | No | `0 min` for DuckDuckGo fallback, `5-10 min` for You.com key setup | set `YOU_API_KEY` for You.com, or rely on the default DuckDuckGo HTML fallback | You.com is optional premium search. The free fallback remains available. |
| Google Trends via `pytrends` | relative momentum and related trend queries | No | `2-5 min` | `pip install -e .[dev,trends]` | `pytrends` is unofficial and the upstream repo is archived. Treat this as best-effort enrichment, not a guaranteed dependency. |
| Bing Autosuggest API | autosuggest enrichment | No | `10-20 min` | set `BING_AUTOSUGGEST_KEY` | This repo still supports it, but new users should treat it as legacy/best-effort. Google Suggest is the simpler first-run path. |
| Search Console export | first-party query enrichment | No | `5-10 min` if you already have the export, longer if you need property setup | export CSV/JSON data and point `SEARCH_CONSOLE_EXPORT` at the file | This repo does not call the Search Console API directly. It consumes local exports. |
| Keyword Planner export | keyword volume and competition enrichment | No | `10-20 min` if you already use Google Ads | export CSV/JSON data and point `KEYWORD_PLANNER_EXPORT` at the file | This repo does not call the Google Ads API directly. It consumes local exports. |
| OpenAI | optional LLM term expansion | No | `5-10 min` | set `OPENAI_API_KEY` and install `.[dev,llm]` | Useful if you want extra expansion ideas. Not needed for the base workflow. |

Environment variables:

- `BING_AUTOSUGGEST_KEY`
- `YOUTUBE_API_KEY`
- `YOU_API_KEY`
- `SEARCH_CONSOLE_EXPORT`
- `KEYWORD_PLANNER_EXPORT`
- `OPENAI_API_KEY`

You can keep these in `.env` and load them with:

```bash
set -a
source .env
set +a
```

## Suggested docs

- OpenAI quickstart: [developers.openai.com/api/docs/quickstart](https://developers.openai.com/api/docs/quickstart)
- YouTube Data API Python quickstart: [developers.google.com/youtube/v3/quickstart/python](https://developers.google.com/youtube/v3/quickstart/python)
- Search Console API Python quickstart: [developers.google.com/webmaster-tools/v1/quickstart/quickstart-python](https://developers.google.com/webmaster-tools/v1/quickstart/quickstart-python)
- Google Ads keyword planning overview: [developers.google.com/google-ads/api/docs/keyword-planning/overview](https://developers.google.com/google-ads/api/docs/keyword-planning/overview)
- You.com quickstart: [documentation.you.com/quickstart](https://documentation.you.com/quickstart)

Notes on posture:

- Search Console and Keyword Planner are export-based in this repo today. The official API docs are useful background, but the current integration path here is still local CSV/JSON export ingestion.
- Bing Autosuggest documentation now lives in Microsoft's older documentation surface. Keep it in mind only if you already use that API elsewhere.
- `pytrends` remains supported here because it is convenient, but it is not an official Google client.

## Output

Each run writes a folder under `runs/`, and the current runtime always writes the full output bundle.

- `report.md`: start here; this is the primary human-readable result
- `clusters.json`: structured shortlist data for inspection or downstream processing
- `evidence.json`: collected evidence items and citations
- `provider_hits.json`: raw-ish provider output summaries for debugging
- `run_meta.json`: run settings, provider status, and summary metadata
- `terms.csv`: spreadsheet-style view of the discovered term set
- `trends.csv`: spreadsheet-style view of trend metrics
- `question_graph.json`: downstream graph or visualization input

The final shortlist is ranked from strongest evidence to weakest evidence. Each niche includes:

- evidence strength and evidence tier
- profile fit score
- cited snippets and URLs when available
- a suggested wedge
- a validation caveat and next step

It also appends a one-line summary to `runs/index.jsonl`.

## What to ignore on day one

- You do not need every API key.
- You do not need every artifact.
- You only need one profile input and the generated `report.md`.

## Legacy project

The previous R-based SEM analysis project is preserved under [legacy/sem-analysis-r](/Users/EVA/Desktop/eva/03_development/_dev/repos/2_analysis/r/sem-analysis/legacy/sem-analysis-r).
