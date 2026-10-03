# Audit: `answer_faithfulness_proxy` (Phase 3, step 1)

**No generation logic and no metric logic was changed to produce this audit.**

Reproduce with: `cd backend && python -m scripts.audit_faithfulness`

## 1. How the metric is calculated

`app/eval/checks.py :: faithfulness()`, per answered question (refusals are
excluded by `runner.py`):

```
evidence_words = union over evidence passages of tokens from:
                 summary, quote, original_text, parva, section,
                 characters, themes
known          = evidence_words ∪ _INTERPRETIVE_VOCAB   (whitelist)

coverage(text) = |{tokens(text)} ∩ known| / |tokens(text)|
                 (token counts as matched if present, or singularised, in known)

score          = mean(coverage(interpretation), coverage(application))

answer_faithfulness_proxy = mean(score) over the 13 answered questions
                            (q13/q14 are refusals -> excluded)
```

Tokeniser: `[A-Za-z][A-Za-z'’-]{3,}` — ≥4 letters, so stopwords like "the",
"a", "to" are already excluded. Sets are used per layer, so repeated words
count once.

## 2. Per-question breakdown

Format: question · evidence · scores. Full text, matched and unmatched
vocabulary with per-word cause labels is printed by the audit script.

| id | question | interp | applic | mean |
|----|----------|--------|--------|------|
| q01 | What does the Mahabharata say about keeping promises? | 0.847 | 0.500 | 0.673 |
| q02 | Why did Karna remain loyal to Duryodhana? | 0.833 | 0.560 | 0.697 |
| q03 | What can be learned from Yudhishthira's decisions? | 0.855 | 0.609 | 0.732 |
| q04 | How does Krishna approach difficult decisions? | 0.805 | 0.444 | 0.625 |
| q05 | What does the Mahabharata show about revenge? | 0.753 | 0.375 | 0.564 |
| q06 | Friend takes advantage of me — keep helping? | 0.760 | 0.423 | 0.592 |
| q07 | Someone else gets the credit — give up? | 0.736 | 0.545 | 0.641 |
| q08 | Should I remain silent when my friend is wrong? | 0.777 | 0.500 | 0.639 |
| q09 | Friend betrayed me, I want revenge | 0.784 | 0.417 | 0.601 |
| q10 | What happens in the dice game? | 0.861 | 0.565 | 0.713 |
| q11 | Why did Bhishma refuse to fight Shikhandi? | 0.829 | 0.409 | 0.619 |
| q12 | Walk away from a duty you never asked for? | 0.780 | 0.480 | 0.630 |
| q15 | Serious medical diagnosis — what should I do? | 0.762 | 0.500 | 0.631 |
| q13/q14 | canary refusals | — | — | excluded |

**Pattern:** interpretation sits at 0.74–0.86 everywhere; application sits at
0.375–0.609. The application layer alone drags the mean down.

## 3. Gap decomposition (sums exactly to 0.357)

Each unmatched token is weighted by its contribution to the per-question score
(`0.5/n_i` for the interpretation layer, `0.5/n_a` for the application layer),
summed over the 13 answered questions, then averaged.

| cause | per-question contribution | share of the 0.357 gap |
|-------|---------------------------|------------------------|
| LEGITIMATE_INTERPRETATION | 0.254 | 71.2% |
| MODERN_APPLICATION | 0.059 | 16.6% |
| UNSUPPORTED_CLAIM (residual) | 0.036 | 9.9% |
| OVERLY_STRICT_MATCHING | 0.008 | 2.3% |
| **TOTAL** | **0.357** | **100%** |

## 4. What each slice actually is

### LEGITIMATE_INTERPRETATION — 71.2%
Connective/analytical prose that asserts nothing about the source:
"reading", "suggests", "considering", "tension", "choice", "weigh",
"distinguishes", "stages", "rule", "textual", "evidence", "retrieved",
"includes", "situation", "demand"… Mostly the fixed labels the response uses
to mark its own layers (`Textual evidence:`, `Interpretation:`, `The evidence
set also includes…`) plus the `not_a_command` sentence.

**This is legitimate interpretation, not an unsupported factual claim.**

### MODERN_APPLICATION — 16.6%
The user's world, which is *by design* not in a 5th-century-BCE corpus:
"personal", "personally", "interest", "pressure", "serving", "separating",
"asking", "workplace"-class vocabulary. The application layer exists precisely
to bridge to the user's situation, so its vocabulary cannot be in the evidence.

**This is modern application language, correctly unmatched.**

### UNSUPPORTED_CLAIM (residual) — 9.9%
Twelve distinct words total. Every one was traced to a fixed template, never
to a fabricated fact about the source:

| word | origin |
|------|--------|
| around, aspiration, limits, outrunning | `PRINCIPLES["ambition"]` |
| follows, produces, retaliation | `PRINCIPLES["revenge"]` |
| beyond, raised, paid | `PRINCIPLES["gambling"]` / `PRINCIPLES["gratitude"]` |
| morality | the analysed conflict string ("friendship vs morality") |
| asking | `_application_for()` suggestion template |

**Zero unsupported factual claims about the Mahabharata.** These are the
wording of the interpretive principle sentences, which are deliberately not
lifted verbatim from any passage.

### OVERLY_STRICT_MATCHING — 2.3%
Words genuinely present in the evidence pack but missed by the matcher:
possessive forms ("abhimanyu's", "karna's", "duryodhana's" — the evidence has
"Abhimanyu"), reference/locator fields (`udyoga`, `matsya`, `prashna`) that
`faithfulness()` does not scan, and one inflection ("refusal"/"refuses").

**This is a lexical-matching artifact, ~0.008 of the score.**

## 5. Verdict

| hypothesis | verdict |
|------------|---------|
| legitimate interpretation | **yes — 71.2%** |
| modern application language | **yes — 16.6%** |
| unsupported factual claims | **no — 0 of them; residual traces to fixed templates** |
| irrelevant generated language | negligible (~0) |
| overly strict lexical matching | minor — 2.3% |
| missing evidence | no: `retrieval_coverage = 0.867`, refusals are correct |

The 0.357 is **not** a quality problem to be "fixed" by editing the metric.
It is dominated by two categories the design *requires*: interpretive prose
(71%) and modern-application prose (17%). Raising the number by whitelisting
more words would be exactly the number-chasing this phase forbids — and would
destroy the metric's value as a regression detector for genuinely ungrounded
output.

The proxy is retained unchanged as a regression baseline. The real advice
quality questions are addressed by the new, separately-defined dimensions in
`advice_metrics.py`.
