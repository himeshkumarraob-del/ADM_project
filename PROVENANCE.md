# Corpus Provenance

This document records the exact source of every passage the chatbot presents as
textual evidence. It is the authoritative provenance record for this repository.

```text
Source:       The Mahabharata of Krishna-Dwaipayana Vyasa
Edition:      Translated into English Prose from the Original Sanskrit Text,
              9 volumes, Calcutta: Bharata Press, 1883-1896
Translator:   Kisari Mohan Ganguli (1883-1896)
Publication:  First published 1883-1896; digital etext released by
              Project Gutenberg (eBooks #15474, #15475, #15476, #15477),
              etext produced from page images scanned at sacred-texts.com;
              Books 1-4 proofed at Distributed Proofing (Juliet Sutherland,
              Project Manager), Books 5-18 proofed at sacred-texts.com
              (John Bruno Hare, Mantra Caitanya).
License:      Public domain. Published 1883-1896 (pre-1929); Project
              Gutenberg eBooks state: "This eBook is for the use of anyone
              anywhere in the United States and most other parts of the world
              at no cost and with almost no restrictions whatsoever."
Source File:  C:\Users\Himesh kumar rao\Desktop\Mahabharata-etext.pdf (5,818 pages)
Access date:  2026-10-03
Coverage:     Extensively indexed -- 16 of the 18 canonical parvas (1,895 primary
              translated prose passages + 6 editorial anchor summaries = 1,901 total
              indexed passages across 1,889 unique sections).
              Includes Bhagavad Gita at Bhishma Parva Sections XXV-XLII.
              Missing parvas (future expansion): Karna Parva, Shalya Parva.
```

## Decision record

Selected on 2026-10-02 after comparing candidates:

| Candidate | Verdict | Why |
|---|---|---|
| **K. M. Ganguli (1883-1896)** | **SELECTED** | Only complete public-domain English translation; section-level structure maps cleanly to the canonical 18-parva taxonomy; plain-text download is reproducible from stable Project Gutenberg / sacred-texts.com source; Gita included in place inside Bhishma Parva. |
| M. N. Dutt (~1895-1905) | Rejected | Only OCR'd scans available; noisy text, no clean machine-readable edition. |
| GRETIL Sanskrit | Deferred | Sanskrit-only; would require a second source + alignment. Candidate for a future `original_text` enrichment pass, tracked separately. |
| BORI / Ramesh Menon / Mehta | Rejected | Copyrighted. |
| Kaggle / GitHub re-packagings | Rejected | Third-party mirrors of the Ganguli etext without additional provenance; ingesting from the primary host directly is strictly better. |

## Active Corpus Ingestion Verification

On **2026-10-03**, the active retrieval database was fully ingested from `Mahabharata-etext.pdf`:

- **Total Indexed Passages**: 1,901
- **Primary Text Prose Passages (`text_type: prose`)**: 1,895 (99.68%)
- **Curated Editorial Summaries (`text_type: summary`)**: 6 (0.32%)
- **Unverified Records**: 0
- **Validation Issues**: 0
- **Canonical Parva Coverage (16 of 18)**:
  1. Adi Parva (237 passages)
  2. Sabha Parva (80 passages)
  3. Vana Parva (313 passages)
  4. Virata Parva (72 passages)
  5. Udyoga Parva (200 passages)
  6. Bhishma Parva (108 passages, including Bhagavad Gita)
  7. Drona Parva (200 passages)
  8. Sauptika Parva (2 passages)
  9. Stri Parva (27 passages)
  10. Shanti Parva (374 passages)
  11. Anushasana Parva (154 passages)
  12. Ashvamedhika Parva (118 passages)
  13. Ashramavasika Parva (8 passages)
  14. Mausala Parva (4 passages)
  15. Mahaprasthanika Parva (2 passages)
  16. Svargarohana Parva (2 passages)

### Future Corpus Expansion
- **Karna Parva**: Planned for indexing in a subsequent release.
- **Shalya Parva**: Planned for indexing in a subsequent release.

## Provenance rules enforced in code

- Every passage row carries `source_id` -> a `sources` row whose `edition`, `translator`, `url` and `license` are the values above.
- Ingest fails validation if a passage presented as primary textual evidence lacks translator/edition metadata (`app/rag/taxonomy.py`, enforced by `tests/test_corpus.py`).
- Section references are stored with **Roman numerals / Section designations exactly as the source prints them** ("Bhishma Parva — Section XXVI"), so asserted locators can never be corroborated by an unrelated number.
- A passage whose `text_type` is `summary` can never carry `is_primary_text = true`.
