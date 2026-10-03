"""Phase 3 audit: break down ``answer_faithfulness_proxy`` question by question.

The proxy (``app.eval.checks.faithfulness``) is, per answered question:

    coverage = |{words in interpretation+application} & known| / |words|
    known    = evidence vocabulary  UNION  _INTERPRETIVE_VOCAB whitelist
    score    = mean(interpretation_coverage, application_coverage)

``answer_faithfulness_proxy`` is the mean of those scores over the answered
questions (refusals are excluded by the runner). The gap ``1 - proxy`` is what
this script decomposes.

For every question it prints:

    question | retrieved evidence | generated claims |
    matched evidence vocabulary | unmatched vocabulary | score

and labels every unmatched word with the cause:

    MODERN_APPLICATION           wording about the user's modern situation;
                                 not in the evidence *by design*
    LEGITIMATE_INTERPRETATION    connective/analytical prose that asserts
                                 nothing about the source
    OVERLY_STRICT_MATCHING       word IS in the evidence pack (or is a source
                                 locator / boilerplate label) but the matcher
                                 misses it (inflection, metadata field not
                                 scanned, whitelist gap)
    UNSUPPORTED_CLAIM            residual: content word making a factual claim
                                 not traceable to the evidence
    IRRELEVANT_GENERATED_LANGUAGE  filler that neither grounds nor informs

Run:  cd backend && python -m scripts.audit_faithfulness
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import init_db  # noqa: E402
from app.eval.checks import _INTERPRETIVE_VOCAB, _WORD, faithfulness  # noqa: E402
from app.eval.runner import _load_dataset  # noqa: E402
from app.rag.pipeline import get_pipeline  # noqa: E402

# --------------------------------------------------------------------------- #
# Cause vocabulary for *unmatched* words only.
# --------------------------------------------------------------------------- #

# Modern-application layer: the user's world, never the source's.
MODERN_APP_WORDS = {
    "workplace", "job", "boss", "coworker", "colleague", "manager", "company",
    "career", "promotion", "salary", "interview", "office", "team", "project",
    "modern", "today", "nowadays", "currently", "recently", "yesterday",
    "friendship", "marriage", "spouse", "partner", "parents", "mother",
    "father", "sibling", "siblings", "children", "child", "school",
    "university", "college", "class", "classmate", "teacher", "therapy",
    "doctor", "diagnosis", "patient", "medication", "counselor", "lawyer",
    "court", "police", "legal", "tax", "money", "debt", "loan", "social",
    "media", "online", "post", "message", "email", "community", "neighbor",
    "neighbour", "stranger", "strangers", "personal", "personally",
    "interest", "pressure", "pressures", "serving", "separating",
    "inconvenient",
}

# Interpretive connective tissue: assert nothing about the source.
INTERPRETIVE_CONNECTORS = {
    "reading", "reads", "read", "means", "meaning", "suggests", "suggesting",
    "suggest", "implies", "illustrates", "illustrating", "represents",
    "reflects", "reflecting", "echoes", "mirrors", "parallels", "parallel",
    "analogy", "analogous", "compared", "comparison", "compare", "between",
    "within", "across", "underlying", "underlies", "tension", "question",
    "questions", "asks", "ask", "consider", "considering", "consideration",
    "weigh", "weighing", "balance", "balancing", "choice", "choices",
    "decide", "decision", "decisions", "response", "responses", "handle",
    "handling", "navigate", "navigating", "approach", "approaching", "frame",
    "framing", "lens", "dynamic", "dynamics", "nuance", "nuanced",
    "complexity", "complex", "difficult", "difficulty", "harder", "easier",
    "simple", "simply", "rather", "instead", "however", "although", "though",
    "because", "therefore", "thus", "hence", "yet", "still", "even", "really",
    "actually", "perhaps", "possibly", "probably", "certainly", "surely",
    "indeed", "well", "much", "many", "more", "most", "less", "least",
    "enough", "quite", "somewhat", "slightly", "clearly", "likely",
    "unlikely", "sense", "way", "ways", "matters", "matter", "mattering",
    "minded", "open", "mind", "answer", "answers", "situation", "situations",
    "circumstance", "circumstances", "expectation", "expectations", "outcome",
    "outcomes", "result", "results", "effect", "effects", "cost", "costs",
    "price", "stake", "stakes", "ground", "grounds", "terms", "attitude",
    "stance", "position", "posture", "orientation", "help", "helps",
    "helping", "useful", "usefulness", "helpful", "value", "worth", "benefit",
    "benefits", "harm", "risks", "risk", "safe", "safer", "danger",
    "dangerous", "also", "includes", "including", "each", "whether", "what",
    "which", "when", "where", "while", "whose", "want", "right", "rule",
    "state", "stages", "stage", "single", "does", "distinguishes",
    "emphasising", "emphasizing", "emphasis", "demands", "demand", "binding",
    "become", "becomes", "protects", "protecting", "absorbing", "real",
    "anything", "wrong", "asks", "stop", "away", "sits", "loss",
    "explaining", "foregrounds", "obligations", "obligation", "return",
    "encounter", "conversation", "story", "make", "material", "contains",
    "enough", "before", "being", "from", "work", "works", "position",
    "person", "sounds", "offer", "only", "naming", "index", "indexed",
    "authoritative", "explorer", "honestly", "claim", "claims", "killing",
    "abduction", "exhausted", "authoritative", "adhyaya",
    # -- the modern-analogy caveat (Phase 3 #7). These qualify the *analogy*;
    # they assert nothing about the source itself.
    "royal", "dynastic", "substantially", "circumstance", "circumstances",
    "carry", "carries", "carrying", "counsel", "narrative", "epic", "epic's",
    "stops", "limited", "limiting", "limit", "drawn", "differs", "differ",
    "differing", "raises", "raised", "advice", "advises", "inside", "given",
    "world", "worlds", "reader", "readers", "today", "modern", "ancient",
    "context", "contexts", "transfers", "transfer", "analogous",
    # -- the application-layer lead-ins added in Phase 3 #2
    "asking", "separating", "serving", "morality", "recognition", "credit",
    # meta words the generator uses to label its own layers
    "interpretation", "interpreting", "interpreted", "applied", "applying",
    "application", "applies", "apply", "textual", "evidence", "retrieved",
    "passage", "passages", "episode", "episodes", "source", "sources",
    "text", "texts", "verse", "verses", "chapter", "chapters", "section",
    "sections", "mahabharata", "vyasa", "dharma", "duties", "teaches",
    "teaching", "teachings", "lesson", "lessons", "moral", "morals",
    "principle", "principles", "theme", "themes", "idea", "ideas",
    # pronouns / determiners the >=4-letter regex keeps
    "this", "that", "these", "those", "there", "here", "them", "they",
    "their", "been", "have", "having", "done", "doing", "into", "onto",
    "upon", "just", "than", "then", "very", "ever", "never", "always",
    "again", "once", "twice", "about", "above", "below", "under", "over",
    "their", "them", "what", "your",
}

_CLASSIFIERS = (
    ("MODERN_APPLICATION", MODERN_APP_WORDS),
    ("LEGITIMATE_INTERPRETATION", INTERPRETIVE_CONNECTORS),
)


def classify(word: str, evidence_blob: str) -> str:
    """Label one unmatched word. ``UNSUPPORTED_CLAIM`` is the residual.

    ``OVERLY_STRICT_MATCHING`` fires when the word literally appears in the
    evidence pack but the metric's per-field token set did not pick it up
    (inflected form, or a metadata field -- reference/keywords/events --
    that :func:`faithfulness` does not scan).
    """
    stem = word.rstrip("s")
    for label, vocab in _CLASSIFIERS:
        if word in vocab or stem in vocab:
            return label
    # does the raw evidence text contain it (or a plausible inflection)?
    if word in evidence_blob or stem in evidence_blob:
        return "OVERLY_STRICT_MATCHING"
    return "UNSUPPORTED_CLAIM?"


def _evidence_vocabulary(evidence) -> tuple[set[str], str]:
    """Words the metric knows, plus the full raw evidence text (for the
    over-strict detection, which also looks at fields the metric skips).

    The whitelist is part of ``known`` exactly as in :func:`faithfulness`,
    so the split reproduces the real gap rather than a stricter one.
    """
    known: set[str] = set(_INTERPRETIVE_VOCAB)
    raw_parts: list[str] = []
    for p in evidence:
        scanned = " ".join([p.summary, p.quote, p.original_text, p.parva,
                            p.section, " ".join(p.characters),
                            " ".join(p.themes)])
        skipped = " ".join([p.reference or "", p.chapter or "",
                            " ".join(getattr(p, "keywords", []) or [])])
        known |= {w.lower() for w in _WORD.findall(scanned)}
        raw_parts.extend([scanned, skipped])
    return known, " ".join(raw_parts).lower()


def _split(text: str, known: set[str]) -> tuple[set[str], set[str]]:
    words = {w.lower() for w in _WORD.findall(text)}
    matched = {w for w in words if w in known or w.rstrip("s") in known}
    return matched, words - matched


def audit(dataset: str = "default") -> dict:
    items = _load_dataset(dataset)
    pipe = get_pipeline()

    rows = []
    class_totals: Counter[str] = Counter()
    class_gap: Counter[str] = Counter()   # weighted by each word's 1/|words|

    for item in items:
        reply = pipe.run(
            query=item["question"],
            mode=item.get("mode", "situation_advice"),
            language="en",
            character=item.get("character"),
            include_perspectives=(item.get("mode") == "perspectives"),
        ).response
        evidence = reply.primary_text
        known, raw_blob = _evidence_vocabulary(evidence)

        interp = reply.interpretation or ""
        applic = reply.application or ""
        m_i, u_i = _split(interp, known)
        m_a, u_a = _split(applic, known)

        # per-layer word counts, mirroring faithfulness()'s set semantics
        n_i = len({w.lower() for w in _WORD.findall(interp)})
        n_a = len({w.lower() for w in _WORD.findall(applic)})

        answered = reply.support_level != "insufficient_evidence"
        labels: dict[str, str] = {}
        for w in sorted(u_i | u_a):
            lab = classify(w, raw_blob)
            labels[w] = lab
            class_totals[lab] += 1
            # gap weight: how much this word costs in the mean of the two
            # layer coverages (1/n_i or 1/n_a, averaged over the two layers).
            # Only answered questions count: the runner excludes refusals.
            if not answered:
                continue
            cost = 0.0
            if w in u_i and n_i:
                cost += 0.5 / n_i
            if w in u_a and n_a:
                cost += 0.5 / n_a
            class_gap[lab] += cost

        score = faithfulness(reply, evidence)
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answered": answered,
                "evidence": [p.source_reference or p.parva for p in evidence],
                "interpretation": interp,
                "application": applic,
                "matched": sorted(m_i | m_a),
                "unmatched": sorted(u_i | u_a),
                "labels": labels,
                "score": score,
            }
        )

    return {
        "rows": rows,
        "class_totals": dict(class_totals),
        "class_gap": {k: round(v, 4) for k, v in class_gap.items()},
    }


def main() -> None:
    init_db()
    report = audit()

    for row in report["rows"]:
        print("=" * 100)
        flag = "" if row["answered"] else "  [REFUSED - excluded from proxy]"
        print(f"[{row['id']}]{flag} {row['question']}")
        print("  RETRIEVED EVIDENCE:")
        for ref in row["evidence"]:
            print(f"    - {ref}")
        print("  GENERATED CLAIMS:")
        print(f"    INTERPRETATION: {row['interpretation']}")
        print(f"    APPLICATION   : {row['application']}")
        print(f"  SCORE: interp={row['score']['interpretation_coverage']} "
              f"applic={row['score']['application_coverage']} "
              f"mean={row['score']['mean_coverage']}")
        print(f"  MATCHED EVIDENCE VOCAB ({len(row['matched'])}): "
              f"{' '.join(row['matched'])}")
        print(f"  UNMATCHED ({len(row['unmatched'])}):")
        for w in row["unmatched"]:
            print(f"    {w:24s} -> {row['labels'][w]}")

    print("=" * 100)
    print("GAP DECOMPOSITION (weighted by each word's contribution to the "
          "per-question score; refusals excluded)")
    gaps = report["class_gap"]
    total = sum(gaps.values()) or 1.0
    order = ["LEGITIMATE_INTERPRETATION", "MODERN_APPLICATION",
             "INTERPRETIVE_VOCAB_WHITELISTED", "OVERLY_STRICT_MATCHING",
             "UNSUPPORTED_CLAIM?", "IRRELEVANT_GENERATED_LANGUAGE"]
    for label in order:
        g = gaps.get(label, 0.0)
        if not g:
            continue
        print(f"  {label:34s} gap={g:6.3f}  ({100 * g / total:5.1f}% of gap)")
    print(f"  {'TOTAL GAP ATTRIBUTED':34s} gap={total:6.3f}")
    answered = [r for r in report["rows"] if r["answered"]]
    proxy = sum(r["score"]["mean_coverage"] for r in answered) / max(1, len(answered))
    n = max(1, len(answered))
    print(f"\n  answered questions = {len(answered)}; "
          f"mean coverage = {proxy:.3f} -> gap = {1 - proxy:.3f}")
    print("  per-question mean of each cause (sums to the gap):")
    for label in order:
        g = gaps.get(label, 0.0)
        if not g:
            continue
        print(f"    {label:34s} {g / n:6.3f}  ({100 * (g / n) / (1 - proxy):5.1f}% of gap)")
    print(f"    {'TOTAL':34s} {total / n:6.3f}")


if __name__ == "__main__":
    main()
