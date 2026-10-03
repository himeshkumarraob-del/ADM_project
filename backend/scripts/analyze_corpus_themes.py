"""Analyze corpus for missing themes needed by retrieval tests."""
import json
from pathlib import Path

CORPUS_DIR = Path("data/corpus")

all_passages = []
for fp in sorted(CORPUS_DIR.glob("**/*.json")):
    if fp.name in ("manifest.json",):
        continue
    data = json.loads(fp.read_text(encoding="utf-8"))
    items = data.get("passages", data) if isinstance(data, dict) else data
    if isinstance(items, list):
        for p in items:
            p["_file"] = fp.name
        all_passages.extend(items)

print(f"Total corpus passages: {len(all_passages)}")

# Check themes needed by retrieval tests
for theme in ["loyalty", "vows", "detachment", "revenge"]:
    matches = [p for p in all_passages if theme in (p.get("themes") or [])]
    print(f"\n{theme}: {len(matches)} passages")
    for m in matches[:3]:
        print(f"  file={m['_file']} parva={m.get('parva','?')} ref={m.get('source_reference','?')[:60]}")

# Check parvas available for Bhishma Parva
print("\n\nParvas in corpus:")
parvas = {}
for p in all_passages:
    pv = p.get("parva", "?")
    parvas[pv] = parvas.get(pv, 0) + 1
for pv, count in sorted(parvas.items()):
    print(f"  {pv}: {count}")

# Check Udyoga Parva passages with loyalty
print("\nUdyoga Parva passages:")
udyoga = [p for p in all_passages if "udyoga" in p.get("parva", "").lower()]
print(f"  Count: {len(udyoga)}")
loyalty_udyoga = [p for p in udyoga if "loyalty" in (p.get("themes") or [])]
print(f"  With loyalty theme: {len(loyalty_udyoga)}")

# Check Karna passages
karna = [p for p in all_passages if "karna" in (p.get("characters") or [])]
print(f"\nKarna passages: {len(karna)}")
karna_themes = set()
for p in karna:
    karna_themes.update(p.get("themes") or [])
print(f"  Karna themes: {sorted(karna_themes)}")

# Check Bhishma Parva / detachment
bhishma_pv = [p for p in all_passages if "bhishma parva" in p.get("parva", "").lower()]
print(f"\nBhishma Parva passages: {len(bhishma_pv)}")
detach = [p for p in bhishma_pv if "detachment" in (p.get("themes") or [])]
print(f"  With detachment: {len(detach)}")

# Revenge
print("\nRevenge theme passages:")
revenge = [p for p in all_passages if "revenge" in (p.get("themes") or [])]
print(f"  Count: {len(revenge)}")
for r in revenge[:3]:
    print(f"  parva={r.get('parva','?')}")
