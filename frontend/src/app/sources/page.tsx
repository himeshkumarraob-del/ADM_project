"use client";

/**
 * Source Explorer — hybrid search over the indexed corpus with verification
 * badges on every card. This is the same endpoint the pipeline uses, so what
 * a user reads here is exactly what the model can cite.
 */

import { useCallback, useEffect, useState } from "react";
import {
  getThemes,
  getCharacters,
  searchPassages,
  type Character,
  type EvidencePassage,
  type Theme,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";

export default function SourcesPage() {
  const { t } = useApp();
  const [query, setQuery] = useState("");
  const [theme, setTheme] = useState("");
  const [parva, setParva] = useState("");
  const [character, setCharacter] = useState("");
  const [speaker, setSpeaker] = useState("");
  const [textType, setTextType] = useState<"" | "verse" | "prose" | "summary">("");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [results, setResults] = useState<EvidencePassage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getThemes()
      .then(setThemes)
      .catch(() => undefined);
    getCharacters()
      .then(setCharacters)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const linkedQuery = new URLSearchParams(window.location.search).get("query");
    if (linkedQuery) setQuery(linkedQuery);
  }, []);

  const run = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await searchPassages({
        q: query,
        parva: parva || undefined,
        character: character || undefined,
        theme: theme || undefined,
        speaker: speaker || undefined,
        text_type: textType || undefined,
        verified_only: verifiedOnly,
        limit: 30,
      });
      setResults(res.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [query, parva, character, theme, speaker, textType, verifiedOnly]);

  return (
    <div className="content">
      <h1 className="page-title">{t("sources")}</h1>
      <p className="page-sub">
        Search the indexed passages directly. Verification status and source type are shown on
        every card.
      </p>

      <div className="notice" style={{ marginBottom: 20, lineHeight: 1.6, fontSize: "13.5px" }}>
        <strong>About the Sources:</strong> Saarathi AI currently draws primarily from the Kisari Mohan Ganguli English translation of the Mahabharata. The current indexed corpus contains 1,895 primary passages across 16 of the 18 canonical Parvas, along with 6 clearly identified editorial summaries. The corpus will be expanded in future.
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div className="field" style={{ flex: 1, minWidth: 220 }}>
          <label>{t("search")}</label>
          <input
            value={query}
            placeholder="dice game, Bhishma's vow, Krishna's counsel…"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void run()}
          />
        </div>
        <div className="field" style={{ minWidth: 170 }}>
          <label>Parva</label>
          <input value={parva} placeholder="e.g. Sabha" onChange={(e) => setParva(e.target.value)} />
        </div>
        <div className="field" style={{ minWidth: 170 }}>
          <label>Character</label>
          <select value={character} onChange={(e) => setCharacter(e.target.value)}>
            <option value="">Any</option>
            {characters.map((item) => (
              <option value={item.name} key={item.slug}>{item.name}</option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: 170 }}>
          <label>{t("themes")}</label>
          <select value={theme} onChange={(e) => setTheme(e.target.value)}>
            <option value="">—</option>
            {themes.map((th) => (
              <option value={th.slug} key={th.slug}>
                {th.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: 150 }}>
          <label>Text type</label>
          <select value={textType} onChange={(e) => setTextType(e.target.value as typeof textType)}>
            <option value="">Any</option>
            <option value="prose">Primary prose</option>
            <option value="verse">Verse</option>
            <option value="summary">Editorial summary</option>
          </select>
        </div>
        <div className="field" style={{ minWidth: 170 }}>
          <label>Speaker</label>
          <input value={speaker} placeholder="e.g. Krishna" onChange={(e) => setSpeaker(e.target.value)} />
        </div>
        <div className="field" style={{ minWidth: 150 }}>
          <label>&nbsp;</label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              style={{ width: "auto" }}
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
            />
            {t("verified")}
          </label>
        </div>
        <div className="field">
          <label>&nbsp;</label>
          <button className="btn" onClick={() => void run()} disabled={busy}>
            {busy ? t("loading") : t("search")}
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      <p className="muted">{results.length} result(s)</p>

      {results.map((r) => (
        <div className="source-card" key={r.id}>
          <div className="ref">{r.source_reference || r.parva}</div>
          <div className="meta">
            {r.parva}
            {r.section ? ` · ${r.section}` : ""} ·{" "}
            <span
              className={`pill ${
                r.text_type === "summary" ? "gold" : "ok"
              }`}
            >
              {r.text_type === "summary" ? "Editorial Summary" : "Primary Translation"}
            </span>
            {" · "}
            <span
              className={`pill ${
                r.verification_status === "verified"
                  ? "ok"
                  : r.verification_status === "rejected"
                    ? "bad"
                    : ""
              }`}
            >
              {r.verification_status}
            </span>
            {typeof r.relevance === "number" && r.relevance > 0 && (
              <span className="pill">relevance {r.relevance.toFixed(2)}</span>
            )}
          </div>
          {r.quote && <div className="quote">{r.quote}</div>}
          {r.summary && <div className="muted">{r.summary}</div>}
          <p>
            {r.themes.map((th) => (
              <span className="pill gold" key={th}>
                {th}
              </span>
            ))}
          </p>
          <details className="retrieval-details">
            <summary>Why this result?</summary>
            <div className="meta">
              Retrieval channels: {r.source || "metadata"} · semantic {r.semantic_score.toFixed(2)} · keyword {r.keyword_score.toFixed(2)}
            </div>
            {r.source_title && <div className="meta">Source: {r.source_title}</div>}
            {r.speaker && <div className="meta">Speaker: {r.speaker}</div>}
          </details>
        </div>
      ))}
    </div>
  );
}
