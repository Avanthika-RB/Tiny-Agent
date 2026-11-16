"""Week 5 Day 4: the production retrieval pipeline as the backend of search_known_issues.

Before: search_known_issues matched keywords against data/known_issues.json (KI-001 ... KI-010).
Now (SEARCH_BACKEND=rag, the default): it searches the help ARTICLES (week4/kb) with the Week 5
production config (week5/results/production.json: hybrid search, alpha 0.6, top 5, no reranker)
and returns the top chunks, each with its source file and section.

Each chunk is shaped like a known issue so the rest of graph_v5 works unchanged:
    id          "KB-" + the first 8 characters of the chunk's hash (stable across runs, so the
                Store can remember "this fix failed" for it like it does for KI ids)
    title       the section the chunk is in, e.g. "VPN disconnects every few minutes"
    source      the file, e.g. kb/01-vpn-access-guide.md
    section     the full section path, e.g. "Troubleshooting > VPN disconnects every few minutes"
    applies_to  which OSes: a section under "Windows"/"On Windows" only applies to Windows, one
                under "macOS"/"On macOS" only to macOS, everything else to every OS. This keeps the
                OS check in after_join meaningful.
    fix         the chunk's text
"""

import json
import re
import sys
from pathlib import Path

WEEK5_RAG = Path(__file__).resolve().parents[2] / "week5" / "rag"
TOP_K = 5
WINDOWS = ["Windows 10", "Windows 11"]
MACOS = ["macOS 14", "macOS 15"]

REGISTRY = {}          # KB id -> issue dict, for every chunk returned so far (graph_v5.issue_by_id reads it)
_retrieve = None
CONFIG = None


def production_retriever():
    """Build the Week 5 production pipeline once."""
    global _retrieve, CONFIG
    if _retrieve is None:
        sys.path.insert(0, str(WEEK5_RAG))
        import common
        from retrievers.pipeline import make_pipeline
        CONFIG = json.loads((common.RESULTS / "production.json").read_text(encoding="utf-8"))
        _retrieve = make_pipeline(**CONFIG)
    return _retrieve


def applies_to(section):
    parts = [p.strip().lower() for p in section.split(">")]
    windows = any(p in ("windows", "on windows") for p in parts)
    mac = any(p in ("macos", "on macos") for p in parts)
    if windows and not mac:
        return WINDOWS
    if mac and not windows:
        return MACOS
    return WINDOWS + MACOS


def as_issue(chunk):
    meta = chunk["metadata"]
    header_path = meta.get("header_path") or ""
    parts = [p.strip() for p in header_path.split(">")] if header_path else []
    section = " > ".join(parts[1:]) if len(parts) > 1 else ""      # without the article title
    text = chunk["text"]
    if header_path and text.startswith(header_path):              # markdown_headers puts the path on line 1
        text = text[len(header_path):].strip()
    title = parts[-1] if len(parts) > 1 else " ".join(text.split())[:60]
    return {
        "id": "KB-" + chunk["id"][:8],
        "title": title,
        "source": meta["source"],
        "section": section,
        "applies_to": applies_to(section),
        "fix": text,
    }


def search(query, k=TOP_K):
    """The top k chunks for a problem description, as issue dicts."""
    issues = [as_issue(c) for c in production_retriever()(query, k)]
    for issue in issues:
        REGISTRY[issue["id"]] = issue
    return issues


def search_text(query):
    """What the search_known_issues tool returns: one line per chunk, with source and section."""
    issues = search(query)
    if not issues:
        return "No help article sections match that description."
    return "\n".join(
        f"{i['id']}: {i['title']} (applies to: {', '.join(i['applies_to'])}; source: {i['source']}; "
        f"section: {i['section'] or 'none'}). Fix: {' '.join(i['fix'].split())}"
        for i in issues
    )


LINE = re.compile(r"^(KB-\w+): (.*?) \(applies to: .*?; source: (.*?); section: (.*?)\)\. Fix: (.*)$", re.M)


def parse(text):
    """The search result lines back into {id, title, source, section, text} (for the evaluation)."""
    return [{"id": m.group(1), "title": m.group(2), "source": m.group(3), "section": m.group(4), "text": m.group(5)}
            for m in LINE.finditer(text)]
