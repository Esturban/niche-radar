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

## Optional provider configuration

`niche-radar` is designed to run without paid services, but some enrichments need environment variables.

- `BING_AUTOSUGGEST_KEY`: enables Bing Autosuggest API
- `YOUTUBE_API_KEY`: enables YouTube Data API
- `YOU_API_KEY`: enables You.com Search for evidence collection and recency metadata
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
- `evidence.json`
- `terms.csv`
- `question_graph.json`
- `trends.csv`
- `provider_hits.json`
- `run_meta.json`

The final shortlist is ranked from strongest evidence to weakest evidence. Each niche includes:

- evidence strength and evidence tier
- profile fit score
- cited snippets and URLs when available
- a suggested wedge
- a validation caveat and next step

It also appends a one-line summary to `runs/index.jsonl`.

## Legacy project

The previous R-based SEM analysis project is preserved under [legacy/sem-analysis-r](/Users/EVA/Desktop/eva/03_development/_dev/repos/2_analysis/r/sem-analysis/legacy/sem-analysis-r).
