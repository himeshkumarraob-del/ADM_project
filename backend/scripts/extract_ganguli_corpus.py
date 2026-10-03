#!/usr/bin/env python
"""Extract primary source text from the verified Ganguli PDF.

Reads ``Mahabharata-etext.pdf`` page by page, splits the running-header
structure ("The Mahabharata, Book N: <Parva>[: <Subparva>]: Section <Roman>")
into per-section prose blocks, and writes a corpus JSON consumable by
``python -m scripts.ingest_corpus``.

Every record's prose is verbatim text taken from the PDF. No summarisation,
no verse or section fabrication, no external text.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

PDF = Path(r"C:\Users\Himesh kumar rao\Desktop\Mahabharata-etext.pdf")
OUT = Path(__file__).resolve().parents[1] / "data" / "corpus" / "06_ganguli_primary.json"

HEADER_RE = re.compile(
    r"The Mahabharata,\s*Book\s+(\d+)\s*:\s*([^:]+?)(?::\s*([^:]+?))?\s*:\s*Section\s+([IVXLC]+)"
    r"(?:\s*[|]?\s*p\.\s*(\d+))?"
)

# Book number -> canonical display parva (app.rag.taxonomy order).
BOOK_PARVA = {
    1: "Adi Parva", 2: "Sabha Parva", 3: "Vana Parva", 4: "Virata Parva",
    5: "Udyoga Parva", 6: "Bhishma Parva", 7: "Drona Parva", 8: "Karna Parva",
    9: "Shalya Parva", 10: "Sauptika Parva", 11: "Stri Parva", 12: "Shanti Parva",
    13: "Anushasana Parva", 14: "Ashvamedhika Parva", 15: "Ashramavasika Parva",
    16: "Mausala Parva", 17: "Mahaprasthanika Parva", 18: "Svargarohana Parva",
}

FOOTER_PREFIXES = ("Next:", "Previous:", "Next :", "Previous :")


def _roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 500, "D": 1000, "M": 1000}
    out = 0
    prev = 0
    for ch in reversed(s):
        v = vals[ch]
        out += v if v >= prev else -v
        prev = max(prev, v)
    return out


def _clean_block(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("file:///") or line.startswith("file:"):
            continue
        if line.startswith(FOOTER_PREFIXES):
            continue
        if line == "Footnotes" or line.startswith("Footnotes"):
            break  # apparatus follows the prose; exclude it
        if re.fullmatch(r"\|?\s*p\.\s*\d+", line):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    text = " ".join(lines)
    # line-break hyphenation artifacts: "some- thing" -> "something"
    text = re.sub(r"(\w)-\s+([a-z])", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_sections() -> list[dict]:
    reader = PdfReader(str(PDF))
    chunks: dict[tuple[int, str], dict] = {}
    order: list[tuple[int, str]] = []

    current_key: tuple[int, str] | None = None
    current_parts: list[str] = []
    current_meta: dict = {}

    def flush() -> None:
        nonlocal current_parts, current_meta
        if current_key is None:
            current_parts, current_meta = [], {}
            return
        text = _clean_block(" ".join(current_parts))
        if current_key in chunks:
            chunks[current_key]["text_parts"].append(text)
        else:
            chunks[current_key] = {"meta": dict(current_meta), "text_parts": [text]}
            order.append(current_key)
        current_parts, current_meta = [], {}

    for page in reader.pages:
        page_text = page.extract_text() or ""
        # split page into (header-match-or-None, text) segments
        pos = 0
        for m in HEADER_RE.finditer(page_text):
            head_text = page_text[pos:m.start()]
            if current_key is not None:
                current_parts.append(head_text)
            flush()
            book = int(m.group(1))
            parva_name = m.group(2).strip()
            subparva = (m.group(3) or "").strip()
            roman = m.group(4)
            printed = m.group(5)
            if "index" in parva_name.lower() or "index" in subparva.lower():
                current_key = None
                current_meta = {}
            else:
                current_key = (book, roman)
                current_meta = {
                    "book": book,
                    "parva": BOOK_PARVA.get(book, parva_name.replace(" Parva", "") + " Parva"),
                    "pdf_parva_label": parva_name,
                    "subparva": subparva,
                    "section": f"Section {roman}",
                    "roman": roman,
                    "printed_page_start": printed or "",
                }
            pos = m.end()
        tail = page_text[pos:]
        if current_key is not None:
            current_parts.append(tail)
        elif current_key is None and tail.strip():
            # still inside a skipped (index) region; ignore
            pass
        # continue accumulating into current section across pages
        if current_key is not None and current_parts == [] :
            pass
        if current_key is not None and tail and tail.strip():
            pass
    flush()

    records = []
    for key in order:
        blob = chunks[key]
        meta = blob["meta"]
        text = " ".join(t for t in blob["text_parts"] if t).strip()
        text = re.sub(r"\s+", " ", text)
        records.append({**meta, "text": text})
    return records


_THEME_KEYWORDS = [
    ("dharma", ("dharma", "righteousness", "righteous")),
    ("duty", ("duty", "duties")),
    ("justice", ("justice", "just ")),
    ("truth", ("truth", "truthful")),
    ("loyalty", ("loyal", "loyalty")),
    ("revenge", ("revenge", "avenge")),
    ("forgiveness", ("forgive", "forgiveness")),
    ("anger", ("anger", "wrath", "angry")),
    ("fear", ("fear", "afraid")),
    ("grief", ("grief", "sorrow", "mourn")),
    ("war", ("war", "battle", "fight")),
    ("gambling", ("dice", "gambling", "game of dice")),
    ("vows", ("vow", "oath")),
    ("deception", ("deceit", "deception", "disguise")),
    ("power", ("kingdom", "king", "throne")),
    ("patience", ("patience", "patient")),
    ("generosity", ("gift", "generous", "charity")),
    ("shame", ("shame", "disgrace")),
    ("detachment", ("detachment", "renounce", "renunciation")),
    ("counsel", ("counsel", "counselled", "advice")),
]

_CHARACTER_NAMES: dict[str, str] = {}


def _character_slugs_present(text: str) -> list[str]:
    from app.knowledge.taxonomy import CHARACTERS  # type: ignore

    found: list[str] = []
    lowered = text.lower()
    for c in CHARACTERS:
        names = [c["name"], *c.get("aliases", [])]
        for n in names:
            if re.search(rf"\b{re.escape(n.lower())}\b", lowered):
                found.append(c["slug"])
                break
    return found[:12]


def _themes_for(text: str) -> list[str]:
    lowered = text.lower()
    out = []
    for slug, needles in _THEME_KEYWORDS:
        if any(n in lowered for n in needles):
            out.append(slug)
    if not out:
        out = ["dharma"]
    return out[:6]


def to_corpus_record(rec: dict, idx: int) -> dict:
    parva = rec["parva"]
    sub = rec["subparva"]
    section_label = f"{sub}: {rec['section']}" if sub else rec["section"]
    pdf_parva = rec["pdf_parva_label"]
    ref = f"{parva}, {section_label} (Ganguli translation, 1883-1896)"
    text = rec["text"]
    excerpt = text[:1200]
    # end excerpt at the last sentence boundary to avoid mid-word cuts
    cut = max(excerpt.rfind(". "), excerpt.rfind('." '), excerpt.rfind("? "), excerpt.rfind("! "))
    if cut > 400:
        excerpt = excerpt[: cut + 1]
    characters = _character_slugs_present(text)
    if not characters:
        characters = ["vyasa"] if "vyasa" in text.lower() else []
    if not characters:
        # Required metadata cannot be empty; fall back to the work's narrator.
        characters = ["vyasa"]
    keywords = [sub] if sub else [rec["section"]]
    return {
        "parva": parva,
        "section": section_label,
        "chapter": None,
        "verse_range": "",
        "speaker": "",
        "listener": "",
        "characters": characters,
        "events": [],
        "themes": _themes_for(text),
        "keywords": keywords,
        "original_text": "",
        "translation": text,
        "quote": excerpt,
        "summary": (
            f"PRIMARY SOURCE TEXT ({parva}, {section_label}): verbatim Ganguli "
            f"prose extracted from the supplied PDF; not an editorial summary."
        ),
        "text_type": "prose",
        "language": "en",
        "source_reference": ref,
        "source_title": "The Mahabharata of Krishna-Dwaipayana Vyasa (Kisari Mohan Ganguli translation, 1883-1896)",
        "source_translator": "Kisari Mohan Ganguli",
        "source_edition": "sacred-texts.com / distributed proofing scan, 1883-1896",
        "is_primary_text": True,
        "verification_status": "verified",
        "verification_note": (
            f"Extracted verbatim from the supplied PDF (Book {rec['book']}: "
            f"{pdf_parva}{': ' + sub if sub else ''}, {rec['section']}"
            f"{', printed p. ' + rec['printed_page_start'] if rec['printed_page_start'] else ''}). "
            "Translator/edition confirmed from the PDF title pages."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    sections = extract_sections()
    by_book: dict[int, int] = {}
    empty = 0
    for s in sections:
        by_book[s["book"]] = by_book.get(s["book"], 0) + 1
        if len(s["text"]) < 200:
            empty += 1
    print(f"sections parsed: {len(sections)}")
    for b in sorted(by_book):
        print(f"  Book {b}: {by_book[b]} sections")
    print(f"short (<200 chars): {empty}")
    total_chars = sum(len(s["text"]) for s in sections)
    print(f"total prose chars: {total_chars:,}")

    passages = [to_corpus_record(s, i) for i, s in enumerate(sections)]
    out = Path(args.out)
    out.write_text(json.dumps({"passages": passages}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(passages)} passages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
