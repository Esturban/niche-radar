# niche-radar

`niche-radar` is a free-first niche discovery CLI. It does not claim to validate demand. It helps a solo operator or small SMB explore:

- rising keyword territories
- adjacent search terms
- recurring question clusters
- possible wedges connected to a user's background

The default design goal is `free first`:

- Google Trends is treated as best-effort relative momentum
- Bing Autosuggest and YouTube are optional enrichments
- Search Console and Keyword Planner are optional local enrichments, not prerequisites
- if providers are unavailable, the run degrades honestly and explains why

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Optional extras:

```bash
pip install -e .[dev,llm,trends]
```

## Usage

```bash
niche-radar discover \
  --resume /path/to/resume.md \
  --topic "small business operations"
```

Optional enrichments:

```bash
niche-radar discover \
  --resume /path/to/resume.pdf \
  --topic "creator education" \
  --with-search-console \
  --with-keyword-planner
```

## Optional provider configuration

`niche-radar` is designed to run without paid services, but some enrichments need environment variables.

- `BING_AUTOSUGGEST_KEY`: enables Bing Autosuggest API
- `YOUTUBE_API_KEY`: enables YouTube Data API
- `SEARCH_CONSOLE_EXPORT`: path to a JSON/CSV export of query data
- `KEYWORD_PLANNER_EXPORT`: path to a JSON/CSV export of keyword data
- `OPENAI_API_KEY`: optional LLM expansion

Notes:

- Google Trends support is best-effort. If `pytrends` is installed, the CLI will use it behind a provider interface and degrade when it fails.
- Search Console and Keyword Planner integrations are export-based in v1. They are optional enrichments, not the core source of truth.

## Output

Each run writes a folder under `runs/` with:

- `report.md`
- `clusters.json`
- `terms.csv`
- `question_graph.json`
- `trends.csv`
- `provider_hits.json`
- `run_meta.json`

It also appends a one-line summary to `runs/index.jsonl`.

## Legacy project

The previous R-based SEM analysis project is preserved under [legacy/sem-analysis-r](/Users/EVA/Desktop/eva/03_development/_dev/repos/2_analysis/r/sem-analysis/legacy/sem-analysis-r).

