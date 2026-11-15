"""THE matching function: when does a retrieved chunk count as a hit for a gold section?
Written once, used by every technique all week.

A gold entry is (article, section), e.g. ("01", "Policy"). A chunk matches it when the chunk
comes from that article AND:

  1. Header rule (markdown_headers, markdown_headers_noprefix): the section's name appears in the
     chunk's header_path, e.g. "VPN Access Guide > Troubleshooting > VPN disconnects every few
     minutes" matches both "VPN disconnects every few minutes" and its parent "Troubleshooting".
  2. Overlap rule (every other chunk, and header chunks with no header_path, like the PDF's):
     the chunk text and the section text share at least 50 characters in a row (case and
     whitespace ignored). A section's text runs from its heading to the next heading of the same
     or higher level, so a parent section includes its subsections, as in rule 1.

The article comes from the file name: kb/01-vpn-access-guide.md and kb_other_formats/03-...pdf
are articles "01" and "03". The HTML, TXT and PDF copies count as the same article.

Each retrieved chunk gets ONE label for the metrics: the highest-grade gold section it matches
that no earlier chunk has claimed (or a section already claimed, which the metrics then ignore
as a duplicate), or None if it matches nothing.
"""

from difflib import SequenceMatcher
from pathlib import Path

import common

MIN_OVERLAP = 50
_sections = None


def squash(text):
    return " ".join(text.lower().split())


def article_of(source):
    return Path(source).name[:2]


def section_texts():
    """{"01/Overview": cleaned text of that section, ...} from the markdown articles in week4/kb,
    cleaned with the same clean_text as the chunks."""
    global _sections
    if _sections is not None:
        return _sections
    _sections = {}
    for path in sorted((common.REPO / "week4" / "kb").glob("*.md")):
        lines = common.ingest.clean_text(path.read_text(encoding="utf-8")).splitlines()
        headings = [(n, len(line) - len(line.lstrip("#")), line.lstrip("#").strip())
                    for n, line in enumerate(lines) if line.startswith("#")]
        for i, (start, level, title) in enumerate(headings):
            end = next((n for n, lvl, _ in headings[i + 1:] if lvl <= level), len(lines))
            _sections[f"{path.name[:2]}/{title}"] = squash("\n".join(lines[start:end]))
    return _sections


def matches(chunk, key):
    """True if this chunk counts as a hit for the gold section `key` ("01/Policy")."""
    article, section = key.split("/", 1)
    meta = chunk["metadata"]
    if article_of(meta["source"]) != article:
        return False
    header_path = meta.get("header_path") or ""
    if header_path:
        return section in [part.strip() for part in header_path.split(">")[1:]]   # [1:] skips the article title
    gold_text = section_texts().get(key)
    if gold_text is None:
        raise KeyError(f"No section {key} in week4/kb. Check the spelling in eval_set.jsonl.")
    text = squash(chunk["text"])
    m = SequenceMatcher(None, text, gold_text, autojunk=False).find_longest_match(0, len(text), 0, len(gold_text))
    return m.size >= MIN_OVERLAP


def label(chunks, gold):
    """One label per retrieved chunk, in rank order (see the module docstring)."""
    claimed = set()
    labels = []
    for chunk in chunks:
        hits = sorted((k for k in gold if matches(chunk, k)), key=lambda k: -gold[k])
        new = [k for k in hits if k not in claimed]
        choice = new[0] if new else (hits[0] if hits else None)
        if choice:
            claimed.add(choice)
        labels.append(choice)
    return labels


def check_gold():
    """Every gold section in the eval set must exist in the articles."""
    missing = [(q["qid"], k) for q in common.load_eval_set() for k in common.gold_of(q) if k not in section_texts()]
    for qid, key in missing:
        print(f"  q{qid}: no section {key} in week4/kb")
    return not missing
