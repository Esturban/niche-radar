This directory preserves the pre-Python `sem-analysis` project as a legacy snapshot.

The active runtime now lives in `src/niche_radar/` and is surfaced through the `niche-radar` CLI.

Why the snapshot exists:

- the original repo was R-based and Google-Trends-oriented
- the current worktree already contained local R changes and untracked files
- keeping a copy here preserves the old analysis logic while making the root repo Python-first

Nothing in this folder is part of the active runtime.
