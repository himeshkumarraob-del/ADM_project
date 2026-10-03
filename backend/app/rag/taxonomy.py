"""Canonical taxonomy validation for the Mahabharata corpus.

Single authority for what counts as a canonical parva, character and theme
reference. Corpus integrity tests and the ingest pipeline both validate against
this module, so a non-canonical value cannot enter the verified corpus metadata
unnoticed (Phase 2, Parts 3-5).

The canonical 18-parva division is fixed tradition; the display names here are
the conventional English forms used throughout the corpus. Normalisation is
deliberately lenient on input ("sauptika parva", "SAUPTIKA", "sauptika") but the
canonical display name is always what gets stored.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# The canonical 18 parvas, in traditional order.
# --------------------------------------------------------------------------- #
CANONICAL_PARVAS: list[str] = [
    "Adi Parva",
    "Sabha Parva",
    "Vana Parva",
    "Virata Parva",
    "Udyoga Parva",
    "Bhishma Parva",
    "Drona Parva",
    "Karna Parva",
    "Shalya Parva",
    "Sauptika Parva",
    "Stri Parva",
    "Shanti Parva",
    "Anushasana Parva",
    "Ashvamedhika Parva",
    "Ashramavasika Parva",
    "Mausala Parva",
    "Mahaprasthanika Parva",
    "Svargarohana Parva",
]

_CANONICAL_PARVA_SET = set(CANONICAL_PARVAS)


def normalize_parva(name: str) -> str:
    """Canonical display name for a parva reference, or "" if not canonical.

    Accepts "Sauptika", "sauptika parva", " SAUPTIKA " etc. Matching is on the
    parva's distinctive head word, so "Adi" and "Adi Parva" both resolve — but
    an unknown name ("Gadra") never resolves to something it is not.
    """
    cleaned = re.sub(r"\s+", " ", (name or "").strip()).lower()
    if not cleaned:
        return ""
    if cleaned.endswith(" parva"):
        cleaned = cleaned[: -len(" parva")].strip()
    for canonical in CANONICAL_PARVAS:
        head = canonical[: -len(" Parva")].lower()
        if cleaned == head:
            return canonical
    return ""


def is_canonical_parva(name: str) -> bool:
    return normalize_parva(name) != ""


# --------------------------------------------------------------------------- #
# Controlled vocabularies. Characters/themes are slugs from the existing
# taxonomy in app.knowledge.taxonomy; the canonical check here validates
# membership so passage metadata cannot drift from it.
#
# Characters: the 18 persona figures in CHARACTERS drive analysis; passages
# additionally name canonical *secondary* figures (deities, epic persons) and
# a small closed set of generic participants ("a Brahmin", "a dog"). Anything
# outside those three sets fails validation.
# --------------------------------------------------------------------------- #
SECONDARY_FIGURES: set[str] = {
    "yayati", "sharmishtha", "devayani", "purukutsa", "surya", "adhiratha",
    "radha", "ekalavya", "hiranyadhanus", "shantanu", "satyavati", "amba",
    "salva", "shikhandi", "dushasana", "shishupala", "jarasandha", "yaksha",
    "savitri", "satyavan", "yama", "dharma", "nala", "damayanti", "kali",
    "jayadratha", "shiva", "urvashi", "indra", "markandeya", "janamejaya",
    "takshaka", "astika", "keechaka", "virata", "uttara", "abhimanyu",
    "dhrishtadyumna", "drishtadyumna", "ghatotkacha", "shalya", "vyasa", "vasishtha",
    "balarama", "satyaki", "pradyumna", "jatasura",
}

# Non-persona participants that legitimately appear in episode metadata.
GENERIC_PARTICIPANTS: set[str] = {
    "a brahmin", "a dog", "kaurava army", "the sleeping pandava camp",
    "brahmins", "courtiers", "citizens of hastinapura",
}


def canonical_character_slugs() -> set[str]:
    from ..knowledge.taxonomy import CHARACTERS

    return {c["slug"] for c in CHARACTERS}


def canonical_theme_slugs() -> set[str]:
    from ..knowledge.taxonomy import THEMES

    return {t["slug"] for t in THEMES}


# --------------------------------------------------------------------------- #
# Passage-level validation used by ingest and by the integrity tests.
# --------------------------------------------------------------------------- #
REQUIRED_PASSAGE_FIELDS = (
    "parva",
    "section",
    "source_reference",
    "themes",
    "characters",
    "summary",
)
VALID_VERIFICATION_STATUSES = {"verified", "unverified", "needs_review", "rejected"}


class PassageIntegrityIssue(Exception):
    """Raised when a passage fails canonical validation."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


def validate_passage_metadata(item: dict, *, require_canonical_parva: bool = True) -> list[str]:
    """Return a list of integrity issues for one passage dict (empty = clean)."""
    issues: list[str] = []

    for field in REQUIRED_PASSAGE_FIELDS:
        value = item.get(field)
        if value is None or (isinstance(value, str) and not value.strip()) or (
            isinstance(value, list) and not value
        ):
            issues.append(f"missing required field: {field}")

    parva = item.get("parva") or ""
    if require_canonical_parva and parva and not is_canonical_parva(parva):
        issues.append(f"non-canonical parva: {parva!r}")

    status = (item.get("verification_status") or "").lower()
    if status and status not in VALID_VERIFICATION_STATUSES:
        issues.append(f"invalid verification_status: {status!r}")

    ref = (item.get("source_reference") or "").strip()
    if ref and parva:
        # The reference must carry the passage's own (canonical) parva. It may
        # lead the reference ("Sauptika Parva — ...") or appear parenthesised
        # ("Bhagavad Gita 2.47 (Bhishma Parva, Adhyaya 26)"). A reference that
        # names a *different* parva is a broken reference.
        head = ref.split("—")[0].split("-")[0].strip()
        head_parva = normalize_parva(head)
        if head_parva:
            if head_parva != normalize_parva(parva):
                issues.append(
                    f"broken reference: source_reference {ref!r} names {head_parva} "
                    f"but parva field is {parva!r}"
                )
        elif normalize_parva(parva) not in ref:
            issues.append(
                f"broken reference: source_reference {ref!r} does not carry parva {parva!r}"
            )

    characters = item.get("characters") or []
    known = canonical_character_slugs()
    slug_by_name = _name_to_slug()
    unknown_chars = [
        c for c in characters
        if c.strip()
        and c.strip().lower() not in slug_by_name
        and c.strip().lower() not in known
        and c.strip().lower() not in SECONDARY_FIGURES
        and c.strip().lower() not in GENERIC_PARTICIPANTS
    ]
    if unknown_chars:
        issues.append(f"characters outside taxonomy: {unknown_chars}")

    themes = item.get("themes") or []
    known_t = canonical_theme_slugs()
    unknown_themes = [t for t in themes if t.strip() and t.strip().lower() not in known_t]
    if unknown_themes:
        issues.append(f"themes outside taxonomy: {unknown_themes}")

    return issues


_NAME_TO_SLUG: dict[str, str] | None = None


def _name_to_slug() -> dict[str, str]:
    """Lower-cased display name / alias -> character slug, built lazily."""
    global _NAME_TO_SLUG
    if _NAME_TO_SLUG is None:
        from ..knowledge.taxonomy import CHARACTERS

        out: dict[str, str] = {}
        for c in CHARACTERS:
            out[c["name"].lower()] = c["slug"]
            for alias in c.get("aliases", []):
                out[alias.lower()] = c["slug"]
        _NAME_TO_SLUG = out
    return _NAME_TO_SLUG
