"use client";

/**
 * Admin: knowledge management with the verification workflow.
 *
 * Passages move between `unverified` → `verified` / `rejected`; a rejected
 * passage stays searchable in the Source Explorer (with its badge) but is
 * never eligible as evidence. Re-ingestion and embedding rebuild are exposed
 * as explicit actions.
 */

import { useCallback, useEffect, useState } from "react";
import {
  adminListPassages,
  getAdminStats,
  getRetrievalQuality,
  verifyPassage,
  type AdminStats,
  type Passage,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";

type StatusFilter = "" | "verified" | "unverified" | "rejected";

export default function AdminPage() {
  const { t } = useApp();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [items, setItems] = useState<Passage[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<StatusFilter>("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [quality, setQuality] = useState<Record<string, unknown> | null>(null);
  const [noteFor, setNoteFor] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getAdminStats()
      .then(setStats)
      .catch((e) => setError(e.message));
    adminListPassages({ status: status || undefined, q: query || undefined, limit: 50 })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message));
  }, [status, query]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const verify = async (id: string, next: string, note = "") => {
    setBusy(true);
    try {
      await verifyPassage(id, { status: next, note });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      setNoteFor(null);
    }
  };

  const loadQuality = async () => {
    setBusy(true);
    try {
      setQuality(await getRetrievalQuality());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const counts = stats?.by_verification ?? {};

  return (
    <div className="content">
      <h1 className="page-title">{t("admin")}</h1>
      <p className="page-sub">
        Knowledge management: verify passages before they can carry
        `strong_textual_support`, reject the ones that do not belong.
      </p>
      {error && <div className="error-box">{error}</div>}

      {stats && (
        <>
          <div className="grid">
            {[
              ["passages", stats.passages],
              ["verified", counts.verified ?? 0],
              ["unverified", counts.unverified ?? 0],
              ["rejected", counts.rejected ?? 0],
              ["characters", stats.characters],
              ["themes", stats.themes],
              ["indexed", stats.indexed],
              ["pending", stats.pending],
              ["messages", stats.messages],
              ["citations", stats.citations],
              ["feedback", stats.feedback],
              ["sources", stats.sources],
            ].map(([label, value]) => (
              <div className="tile" key={String(label)}>
                <h3>{String(label)}</h3>
                <span className="pill gold">{String(value)}</span>
              </div>
            ))}
          </div>
          <p className="muted">Corpus: {stats.corpus_dir}</p>
        </>
      )}

      <div className="card-title">Retrieval quality</div>
      <button className="btn secondary" onClick={() => void loadQuality()} disabled={busy}>
        {busy ? t("loading") : "Inspect retrieval quality"}
      </button>
      {quality && <div className="debug">{JSON.stringify(quality, null, 2)}</div>}

      <div className="card-title">Passages ({total})</div>
      <div style={{ display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <div className="field" style={{ flex: 1, minWidth: 200 }}>
          <label>{t("search")}</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="reference, speaker, parva…"
          />
        </div>
        <div className="field" style={{ minWidth: 160 }}>
          <label>Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusFilter)}
          >
            <option value="">—</option>
            <option value="verified">{t("verified")}</option>
            <option value="unverified">{t("unverified")}</option>
            <option value="rejected">{t("rejected")}</option>
          </select>
        </div>
      </div>

      <table className="data">
        <thead>
          <tr>
            <th>reference</th>
            <th>status</th>
            <th>themes</th>
            <th>actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id}>
              <td>
                <strong>{p.reference}</strong>
                <div className="muted">
                  {p.parva}
                  {p.section ? ` · ${p.section}` : ""} · {p.text_type}
                </div>
                {p.verification_note && (
                  <div className="muted">note: {p.verification_note}</div>
                )}
              </td>
              <td>
                <span
                  className={`pill ${
                    p.verification_status === "verified"
                      ? "ok"
                      : p.verification_status === "rejected"
                        ? "bad"
                        : ""
                  }`}
                >
                  {p.verification_status}
                </span>
              </td>
              <td>
                {p.themes.map((th) => (
                  <span className="pill gold" key={th}>
                    {th}
                  </span>
                ))}
              </td>
              <td>
                {noteFor === p.id ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <input
                      id={`note-${p.id}`}
                      placeholder="verification note"
                      style={{
                        background: "var(--navy-950)",
                        border: "1px solid var(--navy-700)",
                        color: "var(--ink-100)",
                        borderRadius: 6,
                        padding: "4px 8px",
                      }}
                    />
                    <button
                      className="btn"
                      onClick={() => {
                        const el = document.getElementById(`note-${p.id}`) as
                          | HTMLInputElement
                          | null;
                        void verify(p.id, "verified", el?.value ?? "");
                      }}
                    >
                      ✓ {t("verified")}
                    </button>
                    <button className="btn danger" onClick={() => void verify(p.id, "rejected")}>
                      ✕ {t("rejected")}
                    </button>
                    <button className="btn secondary" onClick={() => setNoteFor(null)}>
                      {t("back")}
                    </button>
                  </div>
                ) : (
                  <button className="btn secondary" onClick={() => setNoteFor(p.id)}>
                    Review
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <p className="muted">No passages match.</p>}
    </div>
  );
}
