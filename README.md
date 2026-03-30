# niche-radar

`niche-radar` is a free-first niche discovery CLI for narrowing broad experience into a small set of evidence-backed niche bets.

It helps a solo operator or small SMB answer questions like:

- What niche directions fit my background?
- What adjacent search terms keep appearing around that niche?
- What questions, tutorials, and problem statements already exist in public?
- What is narrow enough to test next, instead of staying at a vague market level?

It does not validate demand, willingness to pay, or competition directly. It gives you a faster way to collect early directional evidence before you talk to users.

## What this tool does for you

Think of the pipeline as a staged assistant:

1. It reads your resume, website, or both to infer what you know.
2. It creates seed niche terms from that profile.
3. It expands those terms using heuristics and optionally OpenAI.
4. It queries search-adjacent surfaces like Google Suggest, YouTube, and optionally Trends/Bing.
5. It gathers supporting evidence pages from the public web.
6. It ranks clusters by evidence strength, specificity, and profile fit.
7. It writes a human-readable report plus supporting artifacts.

Recommendation contract:

- A niche is only recommended when it clears both the focus gate and the evidence gate.
- Focus gate: the ranked cluster must retain the requested niche tokens.
- Evidence gate: the ranked cluster must have cross-source support, including search-adjacent signal plus strong public evidence pages.
- If no cluster clears both gates, the run still completes, but the report explicitly says no data-backed hyperniche passed.

In practice, each provider has a specific job:

- Google Suggest: cheap baseline query expansion when you have no keys
- YouTube / YouTube suggest: surfaces tutorial-style and question-like demand
- Google Trends via `pytrends`: gives relative momentum and related trend queries
- You.com / DuckDuckGo fallback: pulls supporting evidence pages and snippets
- Search Console export: injects first-party queries from your own site
- Keyword Planner export: adds search volume / competition style context from exported keyword data
- OpenAI: proposes more adjacent phrase candidates than heuristics alone

## Fastest first run

If you want to see the tool work before connecting anything else:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

niche-radar discover \
  --resume /path/to/resume.md \
  --focus "small business operations"
```

This gets you a usable run with no API keys at all. The CLI writes a timestamped folder under `runs/`. Open `report.md` first.

Estimated time:

- if Python is already installed: `5-10 min`
- if you need to install Python first: `15-30 min`

## Environment file

If you want optional providers or local exports, start from the example file:

```bash
cp .env.example .env
```

Fill in only the variables you actually plan to use, then load them into your shell before running the CLI:

```bash
set -a
source .env
set +a
```

`niche-radar` reads environment variables directly. It does not auto-load `.env`, so sourcing the file is what makes the values visible to the process.

## Recommended setup path

- `base`: `pip install -e .[dev]`
  Best if you want the tool working quickly with the built-in free fallbacks.
- `better signal`: `pip install -e .[dev,trends]`
  Adds `pytrends` support for Google Trends collection. Useful if you want momentum data, but still best-effort.
- `optional expansion`: `pip install -e .[dev,llm]`
  Adds OpenAI-backed term expansion. The default OpenAI runtime uses `gpt-5.4-nano` with `xhigh` reasoning for broader adjacent ideas.

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

Compare two previous runs:

```bash
niche-radar compare-runs \
  --left runs/2026-03-30T044739+0000-small-business-operations \
  --right runs/2026-03-30T045151+0000-shopify-ecommerce
```

This prints the top-cluster delta plus focus/evidence gate deltas so you can verify that a changed focus materially changed the output.

## Provider setup guide

The table below is the practical setup guide for this repo, not a generic API catalog.

Time estimates are intentionally rough:

- `already have access`: you already have the relevant account/property/project and just need to generate a key or export a file
- `starting from scratch`: assume you do not already have the account, project, property, or console familiarity

| Integration | What it does in `niche-radar` | Do you need it? | Time if you already have access | Time starting from scratch | Setup / token / export links | Repo-specific notes |
|---|---|---:|---:|---:|---|---|
| Google Suggest | Baseline autosuggest terms. Helps the tool find adjacent searches even with no keys. | No | `0 min` | `0 min` | No setup required. | This is the easiest first-run source and the current fallback when `BING_AUTOSUGGEST_KEY` is not set. |
| YouTube suggest | Baseline YouTube query suggestions. Helps surface “how to” and tutorial-like demand. | No | `0 min` | `0 min` | No setup required. | This is the current fallback when `YOUTUBE_API_KEY` is not set. |
| YouTube Data API | Pulls actual YouTube search results instead of suggest-only hints. Better for question-like discovery and example titles. | No | `10-20 min` | `20-45 min` | Quickstart: [developers.google.com/youtube/v3/quickstart/python](https://developers.google.com/youtube/v3/quickstart/python). Credentials page: [console.developers.google.com/apis/credentials](https://console.developers.google.com/apis/credentials). API library: [console.developers.google.com/apis/library](https://console.developers.google.com/apis/library). | For this repo you only need an API key and then `YOUTUBE_API_KEY` in `.env`. You do not need OAuth unless you are building your own YouTube app. |
| DuckDuckGo HTML fallback | Finds public evidence pages and snippets with zero setup. | No | `0 min` | `0 min` | No setup required. | This is the default evidence backend when `YOU_API_KEY` is not set. |
| You.com Search | Improves evidence collection with structured web/news results and recency metadata. | No | `5-10 min` | `10-20 min` | Quickstart: [documentation.you.com/quickstart](https://documentation.you.com/quickstart). Platform/API keys: [you.com/platform](https://you.com/platform). Admin keys page: [documentation.you.com/administration/api-keys](https://documentation.you.com/administration/api-keys). | For this repo you only need `YOU_API_KEY`. This is optional, but it is one of the more useful upgrades if you want better evidence quality. |
| Google Trends via `pytrends` | Adds relative momentum and related trend queries. | No | `2-5 min` | `2-5 min` | Install extra: `pip install -e .[dev,trends]`. Upstream repo: [github.com/GeneralMills/pytrends](https://github.com/GeneralMills/pytrends). | `pytrends` is unofficial and the upstream repo is archived. Keep it as best-effort enrichment, not a guaranteed or stable dependency. |
| Bing Autosuggest API | Replaces Google Suggest fallback with Bing Autosuggest results. | No | `10-20 min` | `25-45 min` | Overview: [learn.microsoft.com/en-us/previous-versions/bing/search-apis/bing-autosuggest/overview](https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/bing-autosuggest/overview). Python quickstart: [learn.microsoft.com/en-us/previous-versions/bing/search-apis/bing-autosuggest/quickstarts/rest/python](https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/bing-autosuggest/quickstarts/rest/python). Pricing/subscription entry: [aka.ms/bingsearchapipricing](https://aka.ms/bingsearchapipricing). | Microsoft marks this content as retired / no longer supported. Treat it as legacy only. New users should usually skip this and use the Google Suggest fallback. |
| Search Console export | Injects first-party search queries from your own verified site. This is useful when you already have a site with real traffic. | No | `5-15 min` | `30-90+ min` | Search Console: [search.google.com/search-console](https://search.google.com/search-console). Property verification help: [support.google.com/webmasters/answer/9008080](https://support.google.com/webmasters/answer/9008080). API quickstart background: [developers.google.com/webmaster-tools/v1/quickstart/quickstart-python](https://developers.google.com/webmaster-tools/v1/quickstart/quickstart-python). | This repo does not use the Search Console API directly. It expects a local CSV/JSON export path in `SEARCH_CONSOLE_EXPORT`. If you do not already have a verified property with useful data, skip this at first. |
| Keyword Planner export | Adds exported keyword volume / competition style data to the term set. Useful when you already work inside Google Ads. | No | `10-20 min` | `45-120+ min` | Keyword Planning overview: [developers.google.com/google-ads/api/docs/keyword-planning/overview](https://developers.google.com/google-ads/api/docs/keyword-planning/overview). Keyword Planner help: [support.google.com/google-ads/answer/7337243](https://support.google.com/google-ads/answer/7337243). Google Ads home: [ads.google.com](https://ads.google.com). | This repo does not call the Google Ads API directly. It expects a local CSV/JSON export path in `KEYWORD_PLANNER_EXPORT`. If you do not already use Google Ads, this is usually not worth the setup for a first run. |
| OpenAI | Generates additional adjacent niche phrases beyond the heuristic expansion rules. | No | `5-10 min` | `10-20 min` | Quickstart: [developers.openai.com/api/docs/quickstart](https://developers.openai.com/api/docs/quickstart). Create key: [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Billing: [platform.openai.com/account/billing/overview](https://platform.openai.com/account/billing/overview). | For this repo you only need `OPENAI_API_KEY` and `pip install -e .[dev,llm]`. The default OpenAI runtime is `gpt-5.4-nano` with `xhigh` reasoning, and you can override that with `NICHE_RADAR_OPENAI_MODEL` or `NICHE_RADAR_OPENAI_REASONING`. |

### What each integration actually buys you

- If you want the fastest setup with acceptable output:
  use only the base install and the built-in fallbacks.
- If you want better evidence quality:
  add You.com.
- If you want momentum data:
  add `pytrends`, while accepting that it is unofficial.
- If you already have site traffic:
  add Search Console export.
- If you already use Google Ads:
  add Keyword Planner export.
- If you want broader idea generation:
  add OpenAI.
- If you are new and choosing where to spend setup time:
  skip Bing first.

## Suggested `.env` values

The repo reads these variables directly:

- `BING_AUTOSUGGEST_KEY`
- `YOUTUBE_API_KEY`
- `YOU_API_KEY`
- `SEARCH_CONSOLE_EXPORT`
- `KEYWORD_PLANNER_EXPORT`
- `OPENAI_API_KEY`
- `NICHE_RADAR_OPENAI_MODEL`
- `NICHE_RADAR_OPENAI_REASONING`

Minimal practical `.env` examples:

```bash
# Fastest useful upgrade path
YOU_API_KEY=...
YOUTUBE_API_KEY=...
OPENAI_API_KEY=...
NICHE_RADAR_OPENAI_MODEL=gpt-5.4-nano
NICHE_RADAR_OPENAI_REASONING=xhigh
```

```bash
# If you already have first-party Google data
SEARCH_CONSOLE_EXPORT=/absolute/path/to/search-console-export.csv
KEYWORD_PLANNER_EXPORT=/absolute/path/to/keyword-planner-export.csv
```

Load them with:

```bash
set -a
source .env
set +a
```

OpenAI runtime defaults:

- model: `gpt-5.4-nano`
- reasoning effort: `xhigh`
- to lower cost or latency later, set `NICHE_RADAR_OPENAI_REASONING=high`

## Suggested setup order

If you are starting from zero, this is the order that gives the best return on time:

1. Get the base CLI running with no keys.
2. Add `YOU_API_KEY` if you want better evidence collection.
3. Add `YOUTUBE_API_KEY` if you want stronger tutorial / question discovery.
4. Add `OPENAI_API_KEY` if you want broader adjacent term generation.
5. Add `pytrends` only if you care about trend/momentum data enough to tolerate unofficial tooling.
6. Add Search Console or Keyword Planner only if you already have those ecosystems in place.
7. Skip Bing unless you already have a reason to use it.

## Total setup time

These are practical end-to-end estimates for this repo:

- bare minimum working run: `5-10 min`
  Base install, no external accounts, no keys.
- strong “most features that are worth it” setup for a new user: `25-60 min`
  Base install + You.com + YouTube Data API + OpenAI + optional `.env` setup.
- full optional setup if you do not already have Google properties / Google Ads in place: `90-240+ min`
  Base install + You.com + YouTube + OpenAI + `pytrends` + Search Console property setup/export + Google Ads / Keyword Planner setup/export.

If your goal is simply “get this running well,” the highest-value setup is usually:

- base install
- `YOU_API_KEY`
- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`

That gets you most of the practical benefit without spending hours in Google product consoles.

## Output

Each run writes a folder under `runs/`, and the current runtime always writes the full output bundle.

- `report.md`: start here; this is the primary human-readable result
- `clusters.json`: structured shortlist data for inspection or downstream processing
- `evidence.json`: collected evidence items and citations
- `provider_hits.json`: provider output summaries for debugging
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
- You do not need Bing, Search Console, or Keyword Planner to get a useful run.
- You only need one profile input and the generated `report.md`.

## Legacy project

The previous R-based SEM analysis project is preserved under [legacy/sem-analysis-r](/Users/EVA/Desktop/eva/03_development/_dev/repos/2_analysis/r/sem-analysis/legacy/sem-analysis-r).
