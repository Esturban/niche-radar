from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from pypdf import PdfReader

SITE_PATH_HINTS = ("about", "services", "work", "portfolio", "case-studies", "case-studies/", "case-studies", "case-study")
DEFAULT_SITE_PAGE_BUDGET = 4
REQUEST_TIMEOUT = 10


@dataclass(slots=True)
class ProfileSource:
    text: str
    metadata: dict


def load_profile(resume_path: Path | None = None, site_url: str | None = None, page_budget: int = DEFAULT_SITE_PAGE_BUDGET) -> ProfileSource:
    texts: list[str] = []
    metadata: dict[str, object] = {"sources": []}

    if resume_path:
        resume_text = load_resume(resume_path)
        texts.append(resume_text)
        metadata["resume_path"] = str(resume_path)
        metadata["sources"].append({"kind": "resume", "path": str(resume_path)})

    if site_url:
        site_pages = load_site(site_url, page_budget=page_budget)
        if site_pages:
            texts.extend(page["text"] for page in site_pages if page.get("text"))
            metadata["site_url"] = site_url
            metadata["site_pages"] = [
                {
                    "url": page["url"],
                    "title": page.get("title"),
                    "status_code": page.get("status_code"),
                }
                for page in site_pages
            ]
            metadata["sources"].append({"kind": "site", "url": site_url, "pages": len(site_pages)})

    normalized = normalize_text("\n\n".join(texts))
    if not normalized.strip():
        raise ValueError("Profile sources contained no extractable text.")
    return ProfileSource(text=normalized, metadata=metadata)


def load_resume(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError(f"Unsupported resume format: {suffix}")

    normalized = normalize_text(text)
    if not normalized.strip():
        raise ValueError("Resume/profile contained no extractable text.")
    return normalized


def load_site(site_url: str, page_budget: int = DEFAULT_SITE_PAGE_BUDGET) -> list[dict]:
    normalized_url = _normalize_url(site_url)
    parsed_root = urlparse(normalized_url)
    collected: list[dict] = []
    seen: set[str] = set()
    queue = [normalized_url]

    while queue and len(collected) < page_budget:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        page = fetch_page(current)
        if not page:
            continue
        collected.append(page)

        if len(collected) >= page_budget:
            break

        for link in _candidate_links(page.get("links", []), parsed_root):
            if link not in seen and link not in queue:
                queue.append(link)
            if len(queue) + len(collected) >= page_budget:
                break

    return collected


def normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip())


def _normalize_url(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def fetch_page(url: str) -> dict | None:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception:
        return None

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        return None

    parser = _HTMLTextParser()
    parser.feed(response.text)
    text = normalize_text(parser.text)
    if not text:
        return None
    return {
        "url": response.url,
        "title": parser.title or response.url,
        "text": text,
        "links": parser.links,
        "status_code": response.status_code,
    }


def _candidate_links(links: list[str], parsed_root) -> list[str]:
    output: list[str] = []
    for link in links:
        resolved = urljoin(parsed_root.geturl(), link)
        parsed = urlparse(resolved)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != parsed_root.netloc:
            continue
        lowered = parsed.path.lower().strip("/")
        if not lowered:
            continue
        if any(hint in lowered for hint in SITE_PATH_HINTS):
            output.append(f"{parsed.scheme}://{parsed.netloc}/{lowered}")
    return output


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(part for part in self.text_parts if part).strip()

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._in_title:
            self.title = cleaned
        else:
            self.text_parts.append(cleaned)
