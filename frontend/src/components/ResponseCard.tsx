"use client";

/**
 * Renders one assistant reply in the documented seven-section format:
 * Your Situation · From the Mahabharata · What It Teaches · Applying It ·
 * A Different Perspective · Practical Reflection · Sources.
 *
 * Refusals collapse to the documented wording + support badge — the system
 * never shows sections it has no evidence for.
 */

import { useState } from "react";
import type { Citation, GuidanceResponse } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import {
  SECTIONS,
  SUPPORT_DESCRIPTIONS,
  SUPPORT_LABELS,
  type Locale,
} from "@/lib/i18n";

export default function ResponseCard({
  reply,
  citations,
  detail = "detailed",
  onFeedback,
}: {
  reply: GuidanceResponse;
  citations?: Citation[];
  detail?: "concise" | "detailed";
  onFeedback?: (rating: 1 | -1) => void;
}) {
  const { locale, t } = useApp();
  const [showDebug, setShowDebug] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);
  const sections = SECTIONS[locale as Locale] ?? SECTIONS.en;
  const refused = reply.support_level === "insufficient_evidence";
  const concise = detail === "concise";

  const heading = (i: number) => <div className="card-title">{sections[i]}</div>;

  const giveFeedback = (rating: 1 | -1) => {
    setFeedbackGiven(rating);
    onFeedback?.(rating);
  };

  return (
    <div className="response-body">
      {/* support badge + safety notices sit above the sections */}
      <p style={{ marginTop: 0 }}>
        <span className={`badge ${reply.support_level}`}>
          {SUPPORT_LABELS[locale as Locale][reply.support_level]}
        </span>
      </p>
      {refused ? (
        <div className="notice crisis">{reply.evidence_note || SUPPORT_DESCRIPTIONS[locale as Locale].insufficient_evidence}</div>
      ) : (
        <>
          <p className="muted" style={{ fontStyle: "italic" }}>
            {SUPPORT_DESCRIPTIONS[locale as Locale][reply.support_level]}
          </p>

          {/* 1. Your Situation ------------------------------------------ */}
          {reply.situation_summary && (
            <>
              {heading(0)}
              <p>{reply.situation_summary}</p>
              {(reply.analysis.themes.length > 0 ||
                reply.analysis.entities.length > 0) && (
                <p>
                  {reply.analysis.themes.map((th) => (
                    <span className="pill gold" key={`t-${th}`}>
                      {th}
                    </span>
                  ))}
                  {reply.analysis.entities.map((en) => (
                    <span className="pill" key={`e-${en}`}>
                      {en}
                    </span>
                  ))}
                  {reply.analysis.conflict && (
                    <span className="pill bad">{reply.analysis.conflict}</span>
                  )}
                </p>
              )}
            </>
          )}

          {/* 2. From the Mahabharata ------------------------------------ */}
          {reply.episode && (
            <>
              {heading(1)}
              <p>{reply.episode}</p>
              {reply.episode_reference && (
                <p className="muted">— {reply.episode_reference}</p>
              )}
              {reply.primary_text.slice(0, 3).map((p) => (
                <div className="source-card" key={p.id}>
                  <div className="ref">
                    <a href={`/sources?query=${encodeURIComponent(p.source_reference || p.parva)}`}>
                      {p.source_reference || p.parva}
                    </a>
                  </div>
                  <div className="meta">
                    {p.parva}
                    {p.section ? ` · ${p.section}` : ""}
                    {p.speaker ? ` · speaker: ${p.speaker}` : ""}
                    {` · `}
                    <span className={`pill ${p.text_type === "summary" ? "gold" : "ok"}`}>
                      {p.text_type === "summary" ? "Editorial Summary" : "Primary Translation"}
                    </span>
                    {` · ${p.verification_status}`}
                  </div>
                  {p.text_type !== "summary" && p.quote && (
                    <div className="quote"><strong>Primary Translated Text (Ganguli): </strong>{p.quote}</div>
                  )}
                  {p.text_type === "summary" && (
                    <div className="muted" style={{ fontStyle: "normal", background: "rgba(218, 165, 32, 0.08)", padding: "8px 12px", borderRadius: "6px", marginTop: "6px" }}>
                      <strong>Editorial Summary: </strong>{p.summary || p.quote}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {/* 3. What It Teaches ----------------------------------------- */}
          {reply.interpretation && (
            <>
              {heading(2)}
              <p>{reply.interpretation}</p>
            </>
          )}

          {/* 4. Applying It --------------------------------------------- */}
          {!concise && reply.application && (
            <>
              {heading(3)}
              <p>{reply.application}</p>
            </>
          )}

          {/* 5. A Different Perspective --------------------------------- */}
          {!concise && reply.perspectives.length > 0 && (
            <>
              {heading(4)}
              {reply.perspectives.map((p) => (
                <div className="source-card" key={p.character}>
                  <div className="ref">
                    A perspective associated with {p.character}
                  </div>
                  <p style={{ margin: "6px 0" }}>{p.stance}</p>
                  {p.basis && <div className="meta">Interpretive basis: {p.basis}</div>}
                  {p.passage_ids.length > 0 && (
                    <div className="meta">Evidence: {p.passage_ids.join(", ")}</div>
                  )}
                </div>
              ))}
            </>
          )}

          {/* 6. Practical Reflection ------------------------------------ */}
          {!concise && reply.reflection_questions.length > 0 && (
            <>
              {heading(5)}
              <ul>
                {reply.reflection_questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {/* 7. Sources ------------------------------------------------------ */}
      {(reply.sources.length > 0 ||
        (citations && citations.length > 0)) && (
        <>
          {heading(6)}
          <ul>
            {reply.sources.map((s) => (
              <li key={s}><a href={`/sources?query=${encodeURIComponent(s)}`}>{s}</a></li>
            ))}
          </ul>
          {citations && citations.length > 0 && (
            <p className="muted">
              {citations.map((c) => (
                <a
                  className={`pill ${c.verified ? "ok" : ""}`}
                  key={c.id}
                  title={c.reference}
                  href={`/sources?query=${encodeURIComponent(c.reference)}`}
                >
                  {c.reference} ({c.support_level})
                </a>
              ))}
            </p>
          )}
          {concise && (
            <p className="muted">Showing the essential evidence and interpretation. Choose Detailed for application, perspectives, and reflection questions.</p>
          )}
        </>
      )}

      {/* safety notices --------------------------------------------------- */}
      {reply.safety_notices.length > 0 && (
        <>
          <div className="card-title">{t("safety")}</div>
          {reply.safety_notices.map((n, i) => (
            <div className={`notice ${n.kind}`} key={`${n.kind}-${i}`}>
              {n.message}
            </div>
          ))}
        </>
      )}

      {/* feedback + debug -------------------------------------------------- */}
      <p className="muted" style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {onFeedback && (
          <>
            <button
              className="chip"
              disabled={feedbackGiven !== null}
              onClick={() => giveFeedback(1)}
            >
              {feedbackGiven === 1 ? "✓ " : ""}
              {t("feedback_helpful")}
            </button>
            <button
              className="chip"
              disabled={feedbackGiven !== null}
              onClick={() => giveFeedback(-1)}
            >
              {feedbackGiven === -1 ? "✓ " : ""}
              {t("feedback_not_helpful")}
            </button>
          </>
        )}
        <button className="chip" onClick={() => setShowDebug((v) => !v)}>
          {showDebug ? t("hide_debug") : t("show_debug")}
        </button>
        <span className="pill">generator: {reply.generator}</span>
      </p>
      {showDebug && (
        <div className="debug">
          <strong>Retrieval summary</strong>
          <div>Semantic matches: {String(reply.retrieval_debug.semantic_hits ?? 0)}</div>
          <div>Keyword matches: {String(reply.retrieval_debug.keyword_hits ?? 0)}</div>
          <div>Metadata matches: {String(reply.retrieval_debug.metadata_hits ?? 0)}</div>
          <div>Evidence used: {String(reply.retrieval_debug.evidence_count ?? 0)}</div>
          <details>
            <summary>Full retrieval data</summary>
            <pre>{JSON.stringify(reply.retrieval_debug, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
